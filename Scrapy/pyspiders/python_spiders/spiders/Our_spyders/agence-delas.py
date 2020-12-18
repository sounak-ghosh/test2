# Author: Sounak Ghosh
import scrapy
import js2xml
import re
import json
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
# import geopy
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter
from scrapy.selector import Selector

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
    name = "Agence_Delas_PySpider_france"
    allowed_domains = ['www.agence-delas.fr', 'www.delas-montelimar.com', 'www.delas-aubenas.com']
    start_urls = ['www.agence-delas.fr']
    execution_type = 'testing'
    country = 'french'
    locale ='fr'

    
    def start_requests(self):
        start_urls = ['http://www.delas-aubenas.com/a-louer/1', 'http://www.delas-montelimar.com/a-louer/1']

        for url in start_urls:
            if "aubenas" in url:
                main_url = "http://www.delas-aubenas.com"
            if "montelimar" in url:
                main_url = "http://www.delas-montelimar.com"
            yield scrapy.Request(
                url=url, 
                callback=self.parse, meta={'main_url': main_url})

    def parse(self, response):
        soup = BeautifulSoup(response.body)
        imax = 0
        for page in soup.find("ul", class_="pagination").findAll("li"):
            if page.text and int(page.text) > imax:
                imax = int(page.text)

        main_url = response.meta.get('main_url')

        links = []
        for el in soup.find("section", class_="row listing2").findAll("a"):
            links.append(main_url+el['href'])

        for i in range(2,imax+1):
            yield scrapy.Request(
                url=main_url+"/a-louer/{}".format(i), 
                callback=self.get_external_link, meta={'main_url': main_url, 'links': links})


    def get_external_link(self, response):
        soup1 = BeautifulSoup(response.body)
        main_url = response.meta.get('main_url')
        external_links = response.meta.get('links')

        for el in soup1.find("section", class_="row listing2").findAll("a"):
            external_links.append(main_url+el['href'])
        external_links = list(set(external_links))

        for link in external_links:
            yield scrapy.Request(
                url=link, 
                callback=self.get_property_details, meta={'link': link})

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body)

        item["external_link"]  = response.meta.get('link')

        item["title"] = soup2.find("div", class_="containerDetail").find("div", class_="themTitle").find("h1").text

        images = []
        for img in soup2.find("ul", class_="imageGallery loading").findAll("li"):
            if img.find("img"):
                images.append(img.find("img")['src'])
        item["images"]= images
        item["external_images_count"]= len(images)

        item["external_id"] = soup2.find("span", class_="ref").text.replace('Ref ', '').strip()

        description = soup2.find('p', itemprop="description").text.strip()
        item["description"] = description

        temp_dic = {}
        if soup2.find("div", id="infos"):
            for span in soup2.find("div", id="infos").findAll("p", class_="data"):
                temp_dic[span.find("span", class_="termInfos").text.strip()] = span.find("span", class_="valueInfos").text.strip()
        if soup2.find("div", id="details"):
            for span in soup2.find("div", id="details").findAll("p", class_="data"):
                temp_dic[span.find("span", class_="termInfos").text.strip()] = span.find("span", class_="valueInfos").text.strip()
        if soup2.find("div", id="infosfi"):
            for span in soup2.find("div", id="infosfi").findAll("p", class_="data"):
                temp_dic[span.find("span", class_="termInfos").text.strip()] = span.find("span", class_="valueInfos").text.strip()
        temp_dic = cleanKey(temp_dic)

        item["zipcode"] = temp_dic["codepostal"]
        item["city"] = temp_dic["ville"]
        if "surfacehabitable_m" in temp_dic:
            item["square_meters"]  = getSqureMtr(temp_dic["surfacehabitable_m"])
        if "nombredechambre_s" in temp_dic:
            item["room_count"] = getSqureMtr(temp_dic["nombredechambre_s"])

        if "meubl" in temp_dic:
            if temp_dic["meubl"] == 'OUI':
                item["furnished"] = True
            if temp_dic["meubl"] == 'NON':
                item["furnished"] = False

        if "etage" in temp_dic:
            item["floor"] = temp_dic["etage"]

        if "ascenseur" in temp_dic:
            if temp_dic["ascenseur"] == 'OUI':
                item["elevator"] = True
            if temp_dic["ascenseur"] == 'NON':
                item["elevator"] = False

        if "balcon" in temp_dic:
            if temp_dic["balcon"] == 'OUI':
                item["balcony"] = True
            if temp_dic["balcon"] == 'NON':
                item["balcony"] = False

        if "terrasse" in temp_dic:
            if temp_dic["terrasse"] == 'OUI':
                item["terrace"] = True
            if temp_dic["terrasse"] == 'NON':
                item["terrace"] = False

        if "nbdesalledebains" in temp_dic:
            item["bathroom_count"] = getSqureMtr(temp_dic["nbdesalledebains"])

        item["rent"] = getSqureMtr(temp_dic["loyercc__mois"])

        item["deposit"]  = getSqureMtr(temp_dic["d_p_tdegarantiettc"])

        item["currency"]='EUR' 

        item["external_source"] = 'Agence_Delas_PySpider_france'

        lat = re.findall("center: {(.+)},",str(soup2))[0].split(',')[0].split(':')[-1].strip()
        lng = re.findall("center: {(.+)},",str(soup2))[0].split(',')[1].split(':')[-1].strip()
        item["latitude"] = lat
        item["longitude"] = lng
        # location = getAddress(lat, lng)
        # item["address"] = location.address

        if "tudiant" in description.lower() or  "studenten" in description.lower() and "appartement" in description.lower():
            property_type = "student_apartment"
        elif "appartement" in description.lower():
            property_type = "apartment"
        elif "woning" in description.lower() or "maison" in description.lower() or "huis" in description.lower():
            property_type = "house"
        elif "chambre" in description.lower() or "kamer" in description.lower():
            property_type = "room"
        elif "studio" in description.lower():
            property_type = "studio"
        else:
            property_type = "NA"

        item["property_type"] = property_type

        if "avec" in description.lower() or "swimming" in description.lower():
            item["swimming_pool"] = True

        if "aubenas" in response.meta.get('link'):
            item["landlord_phone"] = '04 75 35 06 76'
            item["landlord_email"] = 'agence@delas-aubenas.com'
        if "montelimar" in response.meta.get('link'):
            item["landlord_phone"] = '04 75 00 57 77'
            item["landlord_email"] = 'agency@delas-montelimar.com'


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item






