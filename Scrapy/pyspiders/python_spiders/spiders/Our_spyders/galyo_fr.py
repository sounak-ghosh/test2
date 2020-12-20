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
    name = 'galyo_fr_PySpider_france_fr'
    allowed_domains = ['www.galyo.fr']
    start_urls = ['www.galyo.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.galyo.fr/location.asp"}]

        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                )



    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        url = response.meta.get("url")

        page_links = []
        for row in soup.find('center', attrs={'class': 'pagination'}).find_all('a'):
            url_link = row.get('href')
            if 'https://' in url_link:
                yield scrapy.Request(
                    url=url_link,
                    callback=self.get_page_details
                    )

    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        
        property_ = soup.find('div', attrs={'id': 'resultatliste'}).find_all('div', attrs={'class': 'resultat resultatbis'})
        for row in property_:
            external_link=row.find('span', attrs={'class': 'resultatligne1'}).find('a').get('href')
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )

       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)

        item["external_link"] = response.url

        temp_dic={}
        for row in soup.find('h1', attrs={'class': 'location fichebien'}).find_all('span'):
            temp_dic.update({row.get('class')[0]: row.text.strip()})

        if "intitule" in temp_dic:
            item["title"] = temp_dic["intitule"]
        if "surface" in temp_dic and getSqureMtr(temp_dic["surface"]):
            item["square_meters"] = getSqureMtr(temp_dic["surface"])
        if "prix" in temp_dic and getPrice(temp_dic["prix"]):
            item["rent"] = getPrice(temp_dic["prix"])            


        photo_links = []
        if soup.find('div', attrs={'id': 'VignettesFicheBien1'}):
            for row in soup.find('div', attrs={'id': 'VignettesFicheBien1'}).find_all('div', attrs={'class': 'vignettefichebien'}):
                p_link = row.find('a').get('href')
                if 'https://' in p_link:
                    photo_links.append(p_link)
        if photo_links:
            item['images'] = photo_links
            item['external_images_count'] = len(photo_links)




        temp_dic1={}
        info_1 = soup.find('div', attrs={'id': 'FicheDescriptifDebutTexte'})
        item['external_id'] = info_1.find('p', attrs={'class': 'fichebienref'}).text.replace("Réf :","").strip()

        for row in info_1.find_all('h2', attrs={'class': 'location'})[1:]:
            temp_dic1.update({row.text: row.next_sibling.text})

        temp_dic1=cleanKey(temp_dic1)
        if "disponibilit" in temp_dic1 and num_there(temp_dic1["disponibilit"]):
            item["available_date"] = format_date(temp_dic1["disponibilit"])
        if "adresse" in temp_dic1:
            item["address"] = temp_dic1["adresse"]




        info_2 = soup.find('div', attrs={'id': 'FicheDescriptifTexte'})
        temp_dic2 = {}
        for row in info_2.find('div', attrs={'class': 'fichebienpicto'}).find_all('div', attrs={'class': 'fichebienpicto1'}):
            key = row.find('img').get('src').rsplit('/',1)[1].split('-')[1].split('.')[0].strip()
            temp_dic2.update({key: row.text.strip()})

        if "nbsdb" in temp_dic2 and getSqureMtr(temp_dic2["nbsdb"]):
            item["bathroom_count"] = getSqureMtr(temp_dic2["nbsdb"])
        if "nbpieces" in temp_dic2 and getSqureMtr(temp_dic2["nbpieces"]):
            item["room_count"] = getSqureMtr(temp_dic2["nbpieces"])
        if "immeuble" in temp_dic2:
            item["floor"] = temp_dic2["immeuble"]
        if "ascenseur" in temp_dic2:
            item["elevator"] =True
        if "piscine" in temp_dic2:
            item["swimming_pool"] =True
        if "balcon" in temp_dic2:
            item["balcony"] =True
        if "stationnement" in temp_dic2:
            item["parking"]=True


        temp_dic4 = {}
        for row in info_2.find_all('li', attrs={'class': 'fichebienlignedetail0'}):
            span_data = row.find_all('span')
            if len(span_data) == 2:
                temp_dic4.update({span_data[0].text.split(':')[0].strip(): span_data[1].text.strip()})

        temp_dic4 = cleanKey(temp_dic4)
        if "d_p_tdegarantie" in temp_dic4 and getPrice(temp_dic4["d_p_tdegarantie"]):
            item["deposit"] = getPrice(temp_dic4["d_p_tdegarantie"])
        if "dontprovisionmensuelledeschargeslocatives" in temp_dic4 and getPrice(temp_dic4["dontprovisionmensuelledeschargeslocatives"]):
            item["utilities"] = getPrice(temp_dic4["dontprovisionmensuelledeschargeslocatives"])


        if soup.find("input",id = "MaxLatitude") and soup.find("input",id = "MaxLongitude"):
            latitude = soup.find("input",id = "MaxLatitude")["value"].replace(",",".")
            longitude = soup.find("input",id = "MaxLongitude")["value"].replace(",",".")

            # location = getAddress(latitude,longitude)
            # if "city" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["city"]
            # if "postcode" in location.raw["address"]:
            #     item["zipcode"] = location.raw["address"]["postcode"]

            item["latitude"] = latitude
            item["longitude"] = longitude


        item["landlord_phone"] = "04 72 77 15 77"
        item["landlord_name"] = "GALYO"
        item["external_source"] = "galyo_fr_PySpider_france_fr"
        item["currency"] = "EUR"
        item["property_type"] = "apartment"
        print (item)
        yield item

