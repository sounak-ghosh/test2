import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
import requests
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

    if len(list_text) == 3:
        output = int(float(list_text[0]+list_text[1]))
    elif len(list_text) == 2:
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
    name = 'Gifparis_PySpider_france'
    allowed_domains = ['www.gifparis.com']
    start_urls = ['www.gifparis.com']
    execution_type = 'testing'
    country = 'france'
    locale ='en'

    def start_requests(self):
        start_url = 'http://www.gifparis.com/catalog/advanced_search_result.php?action=update_search&search_id=1688129167185628&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_27_search=EGAL&C_27_type=TEXT&C_27=1&C_27_tmp=1&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MAX=&C_65_search=CONTIENT&C_65_type=TEXT&C_65=&C_30_MIN=&C_64_search=INFERIEUR&C_64_type=TEXT&C_64=&C_34_search=COMPRIS&C_34_type=NUMBER&C_34_MIN=&C_34_MAX=&C_33_search=COMPRIS&C_33_type=NUMBER&C_33_MAX=&C_38_search=EGAL&C_38_type=TEXT&C_38=&&search_id=1688129167185628&page=1'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        total_prop = getSqureMtr(soup.find("div",class_="col-barre-navigation col-xs-12").find("div",class_="nb-annonces col-xs-6 col-md-6").text.strip())
        page_count = math.ceil(total_prop/12)
        for ech_prop in soup.find_all("h2", class_="titre_annonce"):
            external_link = "http://www.gifparis.com"+ech_prop.find("a")["href"].replace("..","")
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})

        for ech_pg in range(1,page_count):
            url = f'http://www.gifparis.com/catalog/advanced_search_result.php?action=update_search&search_id=1688129167185628&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_27_search=EGAL&C_27_type=TEXT&C_27=1&C_27_tmp=1&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MAX=&C_65_search=CONTIENT&C_65_type=TEXT&C_65=&C_30_MIN=&C_64_search=INFERIEUR&C_64_type=TEXT&C_64=&C_34_search=COMPRIS&C_34_type=NUMBER&C_34_MIN=&C_34_MAX=&C_33_search=COMPRIS&C_33_type=NUMBER&C_33_MAX=&C_38_search=EGAL&C_38_type=TEXT&C_38=&&search_id=1688129167185628&page={ech_pg+1}'
            yield scrapy.Request(url = url, callback = self.parse2)

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("h2", class_="titre_annonce"):
            external_link = "http://www.gifparis.com"+ech_prop.find("a")["href"].replace("..","")
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link})

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        external_link = response.meta.get("external_link")
        print (external_link)
        item["external_link"] = external_link

        external_id = soup.find("div", class_="col-breadcrumb col-xs-12 col-sm-12 col-md-12 col-lg-12").find("ol").find_all("li")[-1].text.strip().replace("Ref. :","").strip()
        item["external_id"] = external_id

        title = soup.find("div",id="content_details").find("h1").text
        item["title"] = title

        desc = soup.find("div",class_="col-xs-12 col-sm-12 col-md-12 col-lg-12 content_details_description no-padding").find("p").text.strip()
        item["description"] = desc

        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "machine à laver" in desc.lower():
            item["washing_machine"] = True
        if "lave" in desc.lower() and "vaisselle" in desc.lower():
            item["dishwasher"] = True

        address = soup.find("span", class_="ville-produit").text.lower()
        item["address"] = address

        city = soup.find("span", class_="ville-produit").text.split("(")[0].lower()
        item["city"] = city

        zipcode = soup.find("span", class_="ville-produit").text.split("(")[1].replace(")","")
        item["zipcode"] = zipcode

        image_list = []
        for ech_im in soup.find("div", class_="flexslider").find("ul").find_all("li"):
            if ech_im.find("a")["href"]:
                image_list.append("http://www.gifparis.com"+ech_im.find("a")["href"].replace("..",""))
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        temp_rent = re.findall(r'\d+',soup.find("div",class_="prix loyer").find("span", class_="alur_loyer_price").text)
        rent = ""
        if len(temp_rent)>1:
            for ech_digit in temp_rent:
                rent = rent + ech_digit
        else:
            rent = temp_rent[0]
        item["rent"] = int(rent)

        temp_dic = {}
        for ech_det in soup.find("div", id="product_criteres").find_all("div", class_="infos-bien"):
            temp_dic[ech_det.find("div", class_="text col-xs-6 col-sm-6 col-md-6 col-lg-6 no-padding").text.replace(":","").strip()] = ech_det.find("div", class_="value col-xs-6 col-sm-6 col-md-6 col-lg-6 no-padding").text
        temp_dic = cleanKey(temp_dic)

        if "typedebien" in temp_dic:
            if "Appartement".lower() in temp_dic["typedebien"].lower():
                property_type = "apartment"
            item["property_type"] = property_type
        if "etage" in temp_dic:
            floor = temp_dic["etage"]
            item["floor"] = floor

        if "honoraireslocataire" in temp_dic:
            utilities  = getSqureMtr(temp_dic["honoraireslocataire"])
            item["utilities"] = utilities

        if "d_p_tdegarantie" in temp_dic:
            deposit = getSqureMtr(temp_dic["d_p_tdegarantie"])
            item["deposit"] = deposit

        if "nombrepi_ces" in temp_dic:
            room_count = int(temp_dic["nombrepi_ces"])
            item["room_count"] = room_count

        if "salle_s_debains" in temp_dic:
            bathroom_count = int(temp_dic["salle_s_debains"])
            item["bathroom_count"] = bathroom_count

        if "meubl" in temp_dic:
            if "Oui".lower() in temp_dic["meubl"].lower():
                item["furnished"] = True
            if "Non".lower() in temp_dic["meubl"].lower():
                item["furnished"] = False
        if "surface" in temp_dic:
            square_meters = getSqureMtr(temp_dic["surface"].strip())
            item["square_meters"] = square_meters
        if "ascenseur" in temp_dic:
            if "Oui".lower() in temp_dic["ascenseur"].lower():
                item["elevator"] = True
        if "nombrebalcons" in temp_dic:
            item["balcony"] = True
        if "nombreplacesparking" in temp_dic or "nombregarages_box" in temp_dic:
            item["parking"] = True
        if "valeurconsoannuelle_nergie" in temp_dic:
            energy = temp_dic["valeurconsoannuelle_nergie"]
            item["energy_label"] = energy
            # print(energy)
        if "disponibilit" in temp_dic:
            available_date = strToDate(temp_dic["disponibilit"].strip())
            item["available_date"] = available_date
            # print(available_date)

        item["currency"] = "EUR"
        item["external_source"] = "Gifparis_PySpider_france"
        item["landlord_phone"] = "+33 7 81 78 66 45"
        item["landlord_email"] = "servicegestion@gifparis.com"
        item["landlord_name"] = "Groupe Immobilier Finances"
        
        print(item)
        yield item