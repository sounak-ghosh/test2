import scrapy
import js2xml
import re
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


def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if "." in text:
        if len(list_text) > 0:
            output = int(list_text[0])
        else:
            output=0
        return output
    elif "," in text:
        if len(list_text) > 1:
            output = int(list_text[0]+list_text[1])
        else:
            output=0
        return output
    else:
        if len(list_text) > 0:
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

class QuotesSpider(scrapy.Spider):
    name = "acornproperties_PySpider_uk_en"
    allowed_domains = ['www.acornproperties.co.uk']
    start_urls = ['www.acornproperties.co.uk']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'

    def __init__(self):
        self.student_flag = False
        self.apartment_flag = False



    def start_requests(self):

        start_url =[{"property_type":"apartment","url":"https://www.acornproperties.co.uk/properties/?text-search=&radiusProf=&prof-min-price=&prof-max-price=&beds=&search-box-radio=prof&order=high&pag={}&view=grid"},
        {"property_type":"student_apartment","url":"https://www.acornproperties.co.uk/properties/?text-search=&radius=&stud-min-price=&stud-max-price=&beds=&search-box-radio=stud&order=high&pag={}&view=grid"}]

        for urls in start_url:
            page = 1 
            property_type = urls.get("property_type")
            while True:
                if self.student_flag and property_type == "student_apartment":
                    break
                if self.apartment_flag and property_type == "apartment":
                    break

                url = urls.get("url").format(page)
                page+=1

                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta = {"property_type":property_type})
                

    def parse(self, response):

        soup = BeautifulSoup(response.body,"html.parser")
        property_type = response.meta["property_type"]

        if soup.find("div",class_="col centered") == None:
            if property_type == "student_apartment":
                self.student_flag = True
            if property_type == "apartment":
                self.apartment_flag = True
        
        else:
            all_prop = soup.find_all("div",class_="col centered")            
            for ech_prop in all_prop:
                external_link = ech_prop.find("a")["href"]

                yield scrapy.Request(
                    url=external_link,
                    callback=self.get_property_details,
                    meta = {"property_type":property_type})



    def get_property_details(self, response):
        dic = {}
        soup = BeautifulSoup(response.body,"html.parser")

        property_type = response.meta["property_type"]
        print (response.url)

        if "let" and "agreed" not in soup.find("h4", class_="property-availability").text.lower():
            dic["external_link"] = response.url

            if num_there(soup.find("h4", class_="property-availability").text):
                date = format_date(soup.find("h4", class_="property-availability").text.replace("Available from","").strip())
                dic["available_date"] = date

            soup_str = str(soup)
            extract_lat = re.findall("var mapLat = (.+);",soup_str)
            extract_lng = re.findall("var mapLng = (.+);",soup_str)

            if extract_lat and extract_lng:
                lat = extract_lat[0]
                lon = extract_lng[0]

                location = getAddress(lat,lon)
                address = location.address

                dic["address"] = address
                dic["latitude"]=lat
                dic["longitude"]=lon

                if "city" in location.raw["address"]:
                    dic["city"] = location.raw["address"]["city"]
                elif "town" in location.raw["address"]:
                    dic["city"] = location.raw["address"]["town"]

                postcode = location.raw["address"]["postcode"]
                dic["zipcode"] = postcode

            ref_no = getSqureMtr(soup.find("section",class_="row property-content clearfix").find("div", class_="info clearfix").find("p").text)
            dic["external_id"] = str(ref_no)


            if "student_apartment" == property_type:
                dic["property_type"] = "student_apartment"
            if "apartment" == property_type:
                dic["property_type"] = "apartment"

            all_features = soup.find("div",class_="features clearfix").find_all("li")
            for ech_feat in all_features:
                if "student_apartment" == property_type:
                    dic["property_type"] = "student_apartment"
                    if "bathroom" in ech_feat.text.lower() and getSqureMtr(ech_feat.text):
                        dic["bathroom_count"]=getSqureMtr(ech_feat.text)
                    if "bedroom" in ech_feat.text.lower() and getSqureMtr(ech_feat.text):
                        dic["room_count"] = getSqureMtr(ech_feat.text)
                    if "furnished" in ech_feat.text.lower():
                        dic["furnished"] = True
                else:
                    if "bathroom" in ech_feat.text.lower() and getSqureMtr(ech_feat.text):
                        dic["bathroom_count"]=getSqureMtr(ech_feat.text)
                    if "bedroom" in ech_feat.text.lower() and getSqureMtr(ech_feat.text):
                        dic["room_count"] = getSqureMtr(ech_feat.text)
                    if "furnished" in ech_feat.text.lower():
                        dic["furnished"] = True
                    if "maison" in ech_feat.text.lower() or "house" in ech_feat.text.lower() or "duplex" in ech_feat.text.lower():
                        dic["property_type"] = "house"
                    if "apartment" in ech_feat.text.lower() or "building" in ech_feat.text.lower():
                        dic["property_type"] = "apartment"



            
            title = (soup.find("p",class_="property-sale").text)
            dic["title"] = title

            rent = getPrice(title)
            dic["rent"]=rent

            desc = soup.find("section",class_="row property-content clearfix").find("div",class_="inner-small").find_all("p")[-1].text.strip()
            dic["description"] = desc

            if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                dic["parking"] = True
            if "terras" in desc.lower() or "terrace" in desc.lower():
                dic["terrace"] = True
            if "balcon" in desc.lower() or "balcony" in desc.lower():
                dic["balcony"] = True
            if "zwembad" in desc.lower() or "swimming" in desc.lower():
                dic["swimming_pool"] = True
            if "gemeubileerd" in desc.lower() or "furniture" in desc.lower() or "furnished" in desc.lower():
                dic["furnished"] = True
            if "machine à laver" in desc.lower() or"washing" in desc.lower():
                dic["washing_machine"] = True
            if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
                dic["dishwasher"] = True
            if "lift" in desc.lower() or "elevator" in desc.lower():
                dic["elevator"] = True

            if soup.find("section",class_="epc row centered"):
                energy = soup.find("section",class_="epc row centered").find("img")["src"]
                energy = energy.split("&")
                for en in energy:
                    if "EPC¤tenergy" in en:
                        energy_current = en.split("=")[-1]
                        dic["energy_label"] = energy_current +" KWHEP / M² AN"

            dic["landlord_name"] = "Acorn Properties(Jesmond)"
            dic["landlord_phone"] = "0191 212 2020"
            dic["external_source"] = "acornproperties_PySpider_uk_en"
            dic["currency"] = "GBP"

            prop_id = soup.find("body")["class"][-1].split("-")[-1].strip()
            url_img = "https://www.acornproperties.co.uk/wp-admin/admin-ajax.php"
            data = {
                "action": "load_photos",
                "propertyID": prop_id
            }

            yield scrapy.FormRequest(
                url=url_img,
                formdata = data,
                callback=self.get_property_image,
                meta = dic)




    def get_property_image(self, response):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")

        for k,v in response.meta.items():
            try:
                item[k] = v
            except:
                pass

        image_list = []
        imgs = soup.find_all("div",class_="prop-image bg-img")
        for im in imgs:
            image_list.append(im["style"].replace("background-image: url(","").replace(")","").strip())
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)


        yield item