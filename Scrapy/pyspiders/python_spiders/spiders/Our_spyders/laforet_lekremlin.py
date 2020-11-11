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


def clean_value(text):
    if text is None:
        text = ""
    if isinstance(text,(int,float)):
        text = str(text.encode('utf-8').decode('ascii', 'ignore'))
    text = str(text.encode('utf-8').decode('ascii', 'ignore'))
    text = text.replace('\t','').replace('\r','').replace('\n','')
    return text.strip()

def clean_key(text):
    if isinstance(text,str):
        text = ''.join([i if ord(i) < 128 else ' ' for i in text])
        text = text.lower()
        text = ''.join([c if 97 <= ord(c) <= 122 or 48 <= ord(c) <= 57 else '_'                                                                                         for c in text ])
        text = re.sub(r'_{1,}', '_', text)
        text = text.strip("_")
        text = text.strip()

        if not text:
            raise Exception("make_key :: Blank Key after Cleaning")

        return text.lower()
    else:
        raise Exception("make_key :: Found invalid type, required str or unicode                                                                                        ")

def traverse( data):
    if isinstance(data, dict):
        n = {}
        for k, v in data.items():
            k = str(k)
            if k.startswith("dflag") or k.startswith("kflag"):
                if k.startswith("dflag_dev") == False:
                    n[k] = v
                    continue

            n[clean_key(clean_value(k))] = traverse(v)

        return n

    elif isinstance(data, list) or isinstance(data, tuple) or isinstance(data, set):                                                                                     
        data = list(data)
        for i, v in enumerate(data):
            data[i] = traverse(v)

        return data
    elif data is None:
        return ""
    else:
        data = clean_value(data)
        return data

class laforet(scrapy.Spider):
    name = 'laforet_lekremlin_PySpider_france_fr'
    allowed_domains = ['www.laforet.com']
    start_urls = ['www.laforet.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.laforet.com/api/immo/properties?page=1&perPage=200"}]
        for urls in start_urls:
            yield scrapy.Request(url=urls.get('url'),
                                 callback=self.parse)




    def parse(self, response, **kwargs):
        json_lod = json.loads(response.body)
        total_pages = json_lod["meta"]["pagination"]["total_pages"]

        for page in range(1,total_pages+1):
            url = "https://www.laforet.com/api/immo/properties?page={}&perPage=200".format(page)
            yield scrapy.Request(
                url=url,
                callback=self.get_page_data
            )
       


    def get_page_data(self, response):

        all_property = json.loads(response.body)
        for url in all_property["data"]:
            if url["type"].lower() in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"] and url["transaction_type"] == "rent":
                yield scrapy.Request(
                url=url["links"]["self"],
                callback=self.get_property_details
                )    
        

    def get_property_details(self,response):
        item = ListingItem()
        property_detail = json.loads(response.body)

        item["external_link"] = "https://www.laforet.com"+property_detail["path"]
        item["external_id"] = str(property_detail["immo_id"])
        item["property_type"] = property_detail["type"].lower()
        item["description"] = property_detail["description"]
        item["currency"] = "EUR"
        item["external_source"] = "laforet_lekremlin_PySpider_france_fr"



        if property_detail["rent"]:
            item["rent"] = int(property_detail["rent"])

        if property_detail["lat"]:
            item["latitude"] = str(property_detail["lat"])

        if property_detail["lng"]:
            item["longitude"] = str(property_detail["lng"])

        if property_detail["deposit"]:
            item["deposit"] = int(property_detail["deposit"])

        if property_detail["rooms"]:
            item["room_count"] = property_detail["rooms"]

        if property_detail["bathrooms"]:
            item["bathroom_count"] = property_detail["bathrooms"]

        if property_detail["floors"]:
            item["floor"] = str(property_detail["floors"])

        if property_detail["surface"]:
            item["square_meters"] = int(property_detail["surface"])     
            
        if property_detail["charges"]:
            item["utilities"] = int(property_detail["charges"])

        if property_detail["dpe_value"]:
            item["energy_label"] = str(property_detail["dpe_value"])

        if item["latitude"] and item["longitude"]:
            location = getAddress(item["latitude"],item["longitude"])
            item["address"] = location.address

        if property_detail["address"]["postcode"]:
            item["zipcode"] = property_detail["address"]["postcode"]

        if property_detail["address"]["city"]:
            item["city"] = property_detail["address"]["city"]

        if property_detail["agency"]["name"]:
            item["landlord_name"] = property_detail["agency"]["name"]

        if property_detail["agency"]["email"]:
            item["landlord_email"] = property_detail["agency"]["email"]

        if property_detail["parkings"]:
            item["parking"] = True

        if property_detail["terraces"]:
            item["terrace"] = True

        if property_detail["has_lift"]:
            item["elevator"] = True

        if property_detail["has_swimming_pool"]:
            item["swimming_pool"] = True

        if property_detail["balconies"]:
            item["balcony"] = True


        imgs_lst = []
        for ech_img in property_detail["photos"]:
            pic = ech_img.replace("https://laforetbusiness.laforet-intranet.com","https://www.laforet.com/media/cache")+"?method=max&size=medium"
            imgs_lst.append(pic)

        if imgs_lst:
            item["images"] = imgs_lst
            item["external_images_count"] = len(imgs_lst)

        print (item)
        yield item
