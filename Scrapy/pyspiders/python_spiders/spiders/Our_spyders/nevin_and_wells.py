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
import json
import time

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

def get_subDetails(ech_prop):
    dic = {}
    external_id = ech_prop["id"]
    dic["external_id"] = str(ech_prop["id"])
    if ech_prop["bedrooms"]:
        dic["room_count"] = ech_prop["bedrooms"]
    address =  ech_prop["displayAddress"]
    dic["address"] = address
    dic["zipcode"] = address.split(",")[-1]
    dic["city"] = address.split(",")[-2]
    
    if "apartment" in ech_prop["propertySubType"].lower() or "flat" in ech_prop["propertySubType"].lower():
        property_type = "apartment"
    elif "bungalow" in ech_prop["propertySubType"].lower() or "terraced" in ech_prop["propertySubType"].lower() or "terrace" in ech_prop["propertySubType"].lower() or "detached" in ech_prop["propertySubType"].lower() or "maisonette" in ech_prop["propertySubType"].lower() or "cottage" in ech_prop["propertySubType"].lower() or "house" in ech_prop["propertySubType"].lower():
        property_type = "house"
    elif "studio" in ech_prop["propertySubType"].lower():
        property_type = "studio"
    else:
        property_type = "house"
    dic["property_type"] = property_type

    external_link = "https://www.rightmove.co.uk/properties/"+str(external_id)
    dic["external_link"] = external_link
    dic["latitude"] = str(ech_prop["location"]["latitude"])
    dic["longitude"] = str(ech_prop["location"]["longitude"])
    dic["rent"] = ech_prop["price"]["amount"]
    dic["currency"] = ech_prop["price"]["currencyCode"]
    dic["landlord_name"] = "Nevin and Wells Residential"
    dic["landlord_phone"] = ech_prop["customer"]["contactTelephone"]
    dic["title"] = ech_prop["propertyTypeFullDescription"]
    
    return dic

class auditaSpider(scrapy.Spider):
    name = 'Nevinandwells_Co_PySpider_united_kingdom'
    allowed_domains = ['www.rightmove.co.uk']
    start_urls = ['www.rightmove.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = "https://www.rightmove.co.uk/api/_search?locationIdentifier=BRANCH%5E60744&numberOfPropertiesPerPage=24&radius=0.0&sortType=6&index=0&includeLetAgreed=true&viewType=LIST&channel=RENT&areaSizeUnit=sqft&currencyCode=GBP&isFetching=false"
        yield scrapy.Request(url=start_url, callback = self.parse)

    def parse(self, response, **kwargs):
        global lst_prop
        lst_prop = []

        json_dic = json.loads(response.body)

        for ech_data in json_dic["properties"]:
            lst_prop.append(get_subDetails(ech_data))


        if "pagination" in json_dic:
            page_count = json_dic["pagination"]["total"]

        for p_g in range(page_count):
            i = 0
            i = i + p_g*24
            time.sleep(1)
            if p_g != 0:
                url = "https://www.rightmove.co.uk/api/_search?locationIdentifier=BRANCH%5E60744&numberOfPropertiesPerPage=24&radius=0.0&sortType=6&index={}&includeLetAgreed=true&viewType=LIST&channel=RENT&areaSizeUnit=sqft&currencyCode=GBP&isFetching=false".format(i)
                print(url)
                yield scrapy.Request(url = url, callback = self.parse1,meta = {"flag_complete" : page_count==p_g+1})

    def parse1(self, response, **kwargs):
        print("i am here")
        json_dic = json.loads(response.body)
        flag = response.meta.get("flag_complete")
        print (len(lst_prop),flag)
        for ech_prop in json_dic["properties"]:
            lst_prop.append(get_subDetails(ech_prop))

        if flag:
            print ("total_data: ",len(lst_prop))

            for ech_p in lst_prop:
                url = ech_p["external_link"] 
                yield scrapy.Request(url = url, callback = self.parse2, meta = ech_p)

    def parse2(self, response, **kwargs):
        item = ListingItem()

        subInfo = response.meta
        for k,v in subInfo.items():
            try:
                item[k] = v
            except:
                pass
        extract_data = re.findall("window.PAGE_MODEL = (.+)}}}",response.body.decode("utf-8"))
        e_p_json_dic =json.loads(extract_data[0]+"}}}")
        desc = e_p_json_dic["propertyData"]["text"]["description"]
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
        for ech_im in e_p_json_dic["propertyData"]["images"]:
            image_list.append(ech_im["url"])
        if image_list:
            item["images"] = image_list

        floorplan_image_list = []
        for ech_fp_im in e_p_json_dic["propertyData"]["floorplans"]:
            floorplan_image_list.append(ech_fp_im["url"])
        if floorplan_image_list:
            item["floor_plan_images"] = floorplan_image_list

        if image_list or floorplan_image_list:
            item["external_images_count"] = len(image_list)+len(floorplan_image_list)

        bathroom_count = e_p_json_dic["propertyData"]["bathrooms"]
        if bathroom_count:
            item["bathroom_count"] = bathroom_count
        if e_p_json_dic["propertyData"]["lettings"]["furnishType"]:
            if "unfurnished" not in e_p_json_dic["propertyData"]["lettings"]["furnishType"].lower():
                item["furnished"] = True
        item["external_source"] = "Nevinandwells_Co_PySpider_united_kingdom"
        print(item)
        yield item
