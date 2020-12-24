# Author: Sounak Ghosh
import scrapy
import js2xml
import re
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date

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
    name = "barnes_cannes_PySpider_belgium_fr"
    allowed_domains = ['www.barnes-cannes.com']
    start_urls = ['www.barnes-cannes.com']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def start_requests(self):
        url ='https://www.barnes-cannes.com/fr/location-saisonniere/'

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body,"html.parser")
        imax = getSqureMtr(soup.find("h1", class_="accommodation-list__title d-none d-md-inline-block").text)
        i = 0
        while i <= imax:
            sub_url = 'https://www.barnes-cannes.com/v5_php/moteur.php?ajx=ok&start={}'.format(i)
            i = i + 28
            yield scrapy.Request(
                url=sub_url, 
                callback=self.get_external_link)

    def get_external_link(self, response):
        soup1 = BeautifulSoup(response.body,"html.parser")
        external_links = []
        for el in soup1.find("div", class_="row anim--cascad").findAll("a", class_="link-graydark-primary"):
            external_links.append(el['href'])

        for el in external_links:
            yield scrapy.Request(
                url=el, 
                callback=self.get_property_details, 
                meta={'external_link': el})

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body,"html.parser")
        print (response.url)

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["title"] = soup2.find("p",class_="h3").text

        images = []
        for img in soup2.findAll("div",class_="item d-block"):
            images.append(img.find("img")["data-src"])
        if images:
            item["images"]= images
            item["external_images_count"]= len(images)

        for li in soup2.find("ul",class_="list-inline text-muted my-4").findAll("li"):
            if "m2" in li.text and getSqureMtr(li.text):
                item["square_meters"] = getSqureMtr(li.text)
            if "pièces" in li.text and getSqureMtr(li.text):
                item["room_count"] = getSqureMtr(li.text)

        item["external_id"] = str(getSqureMtr(soup2.find("div",class_="text-muted my-4").text))

        temp_dic = {}
        for table in soup2.find("ul",class_="list-grid").findAll("li"):
            temp_dic[table.findAll("div")[0].text] = table.findAll("div")[1].text
        temp_dic = cleanKey(temp_dic)

        if "tarifs" in temp_dic and getSqureMtr(temp_dic["tarifs"].replace(' ', '')):
            item["rent"] = getSqureMtr(temp_dic["tarifs"].replace(' ', ''))
        if "lave_linge" in temp_dic:
            item["washing_machine"] = True
        if "lave_vaisselle" in temp_dic:
            item["dishwasher"] = True
        if "piscine" in temp_dic:
            item["swimming_pool"] = True


        property_type = temp_dic["typesdebien"]
        if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
            property_type = "student_apartment"
        elif "appartement" in property_type.lower():
            property_type = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "villa" in property_type.lower() or "maison" in property_type.lower() :
            property_type = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
            property_type = "room"
        elif "studio" in property_type.lower():
            property_type = "studio"
        else:
            property_type = "NA"
        item["property_type"] = property_type

        item["city"] = temp_dic["ville"].split(" ")[0]
        item["zipcode"] = temp_dic["ville"].split(" ")[1]

        if "salledebains" in temp_dic:
            item["bathroom_count"] = getSqureMtr(temp_dic["salledebains"])

        if "sallesdebains" in temp_dic:
            item["bathroom_count"] = getSqureMtr(temp_dic["sallesdebains"])


        if soup2.find("p",class_="h6 text-muted"):
            description = soup2.find("p",class_="h6 text-muted").text
            if "garage" in description.lower() or "parking" in description.lower():
                item["parking"] = True
            if "terras" in description.lower() or "terrace" in description.lower():
                item["terrace"] = True
            if "zwembad" in description.lower() or "swimming" in description.lower():
                item["swimming_pool"] = True
            if "gemeubileerd" in description.lower()or "aménagées" in description.lower() or "furnished" in description.lower():
                item["furnished"]=True
            if "garage" in description.lower() or "parking" in description.lower():
                item["parking"] = True
            item["description"] = description

        str_soup = str(soup2)
        extract_text =re.findall("var var_location = (.+)",str_soup)
        if extract_text:
            lat = (extract_text[0].split('(')[1])[:-2].split(',')[0]
            log= (extract_text[0].split('(')[1])[:-2].split(',')[1]
            item["latitude"] = str(lat)
            item["longitude"] = str(log)

            # location = getAddress(lat,log)
            # item["address"] = location.address

        landloard_name = soup2.find("div",class_="anim-fade-up delay-sm").find("p")
        item["landlord_name"] = landloard_name.text.split('+')[0]
        item["landlord_phone"] = landloard_name.text.split('+')[1]

        item["currency"]='EUR'

        item["external_source"] = 'barnes_cannes_PySpider_belgium_fr'

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item
