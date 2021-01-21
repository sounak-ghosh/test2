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
    name = 'Arlenproperties_Co_PySpider_united_kingdom'
    allowed_domains = ['www.arlenproperties.co.uk']
    start_urls = ['www.arlenproperties.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        property_types = ["Apartment","Flat","Room","Studio"]
        for p_t in property_types:
            start_url = f'https://www.arlenproperties.co.uk/search/?address_keyword=&property_type={p_t}&minprice=&maxprice='
            yield scrapy.Request(url = start_url, callback = self.parse1, meta = {"property_type":p_t})

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        tot_prop = getSqureMtr(soup.find("title").text)
        page_count = math.ceil(tot_prop/10)
        if page_count > 1:
            for ech_pg in range(1,page_count):
                url = f"https://www.arlenproperties.co.uk/search/{ech_pg+1}.html?address_keyword=&property_type={property_type}&minprice=&maxprice="
                yield scrapy.Request(url = url, callback = self.parse2, meta = {"property_type":property_type})
        
        for ech_prop in soup.find_all("div", class_="thumb-shadow"):
            external_link = "https://www.arlenproperties.co.uk" + ech_prop.find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

    def parse2(self, response, **kwargs):
        property_type = response.meta.get("property_type")
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("div", class_="thumb-shadow"):
            external_link = "https://www.arlenproperties.co.uk" + ech_prop.find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        print(response.url)

        item["external_link"] = response.url

        temp_prop_type = response.meta.get("property_type")
        if "Apartment" in temp_prop_type or "Flat" in temp_prop_type:
            property_type = "apartment"
        elif "Room" in temp_prop_type:
            property_type = "room"
        elif "Studio" in temp_prop_type:
            property_type = "studio"
        item["property_type"] = property_type

        item["title"] = ' '.join(soup.find("span", class_="text-orange font-skinny upper").text.strip().split())

        address = soup.find("div", class_="details-address").find("h1").text
        item["address"] = address

        item["city"] = "london"

        if "," in address:
            if len(address.split(",")[-1].strip()) <= 3 and num_there(address.split(",")[-1].strip()):
                zipcode = address.split(",")[-1].strip()
                item["zipcode"] = zipcode
            else:
                temp_city_zip = address.split(",")[-1].split(" ")
                if len(temp_city_zip[-1]) <= 3 and num_there(temp_city_zip[-1]):
                    zipcode = temp_city_zip[-1]
                    item["zipcode"] = zipcode
        else:
            temp_city_zip = address.split(" ")
            if len(temp_city_zip[-1]) <= 3 and num_there(temp_city_zip[-1]):
                zipcode = temp_city_zip[-1]
                item["zipcode"] = zipcode

        item["rent"] = 4*getPrice(soup.find("div", class_="details-address").find("h2").text)

        for ech_det_icon in soup.find("div", class_="details-icons").find_all("img"):
            if "bed" in ech_det_icon["src"] and ech_det_icon["alt"] != "0":
                item["room_count"] = int(ech_det_icon["alt"])
            if "bath" in ech_det_icon["src"] and ech_det_icon["alt"] != "0":
                item["bathroom_count"] = int(ech_det_icon["alt"])

        desc = soup.find("div", id="property-short-description").text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if ("terras" in desc.lower() or "terrace" in desc.lower()) and "end of terrace" not in desc.lower() and "terrace house" not in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "unfurnished" in desc.lower():
            pass
        elif "furnished" in desc.lower() or "furniture" in desc.lower() and "unfurnished" not in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        image_list = []
        if soup.find("div", class_="carousel slide property-images"):
            for ech_img in soup.find("div", class_="carousel slide property-images").find("div", class_="carousel-inner").find_all("div"):
                image_list.append("https://www.arlenproperties.co.uk" + ech_img.find("img")["src"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        extract_data = re.findall('www.google.com(.*);',str(soup))
        lat_lon = extract_data[-1].split("q=")[-1].replace('")','').split("%2C")
        item["latitude"] = lat_lon[0]
        item["longitude"] = lat_lon[1]

        item["external_source"] = "Arlenproperties_Co_PySpider_united_kingdom"
        item["landlord_name"] = "Arlen Properties Ltd"
        item["landlord_phone"] = "020 8203 6833"
        item["landlord_email"] = "mail@arlenproperties.co.uk"
        item["currency"] = "GBP"

        print(item)
        yield item


