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
    name = 'Kalmars_PySpider_united_kingdom'
    allowed_domains = ['www.kalmars.com']
    start_urls = ['www.kalmars.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = 'https://www.kalmars.com/property-lettings/properties-to-rent-in-london'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        tot_prop = getSqureMtr(soup.find("div", class_="col-md-5").find("small").text)
        page_count = math.ceil(tot_prop/9)

        for ech_prop in soup.find_all("a", class_="address-details"):
            external_link = "https://www.kalmars.com"+ech_prop["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})
        for ech_pg in range(1,page_count):
            url = f"https://www.kalmars.com/property-lettings/properties-to-rent-in-london/page-{ech_pg+1}"
            yield scrapy.Request(url = url, callback = self.parse2)

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("a", class_="address-details"):
            external_link = "https://www.kalmars.com"+ech_prop["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
    
        item["external_link"] = response.meta.get("external_link")
        
        address = soup.find("header", class_="section-head").find("div", class_="col-sm-12 col-md-8").find("h2").text.strip()
        item["address"] = soup.find("header", class_="section-head").find("div", class_="col-sm-12 col-md-8").find("h2").text.strip()
        
        item["title"] = soup.find("header", class_="section-head").find("div", class_="col-sm-12 col-md-8").find("h2").text.strip()
                
        item["zipcode"]= address.split(",")[-1].strip()

        item["city"] = "London"

        item["rent"] = 4*getPrice(soup.find("span", class_="price-qualifier").text)

        for ech_listdetail_li in soup.find("div", class_="section-aside").find("ul", class_="list-details").find_all("li"):
            if "property type" in ech_listdetail_li.find("h5").text.replace(":","").lower():
                if "studio" in ech_listdetail_li.find("h6").text.lower():
                    property_type = "Studio"
                elif "apartment" in ech_listdetail_li.find("h6").text.lower():
                    property_type = "Apartment"
                elif "house" in ech_listdetail_li.find("h6").text.lower():
                    property_type = "House"
                item["property_type"] = property_type.lower()

            if "bedroom" in ech_listdetail_li.find("h5").text.replace(":","").lower():
                room_count = int(ech_listdetail_li.find("h6").text)
                item["room_count"] = room_count

        floorplan_image_list = []
        if soup.find("div", id="modal-floorplans").find_all("div", class_="slide"):
            floorplan_image_list.append(soup.find("div", id="modal-floorplans").find("div", class_="slide").find("img")["src"])
        if floorplan_image_list:
            item["floor_plan_images"] = floorplan_image_list
                
        image_list = []
        for ech_img in soup.find("div", class_="slider slider-gallery").find_all("div", class_="slide"):
            image_list.append(ech_img.find("img")["src"])
        if image_list:
            item["images"] = image_list
        
        if image_list or floorplan_image_list:
            item["external_images_count"] = len(image_list)+len(floorplan_image_list)

        desc = soup.find("div", class_="section-content property-section").find("p").text
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if ("terras" in desc.lower() or "terrace" in desc.lower()) and "end of terrace" not in desc.lower() and "terrace house" not in desc.lower():
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

        item["landlord_name"] = soup.find("div", class_="card-content").find("h5").text.strip()
        item["landlord_email"] = soup.find("div", class_="card-content").find("h6").find("a",class_="mail").text.strip()
        item["landlord_phone"] = soup.find("div", class_="card-content").find("h6").find("a",class_="tel").text.strip()
        
        extract_data = re.findall("startekDetailsMap(.+);",str(soup))
        lat_lon = extract_data[0].split(",")
        item["latitude"] = lat_lon[1].strip().replace("'","")
        item["longitude"] = lat_lon[2].strip().replace("'","")

        item["currency"] = "GBP"
        item["external_source"] = "Kalmars_PySpider_united_kingdom"

        print(item)
        yield item