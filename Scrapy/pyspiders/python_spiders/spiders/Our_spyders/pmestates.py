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
# import geopy
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter

# locator = Nominatim(user_agent="myGeocoder")

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng) # "52","76"
#     location = locator.reverse(coordinates)
#     return location

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
    name = "pmestates_com_PySpider_london_en"
    allowed_domains = ['pmestates.com']
    start_urls = ['pmestates.com']
    execution_type = 'testing'
    country = 'london'
    locale ='en'

    def start_requests(self):
        url ="http://pmestates.com/index.asp?IDTSec=rent"
        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body,"html.parser")
        page = int(soup.find_all('a',href=re.compile('javascript:GotoPage'))[-2].text)
        
        url = response.url
        for i in range(1,page+1):
            frm = {'searchSection': 'rent',
                    'searchArea': '',
                    'minBed': '',
                    'maxBed': '',
                    'minPrice': '',
                    'maxPrice': '',
                    'p': str(i)
                }

            yield scrapy.FormRequest(
                url=url, 
                callback=self.get_external_link,
                formdata = frm)

    def get_external_link(self, response):
        soup = BeautifulSoup(response.body,"html.parser")
        for a in soup.find_all('h2'):
            external_link = 'http://pmestates.com/'+a.find('a')['href']
            yield scrapy.Request(
                url=external_link, 
                callback=self.get_property_details
                )

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body,"html.parser")

        external_link = response.url
        print(external_link)
        item["external_link"] = external_link

        external_source = 'pmestates_com_PySpider_london_en'
        rec = {}
        address = soup2.find('h1').text

        rent,room_count = re.findall('\d+',clean_value(soup2.find('h2').text.replace(',','')))

        property_type = ''
        if 'house' in clean_value(soup2.find('h2').text.replace(',','')).lower():
            property_type = 'house'
        if 'apartment' in clean_value(soup2.find('h2').text.replace(',','')).lower():
            property_type = 'apartment'
        if 'studio' in clean_value(soup2.find('h2').text.replace(',','')).lower():
            property_type = 'studio'
        if 'studio' in clean_value(soup2.find('h2').text.replace(',','')).lower():
            property_type = 'studio'
        else:
            property_type = 'NA'
        currency = 'EUR'

        email = soup2.find('a',href=re.compile('info@')).text

        contact = (re.findall('\d{11}',soup2.find('a',href=re.compile('info@')).find_previous('td').text.replace(' ','')))[0]

        landlo = soup2.find('a',href=re.compile('info@')).find_previous('td').find('strong').text

        city = address.split(',')[-1]

        ss = None
        try:
            ss = geolocator.geocode(city)
        except:
            pass

        if ss:
            item['latitude'] = str(ss.latitude)
            item['longitude'] = str(ss.longitude)

        s = None
        try:
            s = geolocator.reverse((rec['latitude'],rec['longitude']))
        except:
            pass
        if s:
            zipcode = s.raw['address'].get('postcode','').strip()
            item['zipcode'] = zipcode

        if int(rent):
            item['rent'] = int(rent)
        if int(room_count):
            item['room_count'] = int(room_count)
        item['city'] = city
        item['address'] = address
        item['property_type'] = property_type
        item['currency'] = currency
        item['external_link'] =external_link
        item['external_source'] = external_source
        item['landlord_name'] = landlo
        item['landlord_email'] = email
        item['landlord_phone'] = contact

        img = set()
        for im in soup2.find_all('img',attrs={'name':re.compile('TI')}):
            img.add('http://pmestates.com/'+im['src'])
        if img:
            images = list(img)
            external_images_count = len(img)
            item['images'] = images
            item['external_images_count'] = external_images_count

        desc = clean_value(soup2.find('h1').find_parent('tr').find_parent('tr').find_parent('tr').find_next_sibling('tr').text)
        item['description'] = desc
        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item
