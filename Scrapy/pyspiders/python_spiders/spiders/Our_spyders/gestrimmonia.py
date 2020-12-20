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

class laforet(scrapy.Spider):
    name = 'gestrimmonia_PySpider_france_fr'
    allowed_domains = ['www.gestrimmonia.com']
    start_urls = ['www.gestrimmonia.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.gestrimmonia.com/"}]
        for urls in start_urls:
            yield scrapy.Request(url=urls.get('url'),
                                 callback=self.parse)




    def parse(self, response, **kwargs):
        extract_text = re.findall("var markers =(.+);",response.body.decode("utf-8"))
        json_data = json.loads(extract_text[0].strip())

        for echProperty in json_data:
            if echProperty["typop"] == 2:
                links = "https://www.gestrimmonia.com/annonce-"+echProperty["code"]
                print (links)
                yield scrapy.Request(
                    url=links,
                    callback=self.get_property_details,
                    meta = {"external_link":links,"latitude":echProperty["lat"],"longitude":echProperty["lng"],
                    "title":echProperty["titre"],"city":echProperty["ville"]}
                )

       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()

        soup = BeautifulSoup(response.body)

        price = getSqureMtr(soup.find("span",class_="top-price location").text.strip())
        external_link = response.meta.get("external_link")
        latitude = response.meta.get("latitude")
        longitude = response.meta.get("longitude")
        title = response.meta.get("title")
        city = response.meta.get("city")


        if soup.find("div",class_="ref"):
            item["external_id"]= soup.find("div",class_="ref").text.replace("Ref.","").strip()



        if soup.find("div",class_="desc location"):
            description = soup.find("div",class_="desc location").find("div",class_="text location").text.strip()
            item["description"] = description

            p_tag = soup.find("div",class_="desc location").find("p").text.strip()
            lstDat = p_tag.split(":")
            for ind,ech_txt in enumerate(lstDat):
                if "pot de garant" in ech_txt.lower():
                    deposit = getSqureMtr(lstDat[ind+1])
                    item["deposit"] = deposit
                if "provisions charges" in ech_txt.lower():
                    utilities = getSqureMtr(lstDat[ind+1])
                    item["utilities"] = utilities
        


        if soup.find("div",class_="kpi"):
            all_itm = soup.find("div",class_="kpi").find_all("span",class_="item")

            for items in all_itm:
                txt_dat = items.text.strip()
                if "parking" in txt_dat.lower():
                    item["parking"] = True

                if "pièce" in txt_dat.lower():
                    splt_txt = txt_dat.lower().split("pièce")
                    if len(splt_txt) > 1:
                        room_cnt = getSqureMtr(splt_txt[0])
                        square_meters = getSqureMtr(splt_txt[1])

                        item["room_count"] = room_cnt
                        item["square_meters"] = square_meters
                    else:
                        room_cnt = getSqureMtr(splt_txt[0])
                        item["room_count"] = room_cnt

                if "etage" in txt_dat.lower():
                    item["floor"] = str(getSqureMtr(txt_dat.strip()))



        if soup.find("div",class_="list-pics"):
            images = []
            all_pic = soup.find("div",class_="list-pics").find_all("a")
            for img in all_pic:
                images.append(img["href"])
            if images:
                item["images"] = images
                item["external_images_count"] = len(images)


        if soup.find("div",class_="dpe"):
            if soup.find("img",class_="imgDpe"):
                if (soup.find("div",class_="etiquette").find("span").text.strip()) != "0":
                    item["energy_label"] = soup.find("div",class_="etiquette").text.strip()


        # location = getAddress(latitude,longitude)
        # address = location.address
        # zipcode = location.raw["address"]["postcode"]

        if ("tudiant" in title.lower() or  "studenten" in title.lower()) and ("appartement" in title.lower() or "apartment" in title.lower()):
            property_type = "student_apartment"
        elif "appartement" in title.lower() or "apartment" in title.lower():
            property_type = "apartment"
        elif "woning" in title.lower() or "maison" in title.lower() or "huis" in title.lower() or "house" in title.lower():
            property_type = "house"
        elif "chambre" in title.lower() or "kamer" in title.lower():
            property_type = "room"
        elif "studio" in title.lower():
            property_type = "studio"
        else:
            property_type = "NA"


        item["external_link"] = external_link
        item["rent"] = price
        item["latitude"] = latitude
        item["longitude"] = longitude
        item["title"] = title
        item["city"] = city
        # item["address"] = address
        # item["zipcode"] = zipcode
        item["external_source"] = "gestrimmonia_PySpider_france_fr"
        item["property_type"] = property_type
        item["currency"] = "EUR"


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print (item)
            yield item
