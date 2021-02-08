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
    name = 'Acepm_Co_PySpider_united_kingdom'
    allowed_domains = ['www.acepm.co.uk']
    start_urls = ['www.acepm.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = f"https://www.acepm.co.uk/properties.php"
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        
        extract_data = re.findall('\={(.*)};',str(soup))
        all_lat_lon = extract_data[0].split("};")

        for ech_prop in soup.find_all("div", class_="imgcont"):
            external_link = "https://www.acepm.co.uk/" + ech_prop.find("a")["href"].replace("./","")
            external_id = external_link.split("=")[-1]
            for _ in all_lat_lon:
                if external_id in _:
                    latitude = _.split(",")[-2].split(":")[-1].replace("'","")
                    longitude = _.split(",")[-1].split(":")[-1].replace("'","")
                    yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_id" : external_id, "latitude" : latitude, "longitude" : longitude})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body) 
        print(response.url)
        item["external_link"] = response.url

        item["external_id"] = response.meta.get("external_id")
        
        item["latitude"] = response.meta.get("latitude")
        
        item["longitude"] = response.meta.get("longitude")

        item["title"] = soup.find("div", id='letpage').find("h1").text.strip()

        address = soup.find("div", id='letpage').find("h1").text.strip()
        item["address"] = address

        item["zipcode"]= address.split(",")[-1].strip()

        item["city"] = address.split(",")[-2].strip()

        item["rent"] = getPrice(soup.find("div", id='prop-text').find("h2").find("span").text)

        temp_date = soup.find("div", id='prop-text').find("h3").find("span").text.strip()
        if num_there(temp_date.replace("- Available ","")):
            item["available_date"] = strToDate(temp_date.replace("- Available ",""))

        funish_proptype = soup.find("div", id='prop-text').find("h3").text.replace(temp_date,"")

        if "flat" in funish_proptype.lower():
            property_type = "apartment"
        elif "terrace" in funish_proptype.lower() or "semi" in funish_proptype.lower():
            property_type = "house"
        item["property_type"] = property_type

        if "unfurnished" in funish_proptype.lower():
            item["furnished"] = False
        elif "furnished" in funish_proptype.lower() or "furnishing" in funish_proptype.lower(): 
            item["furnished"] = True

        item["room_count"] = getSqureMtr(funish_proptype)

        if "information" in soup.find("div", class_="therest__rcol__item").find("h2").text.lower():
            for ech_feat in soup.find("div", class_="therest__rcol__item").find("ul").find_all("li"):   
                # print(ech_feat.text.strip())
                if "deposit" in ech_feat.text.lower():
                    item["deposit"] = getPrice(ech_feat.text.strip())
                if "washing" in ech_feat.text.lower():
                    item["washing_machine"] = True
                if "dishwasher" in ech_feat.text.lower():
                    item["dishwasher"] = True

        desc = ""
        for ech_p in soup.find("div", id='prop-text').find_all("p", recursive = False):
            desc = desc + ech_p.text + "\n"
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
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        images = []
        for ech_img in soup.find("div", class_='flexslider').find_all("li"):
            images.append("https://www.acepm.co.uk/" + ech_img.find("img")["src"].replace("./",""))
        if images:
            item["images"] = images
            item["external_images_count"] = len(images)

        item["landlord_name"] = "ACE Property"
        item["landlord_phone"] = "0131 229 4400"
        item["landlord_email"] = "info@acepm.co.uk"
        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"

        print(item)
        yield item
        