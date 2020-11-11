import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests
import geopy
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="myGeocoder")

def get_lat_lon(_address):
    location = geolocator.geocode(_address)
    return location.latitude,location.longitude


def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
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


class QuotesSpider(scrapy.Spider):
    name = 'cubixestateagents_co_uk_PySpider_unitedkingdom_en'
    allowed_domains = ['www.cubixestateagents.co.uk']
    start_urls = ['www.cubixestateagents.co.uk']
    execution_type = 'testing'
    country = 'unitedkingdom'
    locale ='en'

    def start_requests(self):
        url="https://www.cubixestateagents.co.uk/properties-for-rent/?tab=for-rent"

        yield scrapy.Request(
            url=url,
            callback=self.parse
            )


    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")


        if soup.find("div", class_="pagination-wrap"):
            all_pages = soup.find("div", class_="pagination-wrap").find("ul").find_all("li")
            if num_there(all_pages[-1].text):
                count = all_pages[-1].text
            elif num_there(all_pages[-2].text):
                count = all_pages[-2].text
            count = int(count)

            for c in range(count):
                if c==0:
                    url = "https://www.cubixestateagents.co.uk/properties-for-rent/?tab=for-rent"
                else:
                    url = "https://www.cubixestateagents.co.uk/properties-for-rent/page/{}/?tab=for-rent".format(str(c+1))
                    
                yield scrapy.Request(
                    url=url,
                    callback=self.get_page_details
                    )
       
    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        all_prop = soup.find("div", class_="listing-view list-view card-deck").find_all("div", class_="item-wrap item-wrap-v1 item-wrap-no-frame h-100")
        for ech_prop in all_prop:
            external_link = ech_prop.find("div", class_="item-header").find("a",class_="hover-effect")["href"]
            print (external_link)
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )


    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)
        print (response.url)

        match = re.findall("var houzez_single_property_map =(.+);",str_soup)
        if match:
            dic_data = eval(match[0])
            if "lat" in dic_data:
                item["latitude"] = str(dic_data["lat"])
            if "lng" in dic_data:
                item["longitude"] = str(dic_data["lng"]) 

        title = soup.find("div", class_="page-title").find("h1").text.strip()
        item["title"] = title

        desc = soup.find("div", id="property-description").find("div", class_="block-content-wrap").text.strip()
        item["description"] = desc
        # print(desc)

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if ("gemeubileerd" in desc.lower() or "furnished" in desc.lower() or "meublé" in desc.lower()) and "unfurnished" not in desc.lower():
            item["furnished"] = True
        if "machine à laver" in desc.lower() or ("washing" in desc.lower() and "machine" in desc.lower()):
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.lower():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "ascenseur" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        temp_dic = {}
        details = soup.find("div",id="property-details").find("div", class_="detail-wrap").find("ul").find_all("li")
        for ech_det in details:
            temp_dic[ech_det.find("strong").text] = ech_det.find("span").text
        temp_dic = cleanKey(temp_dic)
        
        if "propertyid" in temp_dic:
            item["external_id"] = temp_dic["propertyid"]
        
        if "price" in temp_dic:
            item["rent"] = getPrice(temp_dic["price"])

        if "propertysize" in temp_dic:
            item["square_meters"] = getSqureMtr(temp_dic["propertysize"])

        if "bedrooms" in temp_dic:
            item["room_count"] = int(temp_dic["bedrooms"])

        if "bathroom" in temp_dic:
            item["bathroom_count"] = int(temp_dic["bathroom"])

        property_type="NA"
        if "propertytype" in temp_dic:
            if "apartment" in temp_dic["propertytype"].lower():
                property_type = "apartment"
            elif "house" in temp_dic["propertytype"].lower() or "maisonette" in temp_dic["propertytype"].lower():
                property_type = "house"
            elif "room" in temp_dic["propertytype"].lower():
                property_type = "room"
            else:
                property_type = "NA"



        temp_dic = {}
        add_detail = soup.find("div",id="property-address").find("div", class_="block-content-wrap").find("ul").find_all("li")
        for ech_add_det in add_detail:
            temp_dic[ech_add_det.find("strong").text] = ech_add_det.find("span").text
        temp_dic = cleanKey(temp_dic)

        if "address" in temp_dic:
            item["address"] = temp_dic["address"]
        if "city" in temp_dic:
            item["city"] = temp_dic["city"]
        if "zip_postalcode" in temp_dic:
            item["zipcode"] = temp_dic["zip_postalcode"]

        image_list = []
        imgs = soup.find("div", class_="top-gallery-section").find("div", id="property-gallery-js").find_all("div")
        for im in imgs:
            image_list.append(im.find("img")["src"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        item["external_source"] = "cubixestateagents_co_uk_PySpider_unitedkingdom_en"
        item["landlord_phone"] = "0203 582 8710"
        item["landlord_email"] = "info@cubixestateagents.co.uk"
        item["landlord_name"] = "Cubix Estate Agents"
        item["currency"] = "GBP"
        item["external_link"] = response.url


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            item["property_type"] = property_type
            print(item)
            yield item
