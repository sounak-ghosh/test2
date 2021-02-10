import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
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

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

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
    name = 'Placesbirmingham_Co_PySpider_united_kingdom'
    allowed_domains = ['placesbirmingham.co.uk']
    start_urls = ['placesbirmingham.co.uk']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'
    
    def start_requests(self):
        data = {"type": "rent", "area": "", "price": "", "bedrooms": "", "showSold": "false"}
        start_url = 'https://placesbirmingham.co.uk/wp-content/themes/places/ajax/propertyFilter.php'
        yield scrapy.FormRequest(url = start_url, callback = self.parse1, method = "POST", formdata = data)

    def parse1(self, response, **kwargs):
        temp_props_dic = json.loads(response.body)
        for ech_prop in temp_props_dic:
            temp_dic = {}
            external_link = "https://placesbirmingham.co.uk/property/?id=" + ech_prop["pID"]
            temp_dic["external_link"] = "https://placesbirmingham.co.uk/property/?id=" + ech_prop["pID"]
            
            if int(ech_prop["propertyBedrooms"]) > 0:
                temp_dic["room_count"] = int(ech_prop["propertyBedrooms"])
            
            if int(ech_prop["propertyBathrooms"]) > 0:
                temp_dic["bathroom_count"] = int(ech_prop["propertyBathrooms"])
            
            address = ""
            if ech_prop["addressName"]:
                address = address + ech_prop["addressName"] + ", "
            if ech_prop["addressNumber"]:
                address = address + ech_prop["addressNumber"] + ", "
            if ech_prop["addressStreet"]:
                address = address + ech_prop["addressStreet"] + ", "
            if ech_prop["address2"]:
                address = address + ech_prop["address2"] + ", "
            if ech_prop["address3"]:
                address = address + ech_prop["address3"] + ", "
            if ech_prop["address4"]:
                address = address + ech_prop["address4"] + ", "
            if ech_prop["addressPostcode"]:
                address = address + ech_prop["addressPostcode"]

            if address:
                temp_dic["address"] = address
            
            temp_dic["zipcode"] = ech_prop["addressPostcode"]
            
            temp_dic["city"] = address.split(",")[-2].strip()
            
            temp_prop_type = ech_prop["displayPropertyType"]
            if "studio" in temp_prop_type.lower():
                property_type = "studio"
            elif "apartment" in temp_prop_type.lower() or "flat" in temp_prop_type.lower():
                property_type = "apartment"
            else:
                property_type = "apartment"
            temp_dic["property_type"] = property_type

            if "m" in ech_prop["floorAreaUnits"]:
                square_meters = getSqureMtr(ech_prop["floorArea"])
            if "ft" in ech_prop["floorAreaUnits"]:
                square_meters = int(0.092903 * getSqureMtr(ech_prop["floorArea"]))
            if square_meters > 0:
                temp_dic["square_meters"] = square_meters

            desc = ech_prop["fullDescription"].strip()
            temp_dic["description"] = desc

            #parking mai error aa raha hai, pass nahi ho raha hai
            if "does not have parking" in desc.lower() or "does not come with parking" in desc.lower() or "does not have secure off road parking" in desc.lower() or "has no secure parking" in desc.lower():
                pass
            elif "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                temp_dic["parking"] = True
            if "terrace house" in desc.lower() or "end of terrace" in desc.lower() or "terraced house" in desc.lower():
                pass
            elif "terras" in desc.lower() or "terrace" in desc.lower():
                temp_dic["terrace"] = True
            if "balcon" in desc.lower() or "balcony" in desc.lower():
                temp_dic["balcony"] = True
            if "zwembad" in desc.lower() or "swimming" in desc.lower():
                temp_dic["swimming_pool"] = True
            if "unfurnished" in desc.lower():
                pass
            elif "furnished" in desc.lower() or "furnishing" in desc.lower(): 
                temp_dic["furnished"] = True
            if "machine à laver" in desc.lower() or"washing" in desc.lower():
                temp_dic["washing_machine"] = True
            if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
                temp_dic["dishwasher"] = True
            if "lift" in desc.lower() or "elevator" in desc.lower():
                temp_dic["elevator"] = True

            if ech_prop["latitude"]:
                temp_dic["latitude"] = ech_prop["latitude"]

            if ech_prop["longitude"]:
                temp_dic["longitude"] = ech_prop["longitude"]

            images = ech_prop["images"]
            if images:
                temp_dic["images"] = images
                temp_dic["external_images_count"] = len(images)

            temp_dic["rent"] = getPrice(ech_prop["rent"])

            if int(ech_prop["floorplans"]) > 0:            #no floorplan in any property if it appears we can code later
                pass

            if int(ech_prop["epcGraphs"]) > 0:             #no epc in any property
                pass

            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = temp_dic)

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        
        print(response.url)
        
        for key, val in response.meta.items():
            try:
                item[key] = val
            except:
                pass

        title = []
        for ech_h1 in soup.find("div", class_="grid__item palm--one-whole desk--three-quarters").find_all("h1"):
            title.append(ech_h1.text.strip())
        title = " ".join(title)
        item["title"] = (title)

        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"
        item["landlord_phone"] = "0121 633 0744"
        item["landlord_name"] = "PLACES Birmingham Limited"

        print(item)
        yield item

