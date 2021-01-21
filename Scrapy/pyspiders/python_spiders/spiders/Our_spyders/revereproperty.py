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
    name = 'Revereproperty_Co_PySpider_united_kingdom'
    allowed_domains = ['revereproperty.co.uk']
    start_urls = ['revereproperty.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = 'https://revereproperty.co.uk/NewSearch.php?buyrent=1&area=*&bedrooms=-&minprice=0&maxprice=9000000&submit=search'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        temp_list = []
        for ech_prop_det in soup.find_all("div", class_="padcolumn"):
            title = ech_prop_det.find("h5").text.strip()
            temp_dic={}
            for ech_li in ech_prop_det.find("ul").find_all("li"):
                temp_dic[ech_li.find("span",class_="left").text.replace(":","").strip()] = ech_li.find("span",class_="right").text.strip()
            temp_dic = cleanKey(temp_dic)
            if "propertytype" in temp_dic:
                if "Flat".lower() in temp_dic["propertytype"].lower():
                    property_type = "apartment"
                elif "House".lower() in temp_dic["propertytype"].lower():
                    property_type = "house"
                else:
                    property_type = "NA"
            if property_type in ["apartment","house"]:
                if "permonth" in temp_dic:
                    rent = temp_dic["permonth"]
                if "bedrooms" in temp_dic:
                    room_count = temp_dic["bedrooms"]
                external_link = "https://revereproperty.co.uk/"+ech_prop_det.find("h5").find("a")["href"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link, "room_count":room_count, "rent":rent, "property_type":property_type,"title":title})

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        
        external_link = response.meta.get("external_link")
        item["external_link"] = external_link
        
        room_count = response.meta.get("room_count")
        item["room_count"] = int(room_count)

        rent = getPrice(response.meta.get("rent"))
        item["rent"] = rent
        
        property_type = response.meta.get("property_type")
        item["property_type"] = property_type
        
        title = response.meta.get("title")
        item["title"] = title
        
        address = response.meta.get("title")
        item["address"] = address
        
        temp_zipcode = response.meta.get("title").split(",")[-1].strip().split(" ")
        if len(temp_zipcode) > 1:
            if num_there(temp_zipcode[-2]) and num_there(temp_zipcode[-1]):
                zipcode = temp_zipcode[-2]+" "+temp_zipcode[-1]
                item["zipcode"] = zipcode

        item["city"] = "London"

        desc = soup.find("span", class_="left").text.replace(soup.find("span", class_="left").find("a").text,"").replace(" -","").strip()
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

        bath_count_dic = {"one":1, "two":2, "three":3, "four":4, "five":5, "six":6, "seven":7, "eight":8, "nine":9, "ten":10}
        for ech_feature in soup.find_all("span", class_="left txtbold"):
            if "bathroom" in ech_feature.text.lower() or "shower" in ech_feature.text.lower():
                temp_bath_count = ech_feature.text.split(" ")
                for index,get_bath_count in enumerate(temp_bath_count):
                    if "bathroom" in get_bath_count.lower() or "shower" in get_bath_count.lower():
                        if (temp_bath_count[index-1]).strip().lower() in bath_count_dic:
                            bathroom_count =  bath_count_dic[(temp_bath_count[index-1]).strip().lower()]
                        else:
                            bathroom_count = 1
                        item["bathroom_count"] = bathroom_count

        for lat_lon in soup.find_all("ul", class_="list-property-detail bottomsection")[-1].find_all("p"):
            if "View".lower() in lat_lon.text.lower() and "Map".lower() in lat_lon.text.lower():
                for ech_a in lat_lon.find_all("a"):
                    if "View".lower() in ech_a.text.lower() and "Map".lower() in ech_a.text.lower():
                        temp_lat_lon = ech_a["href"].split("/")
                        for get_latlon in temp_lat_lon:
                            if "@" in get_latlon:
                                latitude = get_latlon.split(",")[0].replace("@","").strip()
                                item["latitude"] = latitude
                                longitude = get_latlon.split(",")[1].strip()
                                item["longitude"] = longitude

        image_list = []
        for ech_img in soup.find_all("div", class_="ts-display-pf-img"):
            image_list.append("https://revereproperty.co.uk/"+ech_img.find("img")["src"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        item["external_source"] = "Revereproperty_Co_PySpider_united_kingdom"
        item["currency"] = "GBP"
        item["landlord_name"] = "Revere Property Limited"
        item["landlord_phone"] = "020 7223 3922"
        item["landlord_email"] = "enquiries@revereproperty.co.uk"

        print(item)
        yield item