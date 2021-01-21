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

class spiderQoutes(scrapy.Spider):
    name = 'Capitalestateagents_PySpider_united_kingdom'
    allowed_domains = ['www.capitalestateagents.com']
    start_urls = ['www.capitalestateagents.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = 'https://www.capitalestateagents.com/Search?listingType=6&statusids=1&obc=Price&obd=Descending&areadata=&areaname=&radius=&bedrooms=&minprice=&maxprice='
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        for div in soup.find_all('div',class_='col propertiesBoxIn'):
            rent = int(re.findall('\d+',clean_value(div.find('h2').find('div').text).replace(',',''))[0])
            external_link = 'https://www.capitalestateagents.com/'+div.find('a')['href']
            yield scrapy.Request(url = external_link, callback = self.get_property_details,meta={"rent":rent})
            
        
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        print (response.url)
        soup1= BeautifulSoup(response.body,"html.parser")
        item['external_link'] = response.url
        item["rent"] = response.meta.get("rent")
        item['external_source'] = 'Capital Estate Agents'
        address = soup1.find('h1').text.strip()
        if num_there(address.split(" ")[-1]):
            item["zipcode"] = address.split(" ")[-1]
        item['address'] = address
        item['title'] = soup1.find('h1').text
        item['property_type'] = "apartment"
        item['currency'] = 'GBP'

        city = item["external_link"].split("/")[-3]
        item["city"] = city

        external_id = item["external_link"].split("/")[-1]
        item["external_id"] = external_id

        if clean_value(soup1.find('i',class_="i-bedrooms").find_previous('div').text):
            item['room_count'] = int(clean_value(soup1.find('i',class_="i-bedrooms").find_previous('div').text))
        

        if clean_value(soup1.find('i',class_="i-bathrooms").find_previous('div').text):
            item['bathroom_count'] = int(clean_value(soup1.find('i',class_="i-bedrooms").find_previous('div').text))

        item['description'] = soup1.find('h2',class_='summaryTitle').find_next('div').text

        tt = soup1.find('div',class_='row featuresBox')

        if tt:
            if 'furnished' in tt.text.lower() :
                furnished = True
                item['furnished'] = furnished
            if 'parking' in tt.text.lower() :
                parking = True
                item['parking'] = parking
            if 'elevator' in tt.text.lower() :
                elevator = True
                item['elevator'] = elevator
            if 'balcony' in tt.text.lower() :
                balcony = True
                item['balcony'] = balcony
            if 'terrace' in tt.text.lower() :
                terrace = True
                item['terrace'] = terrace
            if 'swimming' in tt.text.lower() :
                swimming_pool = True
                item['swimming_pool'] = swimming_pool
            if 'washing machine' in tt.text.lower() :
                washing_machine = True
                item['washing_machine'] = washing_machine
            if 'dishwasher' in tt.text.lower() :
                dishwasher = True
                item['dishwasher'] = dishwasher

        imgs = set()
        for li in soup1.find('div',id='detailsRoyalSlider').find_all('a'):
                imgs.add(li['href'])

        if imgs:
            item['images'] = list(imgs)
            item['external_images_count'] = len(imgs) 

        item['landlord_name'] = "Capital Estate Agents"
        item['landlord_phone'] = "0208 313 0010"
        item['landlord_email'] = "info@capitalestateagents.com"

        yield item
  