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
    name = 'Oyster_Properties_Co_PySpider_united_kingdom'
    allowed_domains = ['www.oyster-properties.co.uk']
    start_urls = ['www.oyster-properties.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = 'https://www.oyster-properties.co.uk/property-search/?department=residential-lettings&address_keyword'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        all_page = soup.find("ul",class_="page-numbers")

        if all_page and all_page.find_all("a",class_="page-numbers"):
            tot_page = all_page.find_all("a",class_="page-numbers")[-2].text.strip()
            print ("totalPage>>>>>",tot_page)

            for ech_page in range(int(tot_page)):
                url = 'https://www.oyster-properties.co.uk/property-search/page/{}/?department=residential-lettings&address_keyword'.format(ech_page+1)
                yield scrapy.Request(url = url, callback = self.get_property_list, dont_filter=True)
    
    def get_property_list(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for li in soup.find('ul',class_='properties clear').find_all('li'):
            external_link = li.find('a')['href']
            yield scrapy.Request(url=external_link, callback=self.get_property_details, dont_filter=True)

        
    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")

        print (response.url)
        address = soup.find('h1').text
        split_space = address.split(" ")
        split_comma = address.split(",")
        zipcode = split_space[-2]+" "+split_space[-1]
        city = split_comma[-1].replace(zipcode,"").strip()

        item["city"] = city
        item["zipcode"] = zipcode
        item["external_link"] = response.url
        item['landlord_phone'] = soup.find('a',title='Call Us').text.replace(' ','')
        item['landlord_email'] = soup.find('a',title='Mail Us').text.replace(' ','')
        item['landlord_name'] = 'Oyster properties'
        item['address'] = address
        item['external_source'] = 'Oyster_Properties_Co_PySpider_united_kingdom'
        item['title'] = soup.find('h1').text.strip()
        item['property_type'] = 'apartment'

        if soup.find('div',class_='features-wrapper').find('span',class_='meta-numbers'):
            item['room_count'] = int(re.findall('\d+',soup.find('div',class_='features-wrapper').find('span',class_='meta-numbers').text)[0])
        
        item['rent'] = int(re.findall('\d+',clean_value(soup.find('span',class_='property-price').text.replace(',','')))[0])
        item['currency'] = 'GBP'
        if soup.find('div',class_='features-wrapper').find('span',class_='meta-numbers'):
            item['bathroom_count'] = int(re.findall('\d+',soup.find('div',class_='features-wrapper').find_all('span',class_='meta-numbers')[1].text)[0])
    
        item['external_id'] = item["external_link"].split('/')[-2]

        lat,lan = re.findall('LatLng\((.*?)\);',str(soup))[0].split(',')
        item['latitude'] = str(lat)
        item['longitude'] = str(lan)

        item['description'] = soup.find('p',class_='room').text.replace('*ZERO DEPOSIT AVAILABLE**\n\n','').replace('*','')

        imgs = set()
        for li in soup.find('div',class_='images').find_all('li'):
            if li.find('a'):
                imgs.add(li.find('a')['href'])
        if imgs:
            item['images'] = list(imgs)
            item['external_images_count'] = len(imgs)  

        tt = soup.find('div',class_='features-wrapper')
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
        print (item)
        yield item