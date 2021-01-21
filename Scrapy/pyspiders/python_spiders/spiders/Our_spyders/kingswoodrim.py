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
    name = 'Kingswoodrim_Co_PySpider_united_kingdom'
    allowed_domains = ['www.kingswoodrim.co.uk']
    start_urls = ['www.kingswoodrim.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = 'https://www.kingswoodrim.co.uk/component/propertylab/propertysearch?option=com_propertylab&layout=propertysearch&task=propertysearch&start=0&perpage=20&minprice=1&type=tolet&Itemid=112&address3=&prop_type=&minbeds=0'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        co = int(re.findall('\d+',soup.find('strong').text)[-1])
        page_per = 5

        limit = int(co/page_per)+1

        for i in range(1,limit+1):
            url = 'https://www.kingswoodrim.co.uk/properties/tolet/'+str((i-1)*page_per)+'/'+str(page_per)+'/'+str(i)
            yield scrapy.Request(url = url, callback = self.get_property_list)
            
        
    def get_property_list(self, response, **kwargs):
        sou= BeautifulSoup(response.body,"html.parser")
        for div in sou.find_all('div',id='page_search'):
            rec = {}
            rec['external_link'] = 'https://www.kingswoodrim.co.uk'+div.find('a')['href']
            rec['title'] = div.find('div',class_='listing-title').find('a')['title']
            rec['address'] = rec['title']
            rec['city'] = 'Nottingham'
            rec['external_source'] = 'Kingswoodrim_Co_PySpider_united_kingdom'
            rec['room_count'] = int(div.find('i',class_='icon-show icon-bed').find_next('span').text)
            rec['currency'] = 'GBP'
            rec["property_type"] = "apartment"
            rec['rent'] = int(re.findall('\d+',clean_value(div.find('div',class_='listing-property-price').text.replace(',','')))[0])
            rec['bathroom_count'] = int(div.find('i',class_='icon-show icon-bath').find_next('span').text)

            yield scrapy.Request(url = rec['external_link'], callback = self.get_property_details, meta = rec)

            
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        ext_sou = BeautifulSoup(response.body,"html.parser")
        print (response.url)


        for k,v in response.meta.items():
            try:
                if v:
                    item[k] = v
            except:
                pass

        splt_space = item["address"].split(" ")
        item["zipcode"] = splt_space[-2]+" "+splt_space[-1]
        item["city"] = splt_space[-3].strip().strip(",")

        tt = ext_sou.find('div',class_='single-property-content').find('ul')

        if tt:
            if 'furnished' in tt.text.lower() :
                furnished = True
                item['furnished'] = furnished
            if 'unfurnished' in tt.text.lower() :
                item['furnished'] = False
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

        ext_sou.find('div',class_='single-property-content').find('ul').decompose()

        item['description'] = ext_sou.find('div',class_='single-property-content').text

        lat,lan = re.findall('LatLng\((.*?)\)',str(ext_sou))[0].split(',')

        if float(lat) and float(lan):
            item['latitude'] = lat
            item['longitude'] = lan

        imgs = set()
        for li in ext_sou.find('div',id='property_slider_wrapper').find_all('img'):
                imgs.add(li['src'])
        if imgs:
            item['images'] = list(imgs)


        if imgs:
            item['images'] = list(imgs)
            item['external_images_count'] = len(imgs) 
        item['landlord_name'] = "kingswood"
        item['landlord_phone'] = "0115 704 3163"
        item['landlord_email'] = "enquiries@kingswoodrim.co.uk"

        floor_url = []
        if  ext_sou.find("aside",id="property-search-widget-2"):
            all_div  = ext_sou.find("aside",id="property-search-widget-2").find_all("div",class_="content-widget")
            for div in all_div:
                if "View Floorplan".lower() in div.text.strip().lower():
                    floor_url = [div.find("a")["href"]]
                    item["floor_plan_images"] = floor_url

        if floor_url or imgs:
            item['external_images_count'] = len(imgs) + len(floor_url)

        print (item)
        yield item
  