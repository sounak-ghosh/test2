import scrapy
import js2xml
import re
import math
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

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
    name = "cjhole_PySpider_unitedkingdom_en"
    allowed_domains = ['www.cjhole.co.uk']
    start_urls = ['www.cjhole.co.uk']
    execution_type = 'testing'
    country = 'unitedkingdom'
    locale ='en'

    def start_requests(self):
        url ='https://www.cjhole.co.uk/property?location=&intent=rent&include-sold=rent'

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body)
        max_prop = getSqureMtr(soup.find("div", class_="row pagination").find("h4").text)
        n = math.ceil(max_prop/24)
        i = 1
        while i <= n:
            sub_url = 'https://www.cjhole.co.uk/property?p={}&per-page=24&intent=rent&price-per=pcm&include-sold=rent&sort-by=price-desc'.format(i)
            i = i + 1
            yield scrapy.Request(
                url=sub_url,
                callback=self.get_external_link)

    def get_external_link(self, response):
        soup1 = BeautifulSoup(response.body)
        for el in soup1.find("div", class_="row property-index").findAll("div", class_="item col-12 p-4 my-2 shadow"):
            # print(el.find("div", class_="col-12 col-lg-3 links").find("a")['href'])
            yield scrapy.Request(
                url=el.find("div", class_="col-12 col-lg-3 links").find("a")['href'], 
                callback=self.get_property_details, 
                meta={'external_link': el.find("div", class_="col-12 col-lg-3 links").find("a")['href']})

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body)

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["currency"]='EUR'

        item["rent"] = getSqureMtr(soup2.find("strong", id="propertyPrice").text.strip().split('|')[0].replace(',', ''))
        
        item["address"] = soup2.find("h2", class_="property-hero-location").text.strip()
        title = soup2.find("h2", class_="text-tertiary").text.strip()
        item["title"] = soup2.find("h2", class_="text-tertiary").text.strip()
        
        item["room_count"] = getSqureMtr(soup2.find("h2", class_="text-tertiary").text.strip())
        
        description = soup2.find("div", class_="property-description py-3").text.strip()
        item["description"] = description
        if "terrace" in description.lower():
            item["terrace"] = True
        if "swimming" in description.lower():
            item["swimming_pool"] = True
        if "furnish" in description.lower():
            item["furnished"]=True
        if "parking" in description.lower():
            item["parking"] = True
        if "balcony" in description.lower():
            item["balcony"]=True
        if "lift" in description.lower() or "elevator" in description.lower():
            item["elevator"]=True

        str_soup = str(soup2)
        lat = (re.findall(".setView(.+)",str_soup)[0])[2:-7].split(',')[0].strip()
        lng = (re.findall(".setView(.+)",str_soup)[0])[2:-7].split(',')[1].strip()
        item["latitude"] = lat
        item["longitude"] = lng
        location = getAddress(lat, lng)
        # print(location.raw['address'])
        if "postcode" in location.raw['address']:
            item["zipcode"]= location.raw["address"]["postcode"]
        if "city" in location.raw['address']:
            item["city"] = location.raw["address"]["city"]
        item["landlord_name"] = soup2.find("h3", class_="text-secondary").text.replace('Contact', '').strip()
        item["landlord_phone"] = soup2.find("p", class_="m-0").text.strip().replace('Call', '').strip()
        
        images = []
        for img in soup2.find("div", class_="gallery").findAll("div", class_="item-slick"):
            images.append(img.find("img")['src'])
        item["images"]= images
        item["external_images_count"]= len(images)

        if "flat" in title.lower() :
            property_type = "apartment"
        elif "house" in title.lower() or "maisonette" in title.lower() or "bungalow" in title.lower():
            property_type = "house"
        else:
            property_type = "NA"
        item["property_type"] = property_type
        
        try:
            item["deposit"] = getSqureMtr(re.findall("DEPOSIT REQUIRED - £(.+)",description)[0])
        except Exception as e:
            pass

        item["external_source"] = 'cjhole_PySpider_unitedkingdom_en'

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item
