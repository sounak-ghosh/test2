import scrapy
import js2xml
import re
import math
import json
from bs4 import BeautifulSoup
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)


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


class QuotesSpider(scrapy.Spider):
    name = "Robinsestates_PySpider_united_kingdom"
    allowed_domains = ['www.robinsestates.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='uk'


    start_urls = ['https://www.robinsestates.com/properties-to-let']

    def parse(self, response):
        soup = BeautifulSoup(response.body)
        max_page = getSqureMtr(soup.find("div", class_="pagination pull-right").find("small").text.split("of")[-1])
        for i in range(0, max_page):
            yield scrapy.Request(
                    url='https://www.robinsestates.com/properties-to-let?start={}'.format(i*10), 
                    callback=self.get_external_link)

    def get_external_link(self, response):
        soup1 = BeautifulSoup(response.body)
        for prop in soup1.findAll("div", class_="eapow-property-thumb-holder"):
            yield scrapy.Request(
                url='https://www.robinsestates.com'+prop.find("a")['href'], 
                callback=self.get_property_details,
                meta={"external_link": 'https://www.robinsestates.com'+prop.find("a")['href']})  

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body)

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["title"] = soup2.find("div", class_="eapow-mainheader").find("h1").text.strip()

        images = []
        for img in soup2.find("div", id="carousel").findAll("li"):
            images.append(img.find("img")['src'])

        item["images"]= images
        item["external_images_count"]= len(images)

        description = soup2.find("div", id="propdescription").find("p").text.strip()
        item["description"] = description

        temp_dic = {}
        for temp in soup2.find("div", id="DetailsBox").findAll("div", class_="eapow-sidecol"):
            if temp.find("address"):
                item["address"] = temp.text
            else:
                temp_dic[temp.text.split(':')[0].strip()] = temp.text.split(':')[1].strip()
        temp_dic = cleanKey(temp_dic)
        # print(temp_dic)

        item["external_id"] = temp_dic['ref']

        room_icons = soup2.find("div", id="PropertyRoomsIcons").find("div").text.split()
        item["room_count"] = int(room_icons[0])
        item["bathroom_count"] = int(room_icons[1])


        item["rent"] = getSqureMtr(soup2.find("div", class_="eapow-mainheader").find("h1").text.strip().replace(",", ""))
            
        item["latitude"] = re.findall('lat: "(.+)",' ,str(soup2))[0]
        item["longitude"] = re.findall('lon: "(.+)",' ,str(soup2))[0]

        for sub_desc in soup2.find("ul", id="starItem").findAll("li"):
            print(sub_desc.text.strip())
            if "REFURBISHED" in sub_desc.text.strip():
                item["furnished"] = True

        property_type = "apartment"
        item["property_type"] = property_type

        item["currency"]='EUR'

        item["external_source"] = 'robinsestates.com'


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item
