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

class QuotesSpider(scrapy.Spider):
    name = 'agenceibox_PySpider_france_fr'
    allowed_domains = ['www.agenceibox.com']
    start_urls = ['www.agenceibox.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"http://www.agenceibox.com/a-louer/"}]

        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                meta = {"url":urls.get("url")}
                )



    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        url = response.meta.get("url")

        all_page = eval(soup.find("ul",class_="pagination").find_all("li")[-1].text)

        for page in range(1,all_page+1):
            yield scrapy.Request(
                url=url+str(page),
                callback=self.get_page_details,
                meta = {"url":url+str(page)}
                )

    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        if soup.find("article", class_="row no-gutters"):
            for ech_art in soup.find_all("article", class_="row no-gutters"):
                title = ech_art.find("h1",itemprop="name").text.strip()
                external_id = ech_art.find("div",class_="ref").find("span").text.strip()
                price = getPrice(ech_art.find("div",class_="prix").text.strip())

                if ech_art.find("span",itemprop="numberOfRooms"):
                    room_count = getSqureMtr(ech_art.find("span",itemprop="numberOfRooms").text.strip())
                if ech_art.find("span",itemprop="floorSize"):
                    sqr_mtr = getSqureMtr(ech_art.find("span",itemprop="floorSize").text.strip())

                prop_typ = ech_art.find("p",itemprop="description").text.strip()

                if "tudiant" in prop_typ.lower() or  "studenten" in prop_typ.lower() and "appartement" in prop_typ.lower():
                    property_type = "student_apartment"
                elif "appartement" in prop_typ.lower():
                    property_type = "apartment"
                elif "woning" in prop_typ.lower() or "maison" in prop_typ.lower() or "huis" in prop_typ.lower() or "duplex" in prop_typ.lower():
                    property_type = "house"
                elif "chambre" in prop_typ.lower() or "kamer" in prop_typ.lower():
                    property_type = "room"
                elif "studio" in prop_typ.lower():
                    property_type = "studio"
                else:
                    property_type = "NA"
                
                external_link = "http://www.agenceibox.com"+ech_art.find("a")["href"]
            
                if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                    yield scrapy.Request(
                        url = external_link,
                        callback =self.get_property_details,
                        meta = {"title":title,"external_link":external_link,"external_id":external_id,"property_type":property_type,
                        "square_meters":sqr_mtr,"room_count":room_count,"rent":price}
                        )

       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        str_soup = str(soup)

        title = response.meta.get("title")
        rent = response.meta.get("rent")
        external_link = response.meta.get("external_link")
        external_id = response.meta.get("external_id")
        property_type = response.meta.get("property_type")
        room_count = response.meta.get("room_count")
        square_meters = response.meta.get("square_meters")
        description = soup.find("p",itemprop="description").text.strip()


        extract_text = re.findall("center:(.+)},",str_soup)
        lat_lon = extract_text[0].strip()+"}"
        lat_lon = eval(lat_lon.replace("lat",'"latitude"').replace("lng",'"longitude"'))

        if soup.find("ul",class_="imageGallery notLoaded"):
            all_img = soup.find("ul",class_="imageGallery notLoaded").find_all("li")
            temp_lst = []
            for pics in all_img:
                temp_lst.append(pics["data-src"])

            if temp_lst:
                item["images"]=temp_lst
                item["external_images_count"]=len(temp_lst)




        if soup.find("div",id="myTabContent"):
            temp_dic = {}
            all_tr=soup.find("div",id="myTabContent").find_all("tr")

            for ech_tr in all_tr:
                if ech_tr.find("th",class_="labelInfo") and ech_tr.find("th",class_="valueInfo text-right"):
                    key = ech_tr.find("th",class_="labelInfo").text.strip()
                    vals=ech_tr.find("th",class_="valueInfo text-right").text.strip()
                    temp_dic.update({key:vals})


            temp_dic = cleanKey(temp_dic)

            print(temp_dic)
            print("\n")

            if "ville" in temp_dic:
                item["city"] = temp_dic["ville"]

            if "nombredegarage" in temp_dic:
                item["parking"] = True

            if "etage" in temp_dic:
                item["floor"] = temp_dic["etage"]

            if "chargeslocatives_provisiondonnantlieu_r_gularisationannuelle" in temp_dic:
                item["utilities"] = getSqureMtr(temp_dic["chargeslocatives_provisiondonnantlieu_r_gularisationannuelle"])

            if "codepostal" in temp_dic:
                item["zipcode"] = temp_dic["codepostal"]

            if "nbdesalled_eau" in temp_dic:
                item["bathroom_count"] = getSqureMtr(temp_dic["nbdesalled_eau"])

            if "d_p_tdegarantiettc" in temp_dic:
                item["deposit"] = getPrice(temp_dic["d_p_tdegarantiettc"])

            if "nombredeparking" in temp_dic:
                item["parking"]=True

            if "ascenseur" in temp_dic and temp_dic["ascenseur"] == "NON":
                item["elevator"] = False
            elif "ascenseur" in temp_dic and temp_dic["ascenseur"] == "OUI":
                item["elevator"] = True


            if "balcon" in temp_dic and temp_dic["balcon"] == "NON":
                item["balcony"] = False
            elif "balcon" in temp_dic and temp_dic["balcon"] == "OUI":
                item["balcony"] = True


            if "terrasse" in temp_dic and temp_dic["terrasse"] == "NON":
                item["terrace"] = False
            elif "terrasse" in temp_dic and temp_dic["terrasse"] == "OUI":
                item["terrace"] = True


            if "meubl" in temp_dic and temp_dic["meubl"] == "NON":
                item["furnished"] = False
            elif "meubl" in temp_dic and temp_dic["meubl"] == "OUI":
                item["furnished"] = True




        item["title"] = title
        item["rent"] = rent
        item["room_count"] = room_count
        item["property_type"] = property_type
        item["square_meters"] = square_meters
        item["description"] = description
        item["external_id"] = external_id
        item["latitude"] = str(lat_lon["latitude"])
        item["longitude"] = str(lat_lon["longitude"])
        item["title"] = title
        item["external_link"] = external_link
        item["external_id"] = external_id
        item["property_type"] = property_type
        item["landlord_name"] = "IBOX Mourillon"
        item["landlord_phone"] = "0498009210"
        item["currency"] = "EUR"
        item["external_source"] = "agenceibox_PySpider_france_fr"

        # print (item)
        yield item
