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
    name = "adams_PySpider_france_en"
    allowed_domains = ['www.adamsestates.net']
    start_urls = ['www.adamsestates.net']
    execution_type = 'testing'
    country = 'france'
    locale ='en'

    def start_requests(self):
        url ='https://www.adamsestates.net/properties.aspx?mode=1&commercial=0&showsearch=1&menuID=30'

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body,"html.parser")

        imax = 0
        for page in soup.find("div", class_="pagination").findAll("li"):
            if page.text and int(page.text) > imax:
                imax = int(page.text)

        for i in range(0, imax):
            sub_url ='https://www.adamsestates.net/properties.aspx?mode=1&commercial=0&showsearch=1&menuID=30'
            data = {
            "__VIEWSTATE":soup.find("input", id="__VIEWSTATE")["value"],
            "__VIEWSTATEGENERATOR" : soup.find("input", id="__VIEWSTATEGENERATOR")['value'],
            "__EVENTVALIDATION" :  soup.find("input", id="__EVENTVALIDATION")['value'],
            "__EVENTTARGET" : "ctl00$ContentPlaceHolderMain$repPages$ctl0{}$lnkPage".format(i),
            "__EVENTARGUMENT" : "",
            "__LASTFOCUS" : "",
            "ctl00$ContentPlaceHolderMain$uctPropertySearch$txtSearch": "",
            "ctl00$ContentPlaceHolderMain$uctPropertySearch$cboPropertyTypeGroup": "All Residential",
            "ctl00$ContentPlaceHolderMain$uctPropertySearch$cboBedrooms": "0",
            "ctl00$ContentPlaceHolderMain$uctPropertySearch$cboMinPrice": "0",
            "ctl00$ContentPlaceHolderMain$uctPropertySearch$cboMaxPrice": "0",
            "ctl00$ContentPlaceHolderMain$uctPropertySearch$cboStatus": "Show All",
            "ctl00$ContentPlaceHolderMain$lstSort": "Sort Highest Price",
            "ctl00$ContentPlaceHolderMain$cboPageNos": soup.find("div", id="listing-header").find("select", id="ctl00_ContentPlaceHolderMain_cboPageNos").find("option").text
            }

            yield scrapy.FormRequest(
                url=sub_url, 
                callback=self.get_external_link,
                formdata = data)

    def get_external_link(self, response):
        soup1 = BeautifulSoup(response.body,"html.parser")

        el = []
        for prop in soup1.find("div", id="property-listing").findAll("a"):
            if ".htm" in prop['href']:
                yield scrapy.Request(
                    url='https://www.adamsestates.net/' + prop['href'], 
                    callback=self.get_property_details, 
                    meta={'external_link': 'https://www.adamsestates.net/' + prop['href']})

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body,"html.parser")

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["currency"]='EUR'

        item["title"] = soup2.find("h1", id="banner-title").text.strip()

        
        if 'pw' in soup2.find("div", class_="price").text:
            item["rent"] = getSqureMtr(soup2.find("div", class_="price").text.replace(',', ''))*4
        else:
            item["rent"] = getSqureMtr(soup2.find("div", class_="price").text.replace(',', ''))

        images = []
        for img in soup2.find("div", id="property-detail-thumbs").findAll("div", class_="item"):
            images.append(img.find("img")['src'])
        if images:
            item["images"]= images

        floor_plan = []
        if soup2.find("img",id="ctl00_ContentPlaceHolderMain_imgFloorPlan"):
            floor_plan = [soup2.find("img",id="ctl00_ContentPlaceHolderMain_imgFloorPlan")["src"]]
            item["floor_plan_images"] = floor_plan

        if images or floor_plan:
            item["external_images_count"]= len(images)+len(floor_plan)

        for amenity in soup2.find("div", class_="property-topinfo").find("ul", class_="amenities").findAll("li"):
            if amenity.find("i", class_="icon-area"):
                item["square_meters"] = getSqureMtr(amenity.text.split('/')[0].strip())
            if amenity.find("i", class_="icon-bedrooms"):
                item["room_count"] = int(amenity.text.strip())
            if amenity.find("i", class_="icon-bathrooms"):
                item["bathroom_count"] = int(amenity.text.strip())

        item['address'] = soup2.find('h1',id='banner-title').text.strip()

        description = soup2.find("div", id="tabDescription").text.strip()
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

        if "flat" in description.lower() or "apartment" in description.lower():
            property_type = "apartment"
        elif "house" in description.lower() or "maisonette" in description.lower() or "bungalow" in description.lower():
            property_type = "house" 
        else:
            property_type = "NA"
        item["property_type"] = property_type

        lat = soup2.find("div", id="tabStreetView").find("iframe")['src'].replace('https://maps.google.com/maps?q=&layer=c&cbll=', '').split('&')[0].split(',')[0]
        lng = soup2.find("div", id="tabStreetView").find("iframe")['src'].replace('https://maps.google.com/maps?q=&layer=c&cbll=', '').split('&')[0].split(',')[1]
        item["latitude"] = str(lat)
        item["longitude"] = str(lng)
        item["external_id"] = soup2.find("span", id="ctl00_ContentPlaceHolderMain_lblPropertyID").text
        item["external_source"] = 'adams_PySpider_france_en'

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item






