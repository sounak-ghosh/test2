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
# import timestring
from datetime import datetime

geolocator = Nominatim(user_agent="myGeocoder")

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    # else:
    #     date = str(timestring.Date(text)).replace("00:00:00","").strip()
    return date


# def get_lat_lon(_address):
#     location = geolocator.geocode(_address)
#     return location.latitude,location.longitude


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


class QuotesSpider(scrapy.Spider):
    name = 'pastor_realestate_PySpider_unitedkingdom_en'
    allowed_domains = ['www.pastor-realestate.com']
    start_urls = ['www.pastor-realestate.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        for c in range(1,50):
            url = "https://www.pastor-realestate.com/property-lettings/property-to-rent-in-london/page-"+str(c)
            yield scrapy.Request(
                url=url,
                callback=self.parse
                )


    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        list_url = []
        all_prop = soup.find_all("h4", class_="item-address heading-m")
        if len(all_prop) > 0:
            for ech_prop in all_prop[:11]:
                url = "https://www.pastor-realestate.com"+ech_prop.find("a")["href"]
                list_url.append(url)

        list_url = list(set(list_url))
        for external_link in list_url:
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )


    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)
        print (response.url)

        soup_str = str(soup).replace("'lat'","lat").replace("'lng'","lng")

        extract_lat = re.findall("lat:(.+),",soup_str)
        extract_lon = re.findall("lng:(.+),",soup_str)

        if extract_lat and extract_lon:
            extract_lat = re.findall("lat:(.+),",soup_str)
            extract_lon = re.findall("lng:(.+),",soup_str)

            lat = extract_lat[0]
            lon = extract_lon[0]
            item["latitude"] = str(lat)
            item["longitude"] = str(lon)
            # location=getAddress(lat,lon)

            # if "city" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["city"]
            # elif "town" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["town"]
            # elif "village" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["village"]
            # item["zipcode"] = location.raw["address"]["postcode"]

 
        title = soup.find("div", class_="col-md-12").find("h1").text.strip()
        item["title"] = title

        address = soup.find("div", class_="col-md-12").find("h2").text.strip()
        item["address"] = address

        if soup.find("div", class_="col-md-12").find("p", class_="item-price"):
            rent = getPrice(soup.find("div", class_="col-md-12").find("p", class_="item-price").text)
            # rent = (rent/7)*30
            item["rent"] = rent * 4

        details = soup.find("div", class_="tab-content details").find("div", class_="property-overview-content")

        if details.find("li", class_="bedroom"):
            room_count = getSqureMtr(details.find("li", class_="bedroom").text) 
            item["room_count"] = room_count
        if details.find("li", class_="bathroom"):
            bathroom = getSqureMtr(details.find("li", class_="bathroom").text)
            item["bathroom_count"] = bathroom

        desc = details.find("p").text.strip()
        item["description"] = desc
        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if ("gemeubileerd" in desc.lower() or "furnished" in desc.lower() or "meublé" in desc.lower()) and "unfurnished" not in desc.lower():
            item["furnished"] = True
        if "machine à laver" in desc.lower() or ("washing" in desc.lower() and "machine" in desc.lower()):
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.lower():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "ascenseur" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True


        property_type = "NA"
        features = details.find("ul", class_="attributes").find_all("li")
        for ech_feat in features:
            if "floor" in ech_feat.text.lower():
                item["floor"] = ech_feat.text.strip()

            if ("student" in ech_feat.text.lower() and "apartment" in ech_feat.text.lower()) or ("tudiant" in ech_feat.text.lower() or  "studenten" in ech_feat.text.lower() and "appartement" in ech_feat.text.lower()):
                property_type = "student_apartment"
            elif "property" in ech_feat.text.lower() or "appartement" in ech_feat.text.lower() or "demeure" in ech_feat.text.lower() or "apartment" in ech_feat.text.lower():
                property_type = "apartment"
            elif "woning" in ech_feat.text.lower() or "maison" in ech_feat.text.lower() or "huis" in ech_feat.text.lower() or "duplex" in ech_feat.text.lower() or "house" in ech_feat.text.lower():
                property_type = "house"
            elif "chambre" in ech_feat.text.lower() or "kamer" in ech_feat.text.lower() or"room" in ech_feat.text.lower():
                property_type = "room"
            elif "studio" in ech_feat.text.lower():
                property_type = "studio"
            else:
                property_type = "NA"

        image_list = []
        imgs = soup.find("div",class_="slider slider-modal-gallery js-parent-slider").find_all("div", class_="slide")
        for im in imgs:
            image_list.append(im.find("img")["src"])
        if image_list:
            item["images"]=image_list


        plan_image_list = []
        if soup.find("div", id="floorplan"):
            floor_imgs = soup.find("div", id="floorplan").find("div", class_="modal-body").find("img")["src"]
            plan_image_list.append(floor_imgs)
            if plan_image_list:
                item["floor_plan_images"] = plan_image_list

        if image_list or plan_image_list:
            item["external_images_count"] = len(image_list)+len(plan_image_list)

        if soup.find("div", class_="module-person__name"):
            item["landlord_name"] = soup.find("div", class_="module-person__name").text.strip()
        if soup.find("div", class_="module-person__phone"):
            item["landlord_phone"] = soup.find("div", class_="module-person__phone").text.strip()

        item["external_link"] =  response.url
        item["external_source"] = "pastor_realestate_PySpider_unitedkingdom_en"
        item["currency"] = "GBP"

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            item["property_type"] = property_type
            print (item)
            yield item
