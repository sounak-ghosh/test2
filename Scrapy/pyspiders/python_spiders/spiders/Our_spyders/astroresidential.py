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
    name = 'Astroresidential_Co_PySpider_united_kingdom'
    allowed_domains = ['www.astroresidential.co.uk']
    start_urls = ['www.astroresidential.co.uk']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'
    
    def start_requests(self):
        start_url = 'https://www.astroresidential.co.uk/properties/lettings'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        page_count = 0
        for page in soup.find("div", class_="pagination_footer_wrapper").findAll("li"):
            if num_there(page.text) and int(page.text) > page_count:
                page_count = int(page.text)
        for ech_pg in range(1,page_count):
            url = f"https://www.astroresidential.co.uk/properties/lettings/page-{ech_pg+1}"
            yield scrapy.Request(url = url, callback = self.parse2)

        for ech_prop in soup.find_all("div", class_="propList-inner"):
            external_link = "https://www.astroresidential.co.uk" + ech_prop.find("a")["href"]
            title = ech_prop.find("a").find("div", class_="span6").find("h4").text
            rent = getPrice(ech_prop.find("h5", class_="propertyPrice").text.strip())
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"title": title,"rent": rent})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("div", class_="propList-inner"):
            external_link = "https://www.astroresidential.co.uk" + ech_prop.find("a")["href"]
            title = ech_prop.find("a").find("div", class_="span6").find("h4").text
            rent = getPrice(ech_prop.find("h5", class_="propertyPrice").text.strip())
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"title" : title,"rent": rent})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body) 
        print(response.url)
        item["external_link"] = response.url
        
        item["external_id"]  = response.url.split("/")[-2].strip()

        title = response.meta.get("title")
        item["title"] = title

        check_city = ["flat","apartment","house","maisonette"]
        for c_c in check_city:
            if c_c in title.lower():
                city = title.lower().split(c_c)[-1].strip().title()
                if "*" in city:
                    city = city.split("*")[0].title()
        item["city"] = city
        # address nahi hai, city ko address kar sakte hai maine item mai yield nahi kiya hai address ko

        if "studio" in title.lower():
            property_type = "studio"
        elif "apartment" in title.lower() or "flat" in title.lower():
            property_type = "apartment"
        elif "house" in title.lower() or "maisonette" in title.lower():
            property_type = "house"
        item["property_type"] = property_type
        
        item["rent"] = response.meta.get("rent")

        if "to let" in soup.find("div", class_="sectionContent").find("h3", class_="nobox").text.lower():
            
            desc = ""
            for ech_p in soup.find("div", class_="sectionContent").find_all("p", recursive=False):
                if ech_p.find("strong"):
                    item["available_date"] = strToDate(ech_p.text.replace(ech_p.find("strong").text,"").strip())
                else:
                    desc = desc + ech_p.text.strip() + " "
            desc = desc.strip()
            item["description"] = desc

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

            for bed_bath in soup.find("div", class_="span6 propDetails").find_all("li"):
                if "bedroom" in bed_bath.text.lower():
                    item["room_count"] = getSqureMtr(bed_bath.text)
                if "bathroom" in bed_bath.text.lower():
                    item["bathroom_count"] = getSqureMtr(bed_bath.text)
                
            images = []
            for ech_img in soup.find("div", id="carousel_contents").find_all("a", class_="fancybox"):
                images.append("https:" + ech_img["href"])   #there are some properties with awaiting images which can't be filtered out
            if images:
                item["images"] = images
                item["external_images_count"] = len(images)

            extract_data = re.findall('position: new google.maps.LatLng(.+),',str(soup))
            lat_lon = extract_data[0].split(",")
            item["latitude"] = lat_lon[0].replace("(","").strip()
            item["longitude"] = lat_lon[1].replace(")","").strip()

            item["currency"] = "GBP"
            item["external_source"] = auditaSpider.name
            item["landlord_name"] = "ARPLM. Ltd"
            item["landlord_phone"] = "020 3876 5057"
            item["landlord_email"] = "lettings@astroresidential.co.uk"

            print(item)
            yield item
