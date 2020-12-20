# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time
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

    if len(list_text) > 1:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
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


class laforet(scrapy.Spider):
    name = 'snestates_PySpider_uk_en'
    allowed_domains = ['www.snestates.com']
    start_urls = ['www.snestates.com']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'


    def start_requests(self):
        url = "http://www.snestates.com/properties/to-let/?Page=1&O=Price&Dir=ASC&branch=&Country=&Location=&Town=&Area=&MinPrice=&MaxPrice=&MinBeds=&BedsEqual=&sleeps=&propType=&Furn=&FA=&LetType=&Cat=&Avail=&searchbymap=&locations=&SS=&fromdate=&todate=&minbudget=&maxbudget="
        yield scrapy.Request(
            url = url,
            callback=self.parse
            )

    def parse(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        mail = soup.find('div',class_='banner-info').find('a').text
        con = soup.find('div',class_='banner-info').text.replace(mail,'')
        con = con.strip().replace('|','').strip()
        pages = int(re.findall('\d+',soup.find('div',class_='howmany').text)[-1])

        for i in range(1,pages+1):
            url = 'http://www.snestates.com/properties/to-let/?Page={}&O=Price&Dir=ASC&branch=&Country=&Location=&Town=&Area=&MinPrice=&MaxPrice=&MinBeds=&BedsEqual=&sleeps=&propType=&Furn=&FA=&LetType=&Cat=&Avail=&searchbymap=&locations=&SS=&fromdate=&todate=&minbudget=&maxbudget='.format(str(i))

            yield scrapy.Request(
                url = url,
                callback=self.get_page_details
                )


    def get_page_details(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        for li in soup.find_all('div',class_='searchprop'):
            prop_type = li.find('div',class_='proptype').text
            rent = int(re.findall('\d+',li.find(class_='price').text.replace(',',''))[0])
            add = li.find('div',class_='address').text
            
            external_link = 'http://www.snestates.com/'+li.find('a')['href']

            if "tudiant" in prop_type.lower() or  "studenten" in prop_type.lower() and ("appartement" in prop_type.lower() or "apartment" in prop_type.lower()):
                property_type = "student_apartment"
            elif "appartement" in prop_type.lower() or "apartment" in prop_type.lower() or "flat" in prop_type.lower() or "duplex" in prop_type.lower() or "appartement" in prop_type.lower():
                property_type = "apartment"
            elif "woning" in prop_type.lower() or "maison" in prop_type.lower() or "huis" in prop_type.lower():
                property_type = "house"
            elif "chambre" in prop_type.lower() or "kamer" in prop_type.lower():
                property_type = "room"
            elif "studio" in prop_type.lower():
                property_type = "studio"
            else:
                property_type = "NA"

            if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:

                yield scrapy.Request(
                    url = external_link,
                    callback=self.get_property_details,
                    meta = {"property_type":property_type,"address":add,"rent":rent}
                    )



    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print(response.url)

        if soup.find('div',class_='description'):
            description = soup.find('div',class_='description').text.strip()
            if "garage" in description.lower() or "parking" in description.lower() or "autostaanplaat" in description.lower():
                item["parking"]=True
            if "terras" in description.lower() or "terrace" in description.lower():
                item["terrace"]=True
            if "balcon" in description.lower() or "balcony" in description.lower():
                item["balcony"]=True
            if "zwembad" in description.lower() or "swimming" in description.lower():
                item["swimming_pool"]=True
            if "gemeubileerd" in description.lower() or "furnished" in description.lower():
                item["furnished"]=True
            if "machine à laver" in description.lower():
                item["washing_machine"]=True
            if "lave" in description.lower() and "vaisselle" in description.lower():
                item["dishwasher"]=True
            if "lift" in description.lower():
                item["elevator"]=True

            item["description"] = description

        if soup.find('img',src='images/trandot.gif'):
            lat = soup.find('img',src='images/trandot.gif')['onload'].replace('javascript:loadGoogleMap(','').split(',')[0]
            lng = soup.find('img',src='images/trandot.gif')['onload'].replace('javascript:loadGoogleMap(','').split(',')[1]

            s = geolocator.reverse((lat,lng))
            city = s.raw['address'].get('city','')
            zipcode = s.raw['address'].get('postcode','')

            if city:
                item["city"] = city
            if zipcode:
                item["zipcode"] = zipcode

        
        img = set()
        for im in soup.find('div',id='photocontainer').find_all('img'):
            img.add(im['src'])
        img = list(img)
        if img:
            item["images"] = img
            item["external_images_count"] = len(img)


        item["property_type"] = response.meta["property_type"]
        item["rent"] = response.meta["rent"]
        item["external_link"] = response.url
        item["landlord_name"] = "SN ESTATES LONDON LTD"
        item["landlord_phone"] = "02070961297"
        item["landlord_email"] = "sales@snestates.com"
        item["external_source"] = "snestates_PySpider_uk_en"
        item["currency"] = "GBP"
        item["title"] = response.meta["address"]
        item["address"] = response.meta["address"]

        print (item)
        yield item
