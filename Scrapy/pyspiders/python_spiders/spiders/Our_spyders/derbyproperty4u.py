# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
from datetime import datetime
import math


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
    name = 'Derbyproperty4u_PySpider_united_kingdom'
    allowed_domains = ['derbyproperty4u.com']
    start_urls = ['derbyproperty4u.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        property_types = ["Apartments","Houses","4-Students"]
        for p_t in property_types:
            start_url = f'https://derbyproperty4u.com/4-Rent/{p_t}/'
            yield scrapy.Request(url = start_url, callback = self.parse1, meta = {"property_type":p_t})

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        property_type = response.meta.get("property_type")
        for ech_prop in soup.find_all("div", class_="content-block clear"):
            for ech_title in ech_prop.find_all("a"):
                if ech_title.find("img"):
                    pass
                else:
                    title = ech_title.text.strip()
                    external_link = "https://derbyproperty4u.com" + ech_title["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type, "title" : title})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")

        item["external_link"] = response.url

        item["title"] = response.meta.get("title")

        temp_prop_type = response.meta.get("property_type")
        if "apartment" in temp_prop_type.lower():
            property_type = "apartment"
        elif "house" in temp_prop_type.lower():
            property_type = "house"
        elif "student" in temp_prop_type.lower():
            property_type = "student_apartment"
        item["property_type"] = property_type

        temp_rent = soup.find("div", class_="property-detail").find("h2").text
        if "£" in temp_rent.lower() and "pppw" in temp_rent.lower():
            rent = 4*getPrice(temp_rent.split("£")[-1])
        elif "£" in temp_rent.lower() and "pcm" in temp_rent.lower():
            rent = getPrice(temp_rent.split("£")[-1])
        item["rent"] = rent

        temp_dic = {}
        for ech_li in soup.find("ul", class_="details").find_all("li"):
            if ech_li.find("label"):
                temp_dic[ech_li.find("label").text.replace(":","").strip()] = ech_li.text.replace(ech_li.find("label").text,"").strip()
        temp_dic = cleanKey(temp_dic)

        if "dp4u" in temp_dic:
            item["external_id"] = temp_dic["dp4u"]
        if "postcode" in temp_dic:
            item["zipcode"] = temp_dic["postcode"]
        if "bathrooms" in temp_dic:
            item["bathroom_count"] = int(temp_dic["bathrooms"])
        if "bedrooms" in temp_dic:
            item["room_count"] = int(temp_dic["bedrooms"])

        image_list = []
        for ech_img in soup.find("ul", class_="property-photos clear").find_all("li"):
            image_list.append("https://derbyproperty4u.com" + ech_img.find("a")["href"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        desc = ""
        for ech_p in soup.find("div", class_="property-detail").find_all("p", recursive = False):
            if ech_p.find("strong") and "address" in ech_p.find("strong").text.lower():
                address = ech_p.text.replace(ech_p.find("strong").text,"").strip()
                item["address"] = address
            else:
                desc = desc + ech_p.text.strip() + "\n"
        
        item["description"] = desc.strip()

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if ("terras" in desc.lower() or "terrace" in desc.lower()) and "end of terrace" not in desc.lower() and "terrace house" not in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "unfurnished" in desc.lower():
            item["furnished"] = False
        elif "furnished" in desc.lower() or "furniture" in desc.lower() and "unfurnished" not in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        item["city"] = "Derby"
        item["currency"] = "GBP"
        item["landlord_name"] = "Derbyproperty4u.com Ltd"
        item["landlord_email"] = "info@derbyproperty4u.com"
        item["landlord_phone"] = "01332 987 830"
        item["external_source"] = "Derbyproperty4u_PySpider_united_kingdom"

        print(item)
        yield item




