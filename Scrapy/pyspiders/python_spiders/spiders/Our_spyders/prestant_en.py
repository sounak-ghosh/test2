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
    name = 'prestant_en_PySpider_france_en'
    allowed_domains = ['www.prestant.com']
    start_urls = ['www.prestant.com']
    execution_type = 'testing'
    country = 'france'
    locale ='en'

    def start_requests(self):
        url="https://www.prestant.com/en/module/moteur/ajax.php?switch1=on&loc=location&surfacemin=0&capacite=2&idmodule=280663&1604545293182"

        yield scrapy.Request(
            url=url,
            callback=self.parse
            )


    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")


        property_lst = soup.find("ul",class_="grid-3").find_all("li",class_="item-annonce")


        list_prop = []
        for items in property_lst:
            url_text = items.find("a",href=True)["href"]
            name = items.find("b").text
            
            yield scrapy.Request(
                url=url_text,
                callback=self.get_property_details,
                meta = {"city":name}
                )
       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup).replace("'address'","address")
        print (response.url)

        match = re.findall("address:(.+)",str_soup)

        if match:
            address = eval(match[0])
            item["address"] = address
            

        if soup.find("span",class_="fl annonce-info-value c-price") and num_there(soup.find("span",class_="fl annonce-info-value c-price").text):
            item["rent"] = getPrice(soup.find("span",class_="fl annonce-info-value c-price").text)

        if soup.find("div",class_="fl w30 picto_sdb") and num_there(soup.find("div",class_="fl w30 picto_sdb").text):
            item["bathroom_count"] = getSqureMtr(soup.find("div",class_="fl w30 picto_sdb").text)


        property_type = "NA"
        if soup.find("div",class_="annonce-title"):
            ttl = soup.find("div",class_="annonce-title").find("span").text
            ttl = "  ".join(ttl.split()).split(" ")
            prop_typ = ttl[0]

            if ("student" in prop_typ.lower() and "apartment" in prop_typ.lower()) or ("tudiant" in prop_typ.lower() or  "studenten" in prop_typ.lower() and "appartement" in prop_typ.lower()):
                property_type = "student_apartment"
            elif "property" in prop_typ.lower() or "appartement" in prop_typ.lower() or "demeure" in prop_typ.lower() or "apartment" in prop_typ.lower():
                property_type = "apartment"
            elif "woning" in prop_typ.lower() or "maison" in prop_typ.lower() or "huis" in prop_typ.lower() or "duplex" in prop_typ.lower() or "house" in prop_typ.lower():
                property_type = "house"
            elif "chambre" in prop_typ.lower() or "kamer" in prop_typ.lower() or"room" in prop_typ.lower():
                property_type = "room"
            elif "studio" in prop_typ.lower():
                property_type = "studio"
            else:
                property_type = "NA"


        ref_id= soup.find("span",class_="numeromandat").text.strip()
        item["external_id"] = ref_id.replace("Référence :","").strip()

        if soup.find("div",class_="annonce-title").find("span"):
            det = soup.find("div",class_="annonce-title").find("span").find_next_sibling("span").text.strip().replace(ref_id,"")
            spl_txt = " ".join(det.split()).split("-")
            item["square_meters"] = getSqureMtr(spl_txt[0])
            item["room_count"] = getSqureMtr(spl_txt[1])



        image = soup.find("div",class_="tapis mbs mts pas").find_all("img")
        img_list = []
        for items in image:
            link = items["src"]
            img_list.append(link)    
        if img_list:
            item["images"] = img_list
            item["external_images_count"] = len(img_list)




        if soup.find("div",class_="thetitle"):
            title = soup.find("div",class_="thetitle").find("h4").text.strip()
            item["title"] = title

        desc = soup.find("div",class_="annonce-description").text
        split_txt = desc.split("\n\n\n")
        description = split_txt[-1].strip()
        item["description"] = description

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "gemeubileerd" in desc.lower() or "furnished" in desc.lower() or "meublé" in desc.lower() or "furniture" in desc.lower():
            item["furnished"] = True
        if "machine à laver" in desc.lower() or ("washing" in desc.lower() and "machine" in desc.lower()):
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.lower():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "ascenseur" in desc.lower() or "elevator" in desc.lower():  
            item["elevator"] = True


        name = soup.find("div",class_="info-contact")
        landlord = name.find("span").text
        landlord = landlord.split("-")
        item["landlord_name"] = landlord[0].strip()
        item["landlord_phone"] = landlord[1].strip()
        item["external_source"] = "prestant_en_PySpider_france_en"
        item["currency"] = "GBP"
        item["external_link"] = response.url


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            item["property_type"] = property_type
            # print (item)
            yield item
