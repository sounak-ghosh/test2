# Author: Sounak Ghosh
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


def num_there(s):
    return any(i.isdigit() for i in s)

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date


def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = int(float(list_text[0]+list_text[1]))
    elif len(list_text) == 2:
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
    name = 'Affinity_Home_PySpider_france'
    allowed_domains = ['www.affinity-home.com']
    start_urls = ['www.affinity-home.com']
    execution_type = 'testing'
    country = 'france'
    locale ='en'

    def start_requests(self):
        start_url = 'https://www.affinity-home.com/recherche/location'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        tot_prop = getSqureMtr(soup.find("div", class_="col main_color font-weight-bold").text)
        page_count= math.ceil(tot_prop/12)
        for ech_prop in soup.find_all("div", class_="col-12 position-relative"):
            external_link = "https://www.affinity-home.com" + ech_prop.find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})
        
        for ech_page in range(1,page_count):
            url = f"https://www.affinity-home.com/recherche/location/tous_types/toutes_villes/{ech_page+1}"
            yield scrapy.Request(url = url, callback = self.parse2)

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for ech_prop in soup.find_all("div", class_="col-12 position-relative"):
            external_link = "https://www.affinity-home.com" + ech_prop.find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        
        temp_title = soup.find("h2", class_="text-uppercase").text.strip().split(" ")
        title = ""
        for ech_txt in temp_title:
            if ech_txt:
                title = title + ech_txt.strip() + " "
        if "appartement" in title.lower() or "maison" in title.lower() or "studio" in title.lower():
            if "appartement" in title.lower():
                property_type = "apartment"
                item["property_type"] = property_type

            item["external_link"] = response.meta.get("external_link")
            print(response.meta.get("external_link"))
            item["title"] = title

            rent = getPrice(soup.find("span", class_="annonce_listing_prix main_color").text)
            item["rent"] = rent

            address = soup.find("span", class_="main_color bloc_adresse").text
            item["address"] = address
            
            if "paris" in address.lower():
                city = "paris"
                item["city"] = city
            elif " rue " in address.lower():
                city = ""
                for char in address.lower().split(" rue ")[0]:
                    if not char.isdigit():
                        city = city + char
                item["city"] = city
            else:
                city = address.lower().split(" ")[0]
                item["city"] = city

            for rc_sqm in soup.find_all("span", class_="main_color font-weight-bold text-uppercase bloc_details"):
                if "pièce" in rc_sqm.text.lower() or "pièces" in rc_sqm.text.lower():
                    room_count = getSqureMtr(rc_sqm.text.strip())
                    item["room_count"] = room_count
                if "surface" in rc_sqm.text.lower():
                    square_meters = getSqureMtr(rc_sqm.text.strip())
                    item["square_meters"] = square_meters

            if soup.find("div", class_="col-lg-3 col-12 bloc_details_annonce").find("span", class_="main_color font-weight-bold"):
                if num_there(soup.find("div", class_="col-lg-3 col-12 bloc_details_annonce").find("span", class_="main_color font-weight-bold").text):
                    date = strToDate(soup.find("div", class_="col-lg-3 col-12 bloc_details_annonce").find("span", class_="main_color font-weight-bold").text.replace("disponible :","").strip())
                    item["available_date"] = date
            
            if "Ref" in soup.find("span", class_="mb-3 font-weight-bold d-block").text:
                item["external_id"]=soup.find("span", class_="mb-3 font-weight-bold d-block").text.replace("Ref. :","").strip()

            desc = soup.find("span", class_="font-weight-bold d-block").find_next_sibling().text.strip()
            item["description"] = desc

            if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                item["parking"] = True
            if "terras" in desc.lower() or "terrace" in desc.lower():
                item["terrace"] = True
            if "balcon" in desc.lower() or "balcony" in desc.lower():
                item["balcony"] = True
            if "zwembad" in desc.lower() or "swimming" in desc.lower():
                item["swimming_pool"] = True
            # if "gemeubileerd" in desc.lower() or "furnished" in desc.lower() or "meublé" in desc.lower():
            #     item["furnished"] = True
            if "machine à laver" in desc.lower():
                item["washing_machine"] = True
            if "lave" in desc.lower() and "vaisselle" in desc.lower():
                item["dishwasher"] = True
            if "lift" in desc.lower():
                item["elevator"] = True

            if soup.find("span", class_="text-capitalize"):
                item["furnished"] = True

            image_list = []
            for ech_img in soup.find("div", class_="slider-for").find_all("div", class_="bloc_image_mobile"):
                image_list.append("https://www.affinity-home.com"+ech_img.find("img")["src"])
            if image_list:
                item["images"]=image_list
                item["external_images_count"] = len(image_list)

            item["landlord_phone"] = "01 40 56 98 61"
            item["external_source"] = "Affinity_Home_PySpider_france"
            item["currency"] = "EUR"
            
            temp_all_data = str(soup.find("div", class_="col-lg-3 col-12 bloc_details_annonce")).split("<br/>")

            if "Dépôtdegarantie:".lower() in temp_all_data[-1].replace(" ","").lower():
                list_text = re.findall(r'\d+',temp_all_data[-1])
                if int(list_text[0]) < 10:
                    item["deposit"] = int(list_text[0]+list_text[1])
                else:
                    item["deposit"] = int(list_text[0])

            if "Honorairesdelocation".lower() in temp_all_data[-1].replace(" ","").lower():
                list_text = re.findall(r'\d+',temp_all_data[-1])
                if int(list_text[0]) < 10:
                    item["utilities"] = int(list_text[0]+list_text[1])
                else:
                    item["utilities"] = int(list_text[0])

            if "Dépôtdegarantie:".lower() in temp_all_data[-2].replace(" ","").lower():
                list_text = re.findall(r'\d+',temp_all_data[-2])
                if int(list_text[0]) < 10:
                    item["deposit"] = int(list_text[0]+list_text[1])
                else:
                    item["deposit"] = int(list_text[0])



            # print(item)
            yield item

