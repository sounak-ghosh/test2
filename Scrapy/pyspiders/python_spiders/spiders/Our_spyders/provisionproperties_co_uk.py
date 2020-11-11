import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests
import geopy
from geopy.geocoders import Nominatim
import timestring
from datetime import datetime

geolocator = Nominatim(user_agent="myGeocoder")

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = str(timestring.Date(text)).replace("00:00:00","").strip()
    return date


def get_lat_lon(_address):
    location = geolocator.geocode(_address)
    return location.latitude,location.longitude


def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

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


class QuotesSpider(scrapy.Spider):
    name = 'provisionproperties_co_uk_PySpider_unitedkingdom_en'
    allowed_domains = ['www.provisionproperties.co.uk']
    start_urls = ['www.provisionproperties.co.uk']
    execution_type = 'testing'
    country = 'unitedkingdom'
    locale ='en'

    def start_requests(self):
        url="http://www.provisionproperties.co.uk/properties.php"

        yield scrapy.Request(
            url=url,
            callback=self.parse
            )


    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        all_property = soup.find("div", id="property-results").find_all("div", class_="property-card")
        for ech_prop in all_property:
            external_link = "http://www.provisionproperties.co.uk/"+ech_prop.find("li", class_="property-card-image").find("a")["href"]     
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )


    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)
        print (response.url)

        type_def = soup.find("div", id="breadcrumbs").find_all("li")[1].text.strip()
        if "house" in type_def.lower():
            item["property_type"] = "house"
        if "flat" in type_def.lower():
            item["property_type"] = "apartment"

        address = soup.find("h2", class_="the_font pnk").text.strip()
        item["address"] = address

        try:
            lat,lon = get_lat_lon(address)
            item["latitude"] = str(lat)
            item["longitude"] = str(lon)
            location = getAddress(lat,lon)
            if "city" in location.raw["address"]:
                item["city"] = location.raw["address"]["city"]
            if "town" in location.raw["address"]:
                item["city"] = location.raw["address"]["town"]
            elif "village" in location.raw["address"]:
                item["city"] = location.raw["address"]["village"]
            postcode = location.raw["address"]["postcode"]
            item["zipcode"] = postcode

        except Exception as e:
            print (str(e))
            pass

        title = soup.find("h1", class_="the_font blk cntr").text.strip()
        item["title"] = title

        temp_date = soup.find("div", id="property-spec").find("h3").find("span", class_="note-text").text
        date = temp_date.replace("Available:","").strip()
        if num_there(date):
            item["available_date"] = strToDate(date)

        rent = getSqureMtr(soup.find("div", id="property-spec").find("h3").text.replace(temp_date,""))
        item["rent"] = int(rent)

        rooms = soup.find("div", id="property-spec").find("ul", class_="property-card-spec spacer").find("li", class_="spec beds").text.strip()
        item["room_count"] = int(rooms)

        bathroom = soup.find("div", id="property-spec").find("ul", class_="property-card-spec spacer").find("li", class_="spec baths").text.strip()
        item["bathroom_count"] = int(bathroom)

        desc = soup.find("div", id="property-description").find("p").text.strip()
        item["description"] = desc
        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "gemeubileerd" in desc.lower() or "furniture" in desc.lower():
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if "lave" in desc.lower() and "vaisselle" in desc.lower() or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        all_features = soup.find("div", id="property-features").find("ul").find_all("li")
        for ech_feature in all_features:
            if "garage" in ech_feature.text.lower() or "parking" in ech_feature.text.lower() or "autostaanplaat" in ech_feature.text.lower():
                item["parking"] = True
            if "terras" in ech_feature.text.lower() or "terrace" in ech_feature.text.lower():
                item["terrace"] = True
            if "balcon" in ech_feature.text.lower() or "balcony" in ech_feature.text.lower():
                item["balcony"] = True
            if "zwembad" in ech_feature.text.lower() or "swimming" in ech_feature.text.lower():
                item["swimming_pool"] = True
            if "gemeubileerd" in ech_feature.text.lower() or ("furnished" in ech_feature.text.lower() and "yes" in ech_feature.text.lower()):
                item["furnished"] = True
            if "machine à laver" in ech_feature.text.lower() or"washing" in ech_feature.text.lower():
                item["washing_machine"] = True
            if "lave" in ech_feature.text.lower() and "vaisselle" in ech_feature.text.lower() or "dishwasher" in ech_feature.text.strip():
                item["dishwasher"] = True
            if "lift" in ech_feature.text.lower() or "elevator" in ech_feature.text.lower():
                item["elevator"] = True

        image_list = []
        imgs = soup.find("div", id="property-gallery-main").find_all("div", class_="property-gallery-image")
        for im in imgs:
            image_list.append("http://www.provisionproperties.co.uk"+im.find("img")["src"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)


        item["landlord_email"] = "info@provisionproperties.co.uk"
        item["landlord_name"] = "Provision Properties"
        item["landlord_phone"] = "0113 305 3344"
        item["external_source"] = "provisionproperties_co_uk_PySpider_unitedkingdom_en"
        item["external_link"] = response.url
        item["currency"] = "GBP"

        print (item)
        yield item
