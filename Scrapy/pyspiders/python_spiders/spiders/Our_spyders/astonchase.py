# Author: Sounak Ghosh
import scrapy
import js2xml
import re
import math
import json
from bs4 import BeautifulSoup
import requests
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

def getPrice(text):
    list_text = re.findall(r'\d+',text)


    if "," in text:
        if len(list_text) > 1:
            output = float(list_text[0]+list_text[1])
        elif len(list_text) == 1:
            output = int(list_text[0])
        else:
            output=0
    else:
        if len(list_text) > 1:
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
    name = "astonchase_PySpider_united_kingdom_en"
    allowed_domains = ['www.astonchase.com']
    start_urls = ['www.astonchase.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        url ="https://www.astonchase.com/lettings/properties-to-rent/properties-to-rent-in-london/page-1"
        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body,"html.parser")
        
        if soup.find("ul",class_="pagination"):
            tot_page = soup.find("ul",class_="pagination").find_all("li")[-3].find("a")["title"]

        print (tot_page)

        for i in range(1,int(tot_page)+1):
            yield scrapy.FormRequest(
                url="https://www.astonchase.com/lettings/properties-to-rent/properties-to-rent-in-london/page-"+str(i), 
                callback=self.get_external_link)

    def get_external_link(self, response):
        soup = BeautifulSoup(response.body,"html.parser")

        if soup.find('div',class_='section-body').find('ul',class_='properties').find_all('div',class_="property-image"):
            divs = (soup.find('div',class_='section-body').find('ul',class_='properties').find_all('div',class_="property-image"))
            
            for div in divs:

                li = div.find_previous('li')
                rec = {}
                external_link = 'https://www.astonchase.com'+li.find('h5').find('a')['href']
                external_source = 'astonchase_PySpider_united_kingdom_en'
                address = li.find('h5').text
                if li.find('i',class_="icon-bedrooms"):
                    room_count = int(li.find('i',class_="icon-bedrooms").find_previous('span').text)
                    rec['room_count'] = room_count

                rent = int(re.findall('\d+',li.find('div',class_="property-price per-month").text.replace(',',''))[0])
                if li.find('i',class_="icon-bathrooms"):
                    bathroom_count = int(li.find('i',class_="icon-bathrooms").find_previous('span').text)
                    rec['bathroom_count'] = bathroom_count

                rec['external_link'] = external_link
                rec['external_source'] = external_source
                rec['address'] = address
                rec['currency'] = 'EUR'
                rec['rent'] = rent


                yield scrapy.Request(
                    url=external_link, 
                    callback=self.get_property_details,
                    meta = rec
                )

    def get_property_details(self, response):
        item = ListingItem()
        sou = BeautifulSoup(response.body,"html.parser")

        for k,v in response.meta.items():
            try:
                item[k] = v
            except:
                pass


        external_link = response.url
        print(external_link)
        item["external_link"] = external_link
        if sou.find("header",class_ = "section-head"):
            text_val =  (sou.find("header",class_ = "section-head").find("h2").text.strip())
            item["title"] = text_val
            if "house" in text_val.lower():
                item["property_type"] = "house"
            else:
                item["property_type"] = "apartment"
        
        floor_image = []
        if sou.find("img",alt="floorplan"):
            floor_image = [sou.find("img",alt="floorplan")["src"]]
            item["floor_plan_images"] = floor_image

        tt = sou.find('div',id='amenities')
        if tt:
            if 'furnished' in tt.text.lower():
                item['furnished'] = True
            if 'parking' in tt.text.lower():
                item['parking'] = True
            if 'elevator' in tt.text.lower():
                item['elevator'] = True
            if 'balcony' in tt.text.lower():
                item['balcony'] = True
            if 'terrace' in tt.text.lower():
                item['terrace'] = True
            if 'swimming' in tt.text.lower():
                item['swimming_pool'] = True
            if 'washing machine' in tt.text.lower():
                item['washing_machine'] = True
            if 'dishwasher' in tt.text.lower():
                item['dishwasher'] = True

        json_text = "".join(str(sou.find("script",type="application/ld+json")).split())
        match = re.findall(r'>(.*)<',json_text)

        if match:
            dic = json.loads(match[0])
            item['zipcode'] = dic['address']['postalCode']
            item['city'] = dic['address']['addressLocality']
            item['latitude'] = str(dic['geo']['latitude'])
            item['longitude'] = str(dic['geo']['longitude'])

        if sou.find('div',class_='callout-content'):
            item["landlord_name"] = sou.find('div',class_='callout-content').find_all('a')[0].text
            item["landlord_phone"] = sou.find('div',class_='callout-content').find_all('a')[1].text
            item["landlord_email"] = sou.find('div',class_='callout-content').find_all('a')[-1]['href'].replace('mailto: ','')
        imgs = set()
        for im in sou.find('div',class_='section-image').find_all('img'):
            imgs.add(im['src'])

        if imgs:
            item['images'] =  list(imgs)

        if imgs or floor_image:
            item['external_images_count'] = len(imgs)+len(floor_image)

        description = ''
        for p in sou.find('div',class_='section-content').find_all('p',recursive = False):
            description = description+ clean_value(p.text) 
        if description:
            item['description'] = description

        print (item)
        yield(item)
