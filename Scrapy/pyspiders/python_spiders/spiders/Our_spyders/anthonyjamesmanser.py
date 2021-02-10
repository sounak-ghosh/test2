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
    name = 'Anthonyjamesmanser_Co_PySpider_united_kingdom'
    allowed_domains = ['www.anthonyjamesmanser.co.uk']
    start_urls = ['www.anthonyjamesmanser.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        prop_types = ["Detached%2CSemi-Detached%2CTerraced%2CMaisonette","Apartment"]
        for p_t in prop_types:
            start_url = f"https://www.anthonyjamesmanser.co.uk/search/?showstc=on&showsold=on&instruction_type=Letting&address_keyword=&minprice=&maxprice=&property_type={p_t}"
            yield scrapy.Request(url = start_url, callback = self.parse1, meta = {"property_type":p_t})

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        page_count = math.ceil(getSqureMtr(soup.find("h1").text)/9)
        if page_count > 1:
            for ech_pg in range(1,page_count):
                url = f"https://www.anthonyjamesmanser.co.uk/search/{ech_pg+1}.html?showstc=on&showsold=on&instruction_type=Letting&address_keyword=&minprice=&maxprice=&property_type={property_type}"
                yield scrapy.Request(url = url, callback = self.parse2, meta = {"property_type":property_type})

        for ech_prop in soup.find_all("div", class_="property thumbnails-container"):
            external_link = "https://www.anthonyjamesmanser.co.uk" + ech_prop.find("h3").find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type":property_type})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        for ech_prop in soup.find_all("div", class_="property thumbnails-container"):
            external_link = "https://www.anthonyjamesmanser.co.uk" + ech_prop.find("h3").find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body) 
        print(response.url)
        
        item["external_link"] = response.url
        
        temp_prop_type = response.meta.get("property_type")
        if "Apartment" in temp_prop_type:
            property_type = "apartment"
        else:
            property_type = "house"
        item["property_type"] = property_type

        item["title"] = soup.find("h1").find("span", itemprop="name").text

        address = soup.find("h1").find("span", itemprop="name").text
        item["address"] = address
        
        if "," in address:
            if address.split(",")[-1].strip():
                item["city"] = address.split(",")[-1].strip()

        item["rent"] = getPrice(soup.find("div", class_="property-price spacer-bottom").find("span", itemprop="price").text.strip())

        if soup.find("span", class_="property-bedrooms"):
            item["room_count"] = int(soup.find("span", class_="property-bedrooms").text)

        if soup.find("span", class_="property-bathrooms"):
            item["bathroom_count"] = int(soup.find("span", class_="property-bathrooms").text)

        desc = soup.find("span", itemprop="description").text
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terrace house" in desc.lower() or ("end" in desc.lower() and "terrace" in desc.lower()) or "terraced house" in desc.lower():
            pass
        elif "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "unfurnished" in desc.lower():
            pass
        elif "furnished" in desc.lower() or "furnishing" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        extract_data = re.findall('www.google.com(.*);',str(soup))
        lat_lon = extract_data[-1].split("q=")[-1].replace('")','').split("%2C")
        item["latitude"] = lat_lon[0]
        item["longitude"] = lat_lon[1]

        images = []
        for ech_img in soup.find("div", class_="carousel-inner").find_all("div"):
            images.append("https://www.anthonyjamesmanser.co.uk" + ech_img.find("img")["src"])
        if images:
            item["images"] = images
            item["external_images_count"]= len(images)
            
        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"
        item["landlord_name"] = "Anthony James Manser Estate Agents"
        item["landlord_phone"] = "020 8568 2992"
        item["landlord_email"] = "let@anthonyjamesmanser.co.uk"

        print(item)
        yield item



