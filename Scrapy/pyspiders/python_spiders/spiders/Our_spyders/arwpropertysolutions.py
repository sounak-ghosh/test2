# Author: Sounak Ghosh
import scrapy
import js2xml
import re
import math
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
    name = "arwpropertysolutions_PySpider_england_uk"
    allowed_domains = ['www.arwpropertysolutions.co.uk']
    start_urls = ['www.arwpropertysolutions.co.uk']
    execution_type = 'testing'
    country = 'england'
    locale ='uk'

    def start_requests(self):
        url ='https://www.arwpropertysolutions.co.uk/?id=14845&do=search&for=2&type%5B%5D=&cats=3&minprice=0&maxprice=99999999999&kwa%5B%5D=&minbeds=0'

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body,"html.parser")

        imax = 0
        for page in soup.find("div", class_="results-pagination-wrap").findAll("a"):
            if page.text and int(page.text) > imax:
                imax = int(page.text)

        for i in range(0, imax):
            sub_url = 'https://www.arwpropertysolutions.co.uk/?id=14845&do=search&for=2&type[]=&cats=3&minprice=0&maxprice=99999999999&kwa[]=&minbeds=0&id=14845&order=2&page={}&do=search'.format(i)
            yield scrapy.Request(
                url=sub_url,
                callback=self.get_external_link)

    def get_external_link(self, response):

        soup1 = BeautifulSoup(response.body,"html.parser")
        for el in soup1.findAll("div", class_="results-list-img"):
            yield scrapy.Request(
                url='https://www.arwpropertysolutions.co.uk' + el.find("a")['href'], 
                callback=self.get_property_details, 
                meta={'external_link': 'https://www.arwpropertysolutions.co.uk' + el.find("a")['href']}
                )

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body,"html.parser")

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        images = []
        for img in soup2.findAll("img"):
            if 'http' in img['src']:
                images.append(img['src'])
        item["images"]= images
        item["external_images_count"]= len(images)

        temp_dic = {}
        for table in soup2.find("div",class_="details-icons row").findAll("div"):
            temp_dic[table.text.strip().split(" ")[-1]] = table.text.strip().split(" ")[0]
        temp_dic = cleanKey(temp_dic)

        if "flat" in temp_dic or "apartment" in temp_dic:
            property_type = "apartment"
        elif "house" in temp_dic or "maisonette" in temp_dic or "bungalow" in temp_dic:
            property_type = "house" 
        else:
            property_type = "house"
        item["property_type"] = property_type

        if "bedroom_s" in temp_dic and int(temp_dic["bedroom_s"]):
            item["room_count"] = int(temp_dic["bedroom_s"])
        if "bathroom_s" in temp_dic and int(temp_dic["bathroom_s"]):
            item["bathroom_count"] = int(temp_dic ["bathroom_s"])

        if "parking" in temp_dic and temp_dic["parking"] == "Yes":
            item["parking"] = True
        if "parking" in temp_dic and temp_dic["parking"] == "No":
            item["parking"] = False

        if "sqm" in temp_dic and getSqureMtr(temp_dic["sqm"]):
            item["square_meters"] = getSqureMtr(temp_dic["sqm"])

        item["rent"] = getSqureMtr(soup2.find("h1",class_="detail-price").text)*4

        description = soup2.find("div",class_="details-description").text
        item["description"] = description
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

        extract_text = soup2.find(id="canvas2",class_="map")
        lat = extract_text.find("iframe")["src"].split('&spn=')[-1].split('&')[0].split(',')[0]
        lng = extract_text.find("iframe")["src"].split('&spn=')[-1].split('&')[0].split(',')[1]
        if lat and lng:
            item["latitude"] = lat
            item["longitude"] = lng
            # location = getAddress(lat,lng)
            # item["zipcode"]= location.raw["address"]["postcode"]
            # item["address"] = location.address
            # if "city" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["city"]

        if "address" not in item and soup2.find("h5",class_="details-address1"):
            address = soup2.find("h5",class_="details-address1").text.strip()


        item["currency"]='EUR'
        item["external_source"] = 'arwpropertysolutions_PySpider_england_uk'

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item
