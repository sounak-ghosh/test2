# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests
# import geopy
# from geopy.geocoders import Nominatim

# geolocator = Nominatim(user_agent="myGeocoder")

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng)
#     location = geolocator.reverse(coordinates)
#     return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = float(list_text[0]+list_text[1])
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

class laforet(scrapy.Spider):
    name = 'beresford_residential_PySpider_united_kingdom_en'
    allowed_domains = ['www.beresfordresidential.com']
    start_urls = ['www.beresfordresidential.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_urls = [{"url":"https://www.beresfordresidential.com/properties/lettings/from-500/up-to-5000"}]
        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        last_page = int(soup.find('div', attrs={'class': 'pagination_footer_wrapper'}).find_all('a')[-1].get('href').split('/page-')[-1])
        for page_no in range(1, last_page+1):
            url_link = 'https://www.beresfordresidential.com/properties/lettings/from-500/up-to-5000/page-' + str(page_no)
            yield scrapy.Request(
                url=url_link,
                callback=self.get_page_details
                )

    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        property_ = soup.find('div', attrs={'id': 'properties'}).find_all('div', attrs={'class': 'propList-inner'})
        for row in property_:
            external_link='https://www.beresfordresidential.com' + row.find('div', attrs={'class': 'row-fluid'}).find('a').get('href')
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )

    def get_property_details(self, response, **kwargs):

        item = ListingItem()
        
        soup = BeautifulSoup(response.body,"html.parser")

        item["external_link"] = response.url

        item['external_id'] = soup.find('li', attrs={'class': 'propertyRef'}).text.replace("Ref:","").strip()

        if soup.find("div",class_="titles"):
            desc = soup.find("div",class_="titles").find("p").text.strip()

            if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                item["parking"] = True
            if "terras" in desc.lower() or "terrace" in desc.lower():
                item["terrace"] = True
            if "balcon" in desc.lower() or "balcony" in desc.lower():
                item["balcony"] = True
            if "zwembad" in desc.lower() or "swimming" in desc.lower():
                item["swimming_pool"] = True
            if "gemeubileerd" in desc.lower() or "furniture" in desc.lower() or "furnished" in desc.lower():
                item["furnished"] = True
            if "machine à laver" in desc.lower() or"washing" in desc.lower():
                item["washing_machine"] = True
            if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
                item["dishwasher"] = True
            if "lift" in desc.lower() or "elevator" in desc.lower():
                item["elevator"] = True

            item["description"] = desc

        photo_links = []
        if soup.find('div', attrs={'id': 'propertyDetailPhotos'}):
            for row in soup.find('div', attrs={'id': 'propertyDetailPhotos'}).find('ul', attrs={'class': 'slides'}).find_all('li'):
                p_link = 'https:' + row.find('img').get('src')
                photo_links.append(p_link)
        if photo_links:
            item['images'] = photo_links
            item['external_images_count'] = len(photo_links)

        data = re.findall("Ctesius.addConfig\('properties',(.+)\.properties\);",str(soup))[0]
        data = data.replace('":null', '":""').replace('":true', '":True').replace('":false', '":False').replace('":None', '":""')
        data = eval(data)
        data = data['properties'][0]

        item["title"] = data["display_address"].strip()
        # print (data["price"].strip())
        if "pw" in data["price"].strip():
            item["rent"] = getPrice(data["price"].strip())*4
        else:
            item["rent"] = getPrice(data["price"].strip())

        item["latitude"] = str(data['lat'])
        item["longitude"] = str(data['lng'])

        if data['bedrooms'] == '':
            item["room_count"] = int(data['bedrooms'])
        try:
            item["room_count"] = int(response.xpath("//li[contains(text(),'Bedrooms')]/text()").extract()[0].replace("Bedrooms","").strip())
        except:
            pass
        try:    
            sq = response.xpath("//div[@class='titles']//text()").extract()
            for s in sq:
                if 'sqm' in s:
                    item['square_meters']   = getSqureMtr(s)
                    break
        except:
            pass
        # location = getAddress(item["latitude"], item["longitude"])
        # if "city" in location.raw["address"]:
        #     item["city"] = location.raw["address"]["city"]
        # if "postcode" in location.raw["address"]:
        #     item["zipcode"] = location.raw["address"]["postcode"]

        item["address"] = data["display_address"]
        
        available_date = soup.find('div', attrs={'id': 'propertyDetails'}).find('p').text.strip()
        if 'Property available on:' in available_date:
            available_date = available_date.replace('Property available on:', '').strip()
            item["available_date"] = format_date(available_date)

        item["landlord_phone"] = "020 7358 7979"
        item["landlord_name"] = "Beresford Residential"
        item["external_source"] = "beresford_residential_PySpider_united_kingdom_en"
        item["currency"] = "EUR"
        item["property_type"] = "apartment"

        print (item)
        yield item
