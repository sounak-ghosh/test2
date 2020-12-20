# Author: Sounak Ghosh
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

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date

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
    name = 'Birchletting_PySpider_united_kingdom'
    allowed_domains = ['birchletting.com']
    start_urls = ['birchletting.com']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'

    def start_requests(self):
        
        header = {"origin": "https://birchletting.com","referer": "https://birchletting.com/property-to-let","user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36/8mqLqMuL-37"}
        starting_urls = "https://birchletting.com/property-code.php"
        property_type_list = ["Studio", "Flat"]
        for p_t in property_type_list:
            frmdata = { "search_prop": "1",
                        "property_type": p_t,
                        "bed_min":"", 
                        "bed_max":"", 
                        "price_min":"", 
                        "price_max":"", 
                        "location_vals":"",
                        "order_by":"",
                        "prop_postcode":""
                        }
            yield scrapy.FormRequest(url=starting_urls, callback = self.parse, formdata=frmdata, meta={"property_type": p_t})

    def parse(self, response, **kwargs):

        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        for ech_prop in soup.findAll("div", class_="property-list property"):
            url = "https://birchletting.com"+ech_prop.find("a")["href"]
            yield scrapy.Request(url = url, callback = self.get_property_details,meta = {"property_type":property_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        if "Studio" in response.meta.get("property_type"):
            item["property_type"] = "studio"
        if "Flat" in response.meta.get("property_type"):
            item["property_type"] = "apartment"
        
        item["external_link"] = (response.url)
        print(response.url)

        temp_address = soup.find("div", class_="property-desc").find("h2").text.splitlines()
        temp_address = list(filter(None, temp_address))
        address = ""
        for t in temp_address:
            if t:
                address = address + t.strip()+" "
        item["address"] = address.strip()
        item["title"] = address.strip()
        item["zipcode"] = address.split(",")[-1].strip()
        item["city"] = "london"
        
        desc = soup.find("div", class_="property-desc").find("p").text.strip() + "\n" + soup.find("div", class_="prop-desc-scroll").text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "furnished" in desc.lower() or "furniture" in desc.lower() or "furnishing" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        if soup.find("div", class_="description-resize").find("ul"):
            for ech_feat in soup.find("div", class_="description-resize").find("ul").find_all("li"):
                if ech_feat.text:
                    if "parking" in ech_feat.text.lower():
                        item["parking"] = True
                    if "lift" in ech_feat.text.lower():
                        item["elevator"] = True
                    if "balcony" in ech_feat.text.lower():
                        item["balcony"] = True

        for bed_bath in soup.find("div", class_="property-features features-detailed").find_all("td"):
            if "bed" in bed_bath.text.lower():
                room_count = getSqureMtr(bed_bath.text)
                item["room_count"] = room_count
            if "bath" in bed_bath.text.lower():
                bathroom_count = getSqureMtr(bed_bath.text)
                item["bathroom_count"]=bathroom_count

        for rent_sqm in soup.find("div", class_="property-lst-prices-detailed").find_all("h3"):
            if "sq" in rent_sqm.text and "m" in rent_sqm.text:
                square_meters = getSqureMtr(rent_sqm.text)
                item["square_meters"] = square_meters
            if "pcm" in rent_sqm.text:
                rent = getPrice(rent_sqm.text)
                item["rent"] = rent

        image_list = []
        for im in soup.find("div", class_="fotorama").find_all("a"):
            if im["href"]:
                image_list.append("https://birchletting.com"+im["href"].replace("..",""))
        if image_list:
            item["images"] = image_list
        floor_plan_list = []
        if soup.find("a", class_="floorplan-lnk")["href"]:
            floor_plan_list.append("https://birchletting.com"+soup.find("a", class_="floorplan-lnk")["href"].replace("..",""))
        if floor_plan_list:
            item["floor_plan_images"]=floor_plan_list
        if image_list or floor_plan_list:
            external_images_count = len(image_list)+len(floor_plan_list)
            item["external_images_count"]=external_images_count

        latitude = soup.find("div", class_="lat").text
        longitude = soup.find("div", class_="long").text
        item["latitude"]=latitude
        item["longitude"]=longitude

        item["landlord_phone"] = "+44 (0)20 7222 1975"
        item["landlord_name"] = "Birch & Co"
        item["currency"] = "GBP"
        item["external_source"] = "Birchletting_PySpider_united_kingdom"

        print(item)
        yield item

