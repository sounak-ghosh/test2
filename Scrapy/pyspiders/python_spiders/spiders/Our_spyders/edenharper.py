import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import math
import json


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

    # if len(list_text) == 2:
    #     output = int(list_text[0])
    if len(list_text) > 0:
        output = int(list_text[0])
    else:
        output=0

    return output

def getPrice(text):
    list_text = re.findall(r'\d+',text)
    if "." in text:
        if len(list_text) == 3:
            output = int(float(list_text[0]+list_text[1]))
        elif len(list_text) == 2:
            output = int(float(list_text[0]))
        elif len(list_text) == 1:
            output = int(list_text[0])
        else:
            output=0
    else:
        if len(list_text) == 2:
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

class auditaSpider(scrapy.Spider):
    name = 'Edenharper_PySpider_united_kingdom'
    allowed_domains = ['www.edenharper.com']
    start_urls = ['www.edenharper.com']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'
    
    def start_requests(self):
        start_url = 'https://www.edenharper.com/search.ljson?channel=lettings&fragment='
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        temp_props_dic = json.loads(response.body)
        tot_prop = temp_props_dic["pagination"]["total_count"]
        page_count = math.ceil(tot_prop/10)

        for ech_pg in range(1,page_count):
            url = f"https://www.edenharper.com/search.ljson?channel=lettings&fragment=page-{ech_pg+1}"
            yield scrapy.Request(url = url, callback = self.parse2)

        for ech_prop in temp_props_dic["properties"]:
            # print(ech_prop["status"])
            if "To let" in ech_prop["status"]:
                external_link = "https://www.edenharper.com" + ech_prop["property_url"]
                rent = 4*getPrice(ech_prop["price"])
                room_count = ech_prop["bedrooms"]
                bathroom_count = ech_prop["bathrooms"]
                latitude = ech_prop["lat"]
                longitude = ech_prop["lng"]
                external_id = ech_prop["property_id"]
                temp_prop_type = ech_prop["property_type"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"rent":rent, "room_count":room_count, "bathroom_count":bathroom_count, "latitude":latitude, "longitude":longitude, "external_id":external_id, "temp_prop_type":temp_prop_type})

    def parse2(self, response, **kwargs):
        temp_props_dic = json.loads(response.body)
        for ech_prop in temp_props_dic["properties"]:
            # print(ech_prop["status"])
            if "To let" in ech_prop["status"]:
                external_link = "https://www.edenharper.com" + ech_prop["property_url"]
                rent = 4*getPrice(ech_prop["price"])
                room_count = ech_prop["bedrooms"]
                bathroom_count = ech_prop["bathrooms"]
                latitude = ech_prop["lat"]
                longitude = ech_prop["lng"]
                external_id = ech_prop["property_id"]
                temp_prop_type = ech_prop["property_type"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"rent":rent, "room_count":room_count, "bathroom_count":bathroom_count, "latitude":latitude, "longitude":longitude, "external_id":external_id, "temp_prop_type":temp_prop_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        
        print(response.url)
        item["external_link"] = response.url
        
        item["rent"] = response.meta.get("rent")
        item["room_count"] = int(response.meta.get("room_count"))
        item["bathroom_count"] = int(response.meta.get("bathroom_count"))
        item["latitude"] = str(response.meta.get("latitude"))
        item["longitude"] = str(response.meta.get("longitude"))
        item["external_id"]= str(response.meta.get("external_id"))
        temp_prop_type = response.meta.get("temp_prop_type")
        if "apartment" in temp_prop_type or "flat" in temp_prop_type:
            property_type = "apartment"
        elif "house" in temp_prop_type or "maisonette" in temp_prop_type or "detached" in temp_prop_type:
            property_type = "house"
        elif "studio" in temp_prop_type:
            property_type = "studio"
        item["property_type"] = property_type

        address = soup.find("h1", class_="heading__title").text.strip()
        item["address"] = address

        item["title"] = soup.find("h1", class_="heading__title").text.strip()
        
        item["city"] = "london" #sabke cities check kiye to london, ek baar check kar lena

        if "," in address:
            if len(address.split(",")[-1].strip()) <= 3 and num_there(address.split(",")[-1].strip()):
                zipcode = address.split(",")[-1].strip()
                item["zipcode"] = zipcode
                # print(zipcode)
            else:
                temp_city_zip = address.split(",")[-1].split(" ")
                if len(temp_city_zip[-1]) <= 3 and num_there(temp_city_zip[-1]):
                    zipcode = temp_city_zip[-1]
                    item["zipcode"] = zipcode
                    # print(zipcode)
        else:
            temp_city_zip = address.split(" ")
            if len(temp_city_zip[-1]) <= 3 and num_there(temp_city_zip[-1]):
                zipcode = temp_city_zip[-1]
                item["zipcode"] = zipcode
                # print(zipcode)

        desc = ""
        for ech_p in soup.find("div", class_="property--content").find_all("p"):
            if ech_p.text.strip():
                desc = desc + ech_p.text.strip() + "\n"
        item["description"] = desc.strip()

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terrace house" in desc.lower() or "end of terrace" in desc.lower() or "terraced house" in desc.lower():
            pass
        elif "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "part furnished" in desc.lower() and "unfurnished" in desc.lower():
            item["furnished"] = True
        elif "unfurnished" in desc.lower():
            pass
        elif "furnished" in desc.lower() or "furniture" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        image_list = []
        for ech_img in soup.find("div", id="royalSliderInner").find_all("div", class_="rsContent"):
            image_list.append("https:"+ech_img.find("img")["src"])
        if image_list:
            item["images"] = image_list

        floor_image_list = []
        if soup.find("div", id="floorplan").find("img"):
            floor_image_list.append(soup.find("div", id="floorplan").find("img")["src"])
        if floor_image_list:
            item["floor_plan_images"] = floor_image_list

        if image_list or floor_image_list:
            item["external_images_count"] = len(image_list) + len(floor_image_list)

        if len(soup.find("div", id="epc").find("div", class_="col-sm-7 col-md-8").find_all("img")) > 1:
            for findig_ee in soup.find("div", id="epc").find("div", class_="col-sm-7 col-md-8").find_all("img"):
                if "ee" in findig_ee["src"].split("/")[-1].lower():
                    item["energy_label"] = str(int(findig_ee["src"].split("/")[-1].split("_")[-2])) + " kWhEP/m².an" #not sure about units check it once

        for ech_feat in soup.find("div", class_="property--content").find("div", class_="container").find_all("li"):
            if "no parking" in ech_feat.text.lower():
                pass
            elif "parking" in ech_feat.text.lower():
                item["parking"] = True
            if "end of terrace" in ech_feat.text.lower():
                pass
            elif "terrace" in ech_feat.text.lower():
                item["terrace"] = True
            if "balcony" in ech_feat.text.lower():
                item["balcony"] = True
            if "unfurnished" in ech_feat.text.lower():
                pass
            elif "furnished" in ech_feat.text.lower():
                item["furnished"] = True
            if "washing" in ech_feat.text.lower():
                item["washing_machine"] = True

        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"
        item["landlord_phone"] = soup.find("p", class_="branch--phone").text.strip()
        if "battersea" in soup.find("p", class_="branch--title").text.strip().lower():
            item["landlord_name"] = "Eden Harper estate agency battersea branch"
            item["landlord_email"] = "battlets@edenharper.com"
        elif "brixton" in soup.find("p", class_="branch--title").text.strip().lower():      
            item["landlord_name"] = "Eden Harper estate agency brixton branch"
            item["landlord_email"] = "brixlets@edenharper.com"

        print(item)
        yield item


