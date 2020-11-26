import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time
from geopy.geocoders import Nominatim
import timestring
from word2number import w2n

geolocator = Nominatim(user_agent="myGeocoder")

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
        output = float(list_text[0]+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)


def cleanText(text):
    text = ''.join(text.split())
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text).strip()
    return text.replace(" ","_").lower()


def num_there(s):
    return any(i.isdigit() for i in s)


def cleanKey(data):
    if isinstance(data,dict):
        dic = {}
        for k,v in data.items():
            dic[cleanText(k)]=cleanKey(v)
        return dic
    else:
        return data

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = str(timestring.Date(text)).replace("00:00:00","").strip()
    return date


class spiderQoutes(scrapy.Spider):
    name = 'liferesidential_PySpider_uk_en'
    allowed_domains = ['liferesidential.co.uk']
    start_urls = ['liferesidential.co.uk']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'


    def start_requests(self):
        url = "https://liferesidential.co.uk/property/rent/?address=&min_bed=&max_price="
        yield scrapy.Request(
            url = url,
            callback=self.parse
            )

    def parse(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        total_page = int(soup.find("div",id="searchResults")["data-pages"])

        for page in range(1,total_page+1):
            if page==1:
                url = "https://liferesidential.co.uk/property/rent/?include_uo=False&sort=most_recent"

            else:
                url = "https://liferesidential.co.uk/property/rent/{}/?include_uo=False&sort=most_recent".format(page)

            yield scrapy.Request(
                url = url,
                callback=self.get_page_details
                )


    def get_page_details(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        
        all_prop = soup.find("ul", class_="listings").find_all("li",recursive=False)

        for ech_prop in all_prop:
            root_info  = {}
            root_info["property_type"] = "apartment"

            external_link = "https://liferesidential.co.uk"+ech_prop.find("a")["href"]
            address = ech_prop.find("a")["title"]
            all_li = ech_prop.find("ul",class_=False).find_all("li")
            temp_dic = {}
            for ech_li in all_li:
                k = ech_li.find("i")["class"][0]
                v = ech_li.text.strip()
                temp_dic[k] = v

            temp_dic = cleanKey(temp_dic)
            if "bedrooms" in temp_dic and getSqureMtr(temp_dic["bedrooms"]):
                root_info["room_count"] = getSqureMtr(temp_dic["bedrooms"])
            else:
                root_info["property_type"] = "studio"

            if "bathrooms" in temp_dic and getSqureMtr(temp_dic["bathrooms"]):
                root_info["bathroom_count"] = getSqureMtr(temp_dic["bathrooms"])

            if "price" in temp_dic:
                root_info["rent"] = getPrice(temp_dic["price"].split("/")[-1])
                root_info["deposit"] = getPrice(temp_dic["price"].split(":")[-1])

            root_info["external_id"] = ech_prop.find("a",class_ = "shortlist")["data-ref"]
            root_info["address"] = address
            root_info["title"] = address
            yield scrapy.Request(
                url = external_link,
                callback=self.get_property_details,
                meta = root_info
                )

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print (response.url)


        for k,v in response.meta.items():
            try:
                item[k] = v
            except:
                pass


        if soup.find("div",class_ = "rte"):
            desc = soup.find("div",class_="rte").find("div",class_ = "row").find_next("div",class_ = "row").text.strip()

            if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                item["parking"] = True
            if "terras" in desc.lower() or "terrace" in desc.lower():
                item["terrace"] = True
            if "balcon" in desc.lower() or "balcony" in desc.lower():
                item["balcony"] = True
            if "zwembad" in desc.lower() or "swimming" in desc.lower():
                item["swimming_pool"] = True
            if "machine à laver" in desc.lower() or"washing" in desc.lower():
                item["washing_machine"] = True
            if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
                item["dishwasher"] = True
            if "lift" in desc.lower() or "elevator" in desc.lower():
                item["elevator"] = True

            item["description"] = desc

        image = soup.find_all("picture")
        list_images = []
        for pics in image:
            if pics.find("img",alt="image"):
                list_images.append(pics.find("img",alt="image")["src"])

        if list_images:
            item["images"] = list_images
        
        #floor plan image
        flr = soup.find("div",class_="flexslider")
        flr_plan = []
        if flr:
            flr_plan = [flr.find("img")["src"]]

        if flr_plan:
            item["floor_plan_images"] = flr_plan

        if flr_plan or list_images:
            item["external_images_count"] = len(flr_plan)+len(list_images)



        # #landlord, contact, email_id
        infrmtn = soup.find("div",class_="content-wrapper")
        inform = infrmtn.find("aside",class_="contact-office")
        item["landlord_name"] = inform.find("h2",class_="office-name").text
        item["landlord_phone"] = inform.find("a",class_="plain-link").text
        item["landlord_email"] = inform.find("a",class_="dont-break-out").text
        item["external_source"] = "liferesidential_PySpider_uk_en"
        item["external_link"] = response.url
        item["currency"] = "GBP"
        print (item)
        yield item