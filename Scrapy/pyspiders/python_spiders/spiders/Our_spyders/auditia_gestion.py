# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
from datetime import datetime

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date

def num_there(s):
    return any(i.isdigit() for i in s)

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output

def getRent(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0]+list_text[1])
    elif len(list_text) == 1:
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
        text = ''.join([c if 97 <= ord(c) <= 122 or 48 <= ord(c) <= 57 else '_' for c in text ])
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

class auditaSpider(scrapy.Spider):
    name = 'auditia_gestion_PySpider_france_fr'
    allowed_domains = ['www.auditia-gestion.com']
    start_urls = ['www.auditia-gestion.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"http://www.auditia-gestion.com/fr/immobilier/louer/"}]
        for urls in start_urls:
            yield scrapy.Request(url=urls.get('url'),
                                 callback=self.parse)


    def parse(self, response):
        soup = BeautifulSoup(response.body)
        for urls in soup.find("div",class_="PaginationLinks").find_all("a"):
            yield scrapy.Request(url=urls["href"],
                callback=self.parse2)


    def parse2(self,response,**kwargs):
        soup = BeautifulSoup(response.body)
        ul = soup.find("ul",class_="annonceList louer")
        if ul:
            all_li = ul.find_all("li",class_=True)
            for ech_li in all_li:
                if "".join(ech_li["class"]) in ["bigTitleannonce","annonce","lastOfLineannonce"]:
                    dic = {}
                    dic["rent"] = getRent(ech_li.find("span",class_="price").text)
                    specs = ech_li.find("ul",class_="spef").find_all("li")
                    if specs:
                        if getSqureMtr(specs[0].text):
                            dic["square_meters"] = getSqureMtr(specs[0].text)
                        if getSqureMtr(specs[1].text):
                            dic["room_count"] = getSqureMtr(specs[1].text)
                    dic["external_link"] = ech_li.find("a",class_="enSavoirPlus")["href"]
                    dic["title"] = ech_li.find("h4").text.strip()
                    dic["external_id"] =  ech_li.find("span",class_="refAnnonce").text.strip()
                    dic["property_type"] = property_type = ech_li.find("h3").text.strip()

                    if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
                        property_type = "student_apartment"
                    elif "appartement" in property_type.lower():
                        property_type = "apartment"
                    elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "house" in property_type.lower():
                        property_type = "house"
                    elif "chambre" in property_type.lower() or "kamer" in property_type.lower() or "room" in property_type.lower():
                        property_type = "room"
                    elif "studio" in property_type.lower():
                        property_type = "studio"
                    else:
                        property_type = "NA"


                    if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                        dic["property_type"] = property_type

                        yield scrapy.Request(
                            url=dic["external_link"],
                            callback=self.get_property_details,
                            meta = dic
                        )




    def get_property_details(self, response,**kwargs):
        item = ListingItem()

        item["external_link"] = response.meta.get('external_link')
        item["rent"] = response.meta.get('rent')
        item["property_type"] = response.meta.get('property_type')
        item["title"] = response.meta.get('title')
        item["external_source"] = "auditia_gestion_PySpider_france_fr"
        item["currency"]='EUR'

        if "room_count" in dict(response.meta):
            item["room_count"] = response.meta.get('room_count')
        if "square_meters" in dict(response.meta):
            item["square_meters"] = response.meta.get('square_meters')

        soup = BeautifulSoup(response.body)

        if soup.find("h4",class_="ville"):
            address = soup.find("h4",class_="ville").text.strip()
            city = address.split("(")[0].strip()
            zipcode = address.split("(")[-1].strip(")")
            item["city"] = city
            item["zipcode"] = zipcode
            item["address"] = address


        if soup.find("p",class_="refAnnonce"):
            ref_text = soup.find("p",class_="refAnnonce").text.split("ref.")[-1].strip()
            item["external_id"] = ref_text

        if soup.find("p",class_="descriptif"):
            description = soup.find("p",class_="descriptif").text.strip()
            lst_text = description.lower().split("disponible")
            if len(lst_text) > 1 :
                strgDate = lst_text[-1]
                if re.findall(r'\d{2}\/\d{2}\/\d{4}',strgDate):
                    item["available_date"] = strToDate(re.findall(r'\d{2}\/\d{2}\/\d{4}',strgDate)[0])
                elif re.findall(r'\d{2}\/\d{2}\/\d{2}',strgDate):
                    item["available_date"] = strToDate(re.findall(r'\d{2}\/\d{2}\/\d{2}',strgDate)[0]+"20")
                elif num_there(strgDate):
                    item["available_date"] = "Disponible "+strgDate.strip()
                else:
                    pass
            else:
                strgDate = lst_text[-1]
                if re.findall(r'\d{2}\/\d{2}\/\d{4}',strgDate):
                    item["available_date"] = strToDate(re.findall(r'\d{2}\/\d{2}\/\d{4}',strgDate)[0])
                elif re.findall(r'\d{2}\/\d{2}\/\d{2}',strgDate):
                    item["available_date"] = strToDate(re.findall(r'\d{2}\/\d{2}\/\d{2}',strgDate)[0]+"20")

            if description.split("DEPOT DE GARANTI"):
                deposit = int(re.findall(r'\d+',description.split("DEPOT DE GARANTI")[-1])[0])
                if deposit:
                    item["deposit"] = deposit

            if len(description.split("LOYER HORS CHARGES")) > 1:
                if len(description.split("LOYER HORS CHARGES")[-1].split("CHARGES :")[-1]) > 1:
                    utilities=int(re.findall(r'\d+',description.split("LOYER HORS CHARGES")[-1].split("CHARGES :")[-1])[0])
                    if utilities:
                        item["utilities"] = utilities

            elif len(description.split("CHARGES :")) > 1:
                utilities = int(re.findall(r'\d+',description.split("CHARGES :")[-1])[0])
                if utilities:
                        item["utilities"] = utilities

            if "garage" in description.lower() or "parking" in description.lower() or "autostaanplaat" in description.lower():
                item["parking"]=True
            if "terras" in description.lower() or "terrace" in description.lower():
                item["terrace"]=True
            if "balcon" in description.lower() or "balcony" in description.lower():
                item["balcony"]=True
            if "zwembad" in description.lower() or "swimming" in description.lower():
                item["swimming_pool"]=True
            if "gemeubileerd" in description.lower() or "furnished" in description.lower():
                item["furnished"]=True
            if "machine à laver" in description.lower():
                item["washing_machine"]=True
            if "lave" in description.lower() and "vaisselle" in description.lower():
                item["dishwasher"]=True
            if "lift" in description.lower():
                item["elevator"]=True


                

        if soup.find("div",id="BandeauPhotos"):
            all_img = soup.find("div",id="BandeauPhotos").find_all("a",class_="annonceGallery ImageLink")
            img_lst = []
            for imgs in all_img:
                img_lst.append(imgs["href"])

            if img_lst:
                item["images"] = img_lst
                item["external_images_count"] = len(img_lst)

                

        
        if soup.find("div",id="GraphConsommation") and soup.find("div",id="GraphConsommation").find("span",class_="graphArrowValue"):
            energy_lable = soup.find("div",id="GraphConsommation").find("span",class_="graphArrowValue").text.strip()

            if num_there(energy_lable):
                item["energy_label"] = energy_lable+" KWHEP / M² AN"


        item["landlord_name"] = "Auditia - Gestion immobilière"
        item["landlord_phone"] = "05 62 30 66 20"

        print (item)
        yield item
