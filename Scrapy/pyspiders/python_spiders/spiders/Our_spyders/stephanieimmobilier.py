import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
from datetime import datetime
import math


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

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 0:
        output = int(list_text[0])
    else:
        output=0

    return output

def getPrice(text):
    list_text = re.findall(r'\d+',text)
    if "." in text:
        if len(list_text) == 3:
            output = int(float(list_text[0]+list_text[1]))
        elif len(list_text) == 2:
            output = int(float(list_text[0]))
        elif len(list_text) == 1:
            output = int(list_text[0])
        else:
            output=0
    else:
        if len(list_text) == 2:
            output = int(float(list_text[0]+list_text[1]))
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

class auditaSpider(scrapy.Spider):
    name = 'Stephanieimmobilier_PySpider_france'
    allowed_domains = ['www.stephanieimmobilier.com']
    start_urls = ['www.stephanieimmobilier.com']
    execution_type = 'testing'
    country = 'france'
    locale ='en'

    def start_requests(self):
        start_url = 'https://www.stephanieimmobilier.com/catalog/advanced_search_result.php?action=update_search&search_id=1688311698096428&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_27_search=EGAL&C_27_type=TEXT&C_27=2%2C1&C_27_tmp=1&C_34_MIN=&C_34_search=COMPRIS&C_34_type=NUMBER&C_65_search=CONTIENT&C_65_type=TEXT&C_65=&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MAX=&C_33_search=COMPRIS&C_33_type=NUMBER&C_33_MIN=&C_33_MAX=&C_34_MAX=&C_30_MIN=&C_36_MAX=&C_36_MIN=&C_36_search=COMPRIS&C_36_type=NUMBER&&search_id=1688311698096428&page=1'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        page_count = int(soup.find("li", class_="nb-pages").text.split("/")[1].strip())
        for ech_prop in soup.find_all("div",class_="photo-product"):
            external_link = "https://www.stephanieimmobilier.com" + ech_prop.find("a")["href"].replace("..","")
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})

        for ech_pg in range(1,page_count):
            url = f'https://www.stephanieimmobilier.com/catalog/advanced_search_result.php?action=update_search&search_id=1688311698096428&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_27_search=EGAL&C_27_type=TEXT&C_27=2%2C1&C_27_tmp=1&C_34_MIN=&C_34_search=COMPRIS&C_34_type=NUMBER&C_65_search=CONTIENT&C_65_type=TEXT&C_65=&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MAX=&C_33_search=COMPRIS&C_33_type=NUMBER&C_33_MIN=&C_33_MAX=&C_34_MAX=&C_30_MIN=&C_36_MAX=&C_36_MIN=&C_36_search=COMPRIS&C_36_type=NUMBER&&search_id=1688311698096428&page={ech_pg+1}' 
            yield scrapy.Request(url = url, callback = self.parse2)

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("div",class_="photo-product"):
            external_link = "https://www.stephanieimmobilier.com" + ech_prop.find("a")["href"].replace("..","")
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        external_link = response.meta.get("external_link")
        item["external_link"] = external_link
        print(external_link)

        title = soup.find("div",class_="infos-products-header").find("div",class_="col-xs-12 col-sm-12 col-md-12 col-lg-12").find("h1").text
        item["title"] = title

        address = soup.find("div",class_="infos-products-header").find("div",class_="col-xs-12 col-sm-12 col-md-12 col-lg-12").find("div",class_="product-localisation").text
        item["address"] = address

        zipcode = address.split(" ")[0]
        item["zipcode"] = zipcode

        city = (address.replace(zipcode,"").strip())
        item["city"] = city

        if soup.find("div",class_="infos-products-header").find("div",class_="col-xs-12 col-sm-12 col-md-12 col-lg-12").find("div",class_="prix loyer"):
            rent = getPrice(soup.find("div",class_="infos-products-header").find("div",class_="col-xs-12 col-sm-12 col-md-12 col-lg-12").find("div",class_="prix loyer").text)
            item["rent"] = rent

        for ech_span in soup.find("div", class_="col-xs-12 col-sm-12 col-md-4 col-lg-4").find_all("span", itemprop="name"):
            if "Ref. :" in ech_span.text:
                external_id = ech_span.text.replace("Ref. :","").strip()
                item["external_id"] = external_id

        desc = soup.find("div",class_="desc-text").text.strip()
        item["description"] = desc

        if "machine à laver" in desc.lower():
            item["washing_machine"] = True
        if "lave" in desc.lower() and "vaisselle" in desc.lower():
            item["dishwasher"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"]=True

        image_list = []
        for ech_img in soup.find("div", class_="container-slider-product").find_all("div", class_="item-slider"):
            if "../templates/gnimmo_dumas/catalog/images/no_picture.gif" not in ech_img.find("a")["href"]:
                image_list.append("https://www.stephanieimmobilier.com"+ech_img.find("a")["href"].replace("..",""))
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        temp_dic = {}
        for ech_det_odd in soup.find("div", class_="product-criteres").find_all("li",class_="list-group-item odd"):
            if ech_det_odd.find("b") and ech_det_odd.find("div", class_="col-sm-6"):
                temp_dic[ech_det_odd.find("div", class_="col-sm-6").text.strip()] = ech_det_odd.find("b").text.strip()
        for ech_det_even in soup.find("div", class_="product-criteres").find_all("li",class_="list-group-item even"):
            if ech_det_even.find("div", class_="col-sm-6") and ech_det_even.find("b"):
                temp_dic[ech_det_even.find("div", class_="col-sm-6").text.strip()] = ech_det_even.find("b").text.strip()
        temp_dic = cleanKey(temp_dic)
        # print(temp_dic)

        if "typedebien" in temp_dic:
            if "Appartement".lower() in temp_dic["typedebien"].lower():
                property_type = "Apartment"
            if "Maison".lower() in temp_dic["typedebien"].lower():
                property_type = "House"
            item["property_type"] = property_type

        if "d_p_tdegarantie" in temp_dic:
            deposit = getSqureMtr(temp_dic["d_p_tdegarantie"])
            item["deposit"] = deposit
        if "surface" in temp_dic:
            square_meters = getSqureMtr(temp_dic["surface"])
            item["square_meters"] = square_meters
        if "nombrepi_ces" in temp_dic:
            room_count = int(temp_dic["nombrepi_ces"])
            item["room_count"] = room_count
        if "salle_s_debains" in temp_dic or "salle_s_d_eau" in temp_dic:
            if "salle_s_debains" in temp_dic:
                bathroom_count = int(temp_dic["salle_s_debains"])
                item["bathroom_count"] = bathroom_count
            else:
                bathroom_count = int(temp_dic["salle_s_d_eau"])
                item["bathroom_count"] = bathroom_count
        if "ascenseur" in temp_dic:
            if "Oui" in temp_dic["ascenseur"]:
                item["elevator"] = True
        if "piscine" in temp_dic:
            if "Oui" in temp_dic["piscine"]:
                item["swimming_pool"] = True
        if "etage" in temp_dic:
            floor = temp_dic["etage"]
            item["floor"] = floor
        if "nombregarages_box" in temp_dic:
            item["parking"] = True
        if "nombredeterrasses" in temp_dic:
            item["terrace"] = True
        if "disponibilit" in temp_dic:
            available_date = strToDate(temp_dic["disponibilit"].strip())
            item["available_date"] = available_date
        if "valeurconsoannuelle_nergie" in temp_dic:
            energy_label = temp_dic["valeurconsoannuelle_nergie"]
            item["energy_label"] = energy_label
        if "provisionsurcharges" in temp_dic:
            utilities = getSqureMtr(temp_dic["provisionsurcharges"])
            item["utilities"] = utilities
        if "meubl" in temp_dic:
            if "Oui" in temp_dic["meubl"]:
                item["furnished"] = True

        item["external_source"] = "Stephanieimmobilier_PySpider_france"
        item["currency"] = "EUR"
        item["landlord_phone"] = "04.90.93.51.99"

        # print(item)
        yield item
