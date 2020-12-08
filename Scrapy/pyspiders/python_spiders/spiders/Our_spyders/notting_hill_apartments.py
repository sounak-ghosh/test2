import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="test_app")


def num_there(s):
    return any(i.isdigit() for i in s)

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

    if len(list_text) == 2:
        output = int(list_text[0])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = int(float(list_text[0]+list_text[1]))
    elif len(list_text) == 2:
        output = int(float(list_text[0]+list_text[1]))
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0
    return output

def getRent(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0]+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output


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



class auditaSpider(scrapy.Spider):
    name = 'Nottinghillapartments_PySpider_united_kingdom'
    allowed_domains = ['nottinghillapartments.com']
    start_urls = ['nottinghillapartments.com']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'

    def start_requests(self):
        url="https://nottinghillapartments.com/london-rentals/"
        yield scrapy.Request(url=url,
                             callback=self.parse)

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body)

        all_prop = soup.find_all("div", class_="prop-info")
        
        global el
        el = []
        for ech_prop in all_prop:
            el.append(ech_prop.find("h3", class_="grid-prop-title prop-title").find("a")["href"])

        for find_count in soup.find("div",class_="pagination loop-pagination").find_all("a", class_="page-numbers")[::-1]:
            if num_there(find_count.text):
                count = int(find_count.text)
                break   
        
        print(count)
        for c in range(count):
            if c==0:
                pass
            else:
                url = "https://nottinghillapartments.com/london-rentals/page/{}/".format(str(c+1))
                yield scrapy.Request(url=url, callback=self.parse1,meta = {"flag":c+1==count})
    def parse1(self, response):
        soup1 = BeautifulSoup(response.body,"html.parser")
        all_prop = soup1.find_all("div", class_="prop-info")
        
        for ech_prop in all_prop:
            el.append(ech_prop.find("h3", class_="grid-prop-title prop-title").find("a")["href"])

        if response.meta.get("flag"):
            for ech_url in el:
                yield scrapy.Request(url=ech_url, callback=self.getPropertydtl)

    def getPropertydtl(self,response,**kwargs):
        # print("hi")
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print(response.url)
        item["external_link"] = response.url

        rent = soup.find("div", class_="clearfix padding30").find("span", class_="prop-price pull-right serif italic").text
        rent_month = int((getSqureMtr(rent)/7)*30)
        # print(rent_month)
        item["rent"] = rent_month

        title = soup.find("div", class_="clearfix padding30").find("h2", class_="prop-title pull-left margin0").text
        # print(title)
        item["title"] = title

        all_h2_title = soup.find_all("h2", class_="prop-title pull-left margin0")
        for ech_h2 in all_h2_title:
            if "available" in ech_h2.text.lower():
                if num_there(ech_h2.text):
                    available_date = format_date(ech_h2.text.split(" ")[-1].strip())
                    item["available_date"] = available_date

        temp_dic = {}
        for ech_li in soup.find("ul", class_="more-info mylist clearfix").find_all("li"):
            temp_dic[ech_li.find("span", class_="pull-left").text] = ech_li.find("span", class_="qty pull-right").text
        temp_dic = cleanKey(temp_dic)
        # print(temp_dic)

        # {'id': 'FLAT-\xadLG71-11', 'propertytype': '1 Bedroom', 'bedrooms': '1 ', 'bathrooms': '1 ', 'parking': 'On street (permit req)', 'heating': 'Central heating', 'location': 'Notting Hill'}
        if "id" in temp_dic:
            reference_id = temp_dic["id"]
            # print(reference_id) #extra - nikalna hai
            item["external_id"] = reference_id

        if "bedrooms" in temp_dic:
            if num_there(temp_dic["bedrooms"]):
                room_count = getSqureMtr(temp_dic["bedrooms"].strip())
                # print(room_count)
                item["room_count"] = int(room_count)

        try:
            if "bathrooms" in temp_dic:
                bathroom_count = temp_dic["bathrooms"].strip()
                # print(bathroom_count)
                item["bathroom_count"] = int(bathroom_count)
        except:
            pass

        desc = ""
        for ech_p in soup.find("div",class_="clearfix padding030").find_next("div").find_next_sibling("div").find_all("p"):
            desc = desc + ech_p.text
        # print(desc) 
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "furnished" in desc.lower() or "furniture" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True


        image_list = []
        for im in soup.find("ul", class_="slides").find_all("li"):
            image_list.append(im.find("a", class_="single_prop_img")["href"])
        if image_list:
            # print(image_list)
            item["images"] = image_list
            # print(len(image_list))
            item["external_images_count"] = len(image_list)

        extract_text = re.findall("address:(.+),",str(soup))
        address = (extract_text[0]).strip().replace('"','')
        # print(address)
        item["address"] = address
        item["city"] = "london"
        zipcode = address.split(" ")[-2].strip() + " " + address.split(" ")[-1].strip()
        # print(zipcode)
        item["zipcode"] = zipcode

        try:
            location = geolocator.geocode(address)
            lat=location.latitude
            # print(lat)
            item["latitude"] = str(lat)
            lon=location.longitude
            # print(lon)
            item["longitude"] = str(lon)
        except:
            pass

        item["landlord_name"] = "Notting Hill Apartments"
        item["landlord_phone"] = "+44 (0)20 7221 2288"
        item["landlord_email"] = "info@nottinghillapartments.com"
        item["property_type"] = "apartment"
        item["currency"] = "GBP"
        item["external_source"] = "Nottinghillapartments_PySpider_united_kingdom"
        print(item)
        yield(item)