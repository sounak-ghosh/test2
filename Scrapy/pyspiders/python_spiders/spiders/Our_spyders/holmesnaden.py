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
    name = 'Holmesnaden_PySpider_united_kingdom'
    allowed_domains = ['www.holmesnaden.com']
    start_urls = ['www.holmesnaden.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = "https://www.holmesnaden.com/search?listingType=6&statusids=1&obc=Price&obd=Descending&areainformation=&radius=&minprice=&maxprice=&bedrooms="
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("div", class_="realCol sixWide twelveWide port-item mix"):
            temp_dic = {}
            external_link = "https://www.holmesnaden.com" + ech_prop.find("a", class_="fdLinks")["href"]
            
            temp_dic["external_link"] = "https://www.holmesnaden.com" + ech_prop.find("a", class_="fdLinks")["href"]
            
            temp_dic["title"] = ech_prop.find("a", class_="fdLinks").find("h2").text
            
            temp_dic["rent"] = getPrice(ech_prop.find("div", class_="featuredProPrice").find("div", {"data-bind":"with: $root.modal"}).text.strip())
            
            bed_recep_bath = ech_prop.find("div", class_="itemRooms").text.strip().split(",")
            for index,find_bed_bath in enumerate(ech_prop.find("div", class_="itemRooms").find_all("span")):
                if "bed" in find_bed_bath.find("i")["class"][0]:
                    if num_there(bed_recep_bath[index]):
                        temp_dic["room_count"] = int(bed_recep_bath[index].strip())
                if "bath" in find_bed_bath.find("i")["class"][0]:
                    if num_there(bed_recep_bath[index]):
                        temp_dic["bathroom_count"] = int(bed_recep_bath[index].strip())

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

        address = response.meta.get("title")
        item["address"] = address

        item["property_type"] = "house"
        
        item["zipcode"] = address.split(",")[-1].strip()

        item["city"] = address.split(",")[-2].strip().capitalize()

        desc = soup.find("div", class_="descriptionsColumn").text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "mid terrace" in desc.lower() or "mid-terrace" in desc.lower() or "terraced house" in desc.lower():
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
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.lower():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        floorplan_image_list = []
        if soup.find("div", class_="col fl-twelveWide lg-twelveWide md-sixWide sm-twelveWide"):
            floorplan_image_list.append(soup.find("div", class_="col fl-twelveWide lg-twelveWide md-sixWide sm-twelveWide").find("a")["href"])
        if floorplan_image_list:
            item["floor_plan_images"] = (floorplan_image_list)

        images = []
        for ech_img in soup.find("div", class_="royalSlider rsDefault visibleNearby").find_all("a"):
            images.append(ech_img["href"])
        if images:
            item["images"] = images
        if images or floorplan_image_list:
            item["external_images_count"] = len(images) + len(floorplan_image_list)

        item["landlord_email"] = "lettings@holmesnaden.com"
        item["landlord_phone"] = " 01625 560535"
        item["landlord_name"] = "Holmes Naden Estate Agents"
        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"

        print(item)
        yield item
