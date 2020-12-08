import scrapy
import js2xml
import re
import json
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from scrapy.selector import Selector

locator = Nominatim(user_agent="myGeocoder")

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng) # "52","76"
    location = locator.reverse(coordinates)
    return location

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


class QuotesSpider(scrapy.Spider):
    name = "Ivylettings_PySpider_united_kingdom"
    allowed_domains = ['www.ivylettings.com']
    start_urls = ['www.ivylettings.com']
    execution_type = 'testing'
    country = 'french'
    locale ='fr'

    def start_requests(self):
        url = 'https://www.ivylettings.com/umbraco/Apartment/Search/GetResults?minPrice=0&maxPrice=0&bedrooms=&bathrooms=&features=&sleeps=&area=&searchText=&orderByField=nodeName&orderByDescending=false'
        headers =  {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
        yield scrapy.http.Request(url, headers=headers)

    def parse(self, response):
        my_bytes_value = response.body
        my_json = my_bytes_value.decode('utf8')
        data = json.loads(my_json)
        for json_data in data["Apartments"]:
            if "https" in json_data.get("Url"):
                link = json_data.get("Url")
            else:
                link = "https://www.ivylettings.com" + json_data.get("Url")
                
            yield scrapy.Request(
                url=link, 
                callback=self.get_property_details, 
                meta={'external_link': link,
                        'title': json_data.get("Name"),
                        'rent': json_data.get("Price"),
                        'room': json_data.get("Bedrooms"),
                        'bathroom': json_data.get("Bathrooms"),
                        'lat': json_data["Location"][0],
                        'lng':json_data["Location"][1]})

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body)

        item["external_link"]  = response.meta.get('external_link')
        print(response.meta.get('external_link'))

        item["title"] = response.meta.get('title')

        item["rent"] = response.meta.get('rent') * 30

        item["room_count"] = getSqureMtr(response.meta.get('room'))

        item["bathroom_count"] = getSqureMtr(response.meta.get('bathroom'))
        
        images = []
        for img in soup2.findAll("div", class_="houseslider__image"):
            try:
                images.append("https://www.ivylettings.com"+img.find("img")['src'])
            except Exception as e:
                pass    
        item["images"]= list(set(images))
        item["external_images_count"]= len(images)    

        description = soup2.find("div", class_="houseview__detail-section").text.strip()
        item["description"] = description

        item["latitude"] = response.meta.get('lat')
        item["longitude"] = response.meta.get('lng')
        location = getAddress(response.meta.get('lat'), response.meta.get('lng'))
        item["address"] = location.address
        item["zipcode"]= location.raw["address"]["postcode"]


        if "apartment" in description.lower():
            property_type = "apartment"
        elif "house" in description.lower():
            property_type = "house"
        elif "home" in description.lower():
            property_type = "house"
        else:
            property_type = "NA"

        item["property_type"] = property_type

        item["square_meters"] = getSqureMtr(soup2.find("div", class_="houseview__facts").find("dl", class_="factlist factlist--2").find("dd").text)

        item["currency"]='GBP' 
        item["external_source"] = 'Ivylettings_PySpider_united_kingdom'

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item