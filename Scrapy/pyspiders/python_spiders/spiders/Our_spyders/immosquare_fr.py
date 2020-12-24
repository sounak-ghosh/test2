# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests

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
    name = 'immosquare_fr_PySpider_france_fr'
    allowed_domains = ['www.immosquare.fr']
    start_urls = ['www.immosquare.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.immosquare.fr/immobilier-annonce.html"}]

        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                meta = {"url":urls.get("url")}
                )



    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        
        if soup.find("ul",id="itemContainer"):
            lis_property= soup.find("ul",id="itemContainer").find_all("li",class_="annonce mod mr1 mb1 left")

        for ech_li in lis_property:
            
            text_url = ech_li.find("a")["href"]
            external_link = "https://www.immosquare.fr/"+text_url
            price = getPrice(ech_li.find("span").text)
            city = ech_li.find("h5").find("a").text

            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details,
                meta = {"city":city,"rent":price}
                )

       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)

        print (response.url)

        match = re.findall("address:(.+),",str_soup)
        if match:
            address = (match)[0].strip('"').strip()
            item["address"] = address



        title = soup.find("h1",class_="rouge").text.strip()
        item["title"] = title
        if "tudiant" in title.lower() or  "studenten" in title.lower() and "appartement" in title.lower():
            property_type = "student_apartment"
        elif "appartement" in title.lower():
            property_type = "apartment"
        elif "woning" in title.lower() or "maison" in title.lower() or "huis" in title.lower() or "duplex" in title.lower():
            property_type = "house"
        elif "chambre" in title.lower() or "kamer" in title.lower():
            property_type = "room"
        elif "studio" in title.lower():
            property_type = "studio"
        else:
            property_type = "NA"



        description = soup.find("div",class_="mod w50 right pl2").text.strip()
        item["description"] = description

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



        img_lst=[]
        if soup.find("div",class_="royalSlider rsDefault"):
            img = soup.find("div",class_="royalSlider rsDefault").find_all("a",class_="rsImg")
            for items in img:
                img_lst.append(items["href"])

            item["images"] = img_lst
            item["external_images_count"] = len(img_lst)


        temp_dic = {}
        gen_dts = soup.find("div",class_="line grid4").find_all("li")
        for items in gen_dts:
            text = items.text.split(":")
            temp_dic[text[0].strip()] = text[1].strip()

        temp_dic = cleanKey(temp_dic)
        if "pi_ces" in temp_dic:
            item["room_count"] = getSqureMtr(temp_dic["pi_ces"])
        if "surfacehabitable" in temp_dic and getSqureMtr(temp_dic["surfacehabitable"]):
            item["square_meters"] = getSqureMtr(temp_dic["surfacehabitable"])
        if "salled_eau" in temp_dic and getSqureMtr(temp_dic["salled_eau"]):
            item["bathroom_count"] = getSqureMtr(temp_dic["salled_eau"])
        if "salledebains" in temp_dic and getSqureMtr(temp_dic["salledebains"]):
            item["bathroom_count"] = getSqureMtr(temp_dic["salledebains"])
        if "parkingext_rieur" in temp_dic:
            item["parking"] = True
        if "terrasse" in temp_dic:
            item["terrace"] = True


        if soup.find("div",class_="mod w50 left consommation mt2 mb2"):
            energy = soup.find("div",class_="mod w50 left consommation mt2 mb2").find("p").text
            eng = energy.replace("Consommationénergétique","")
            eng_value = eng.split("/")[0].replace("kWh","")
            if int(eng_value.strip()) != 0:
                item["energy_label"] = eng


        if soup.find("div",class_="w50 mod left"):
            landlrd_name =(soup.find("div",class_="w50 mod left").text.strip().split("\n"))[1].strip()
            item["landlrd_name"] = landlrd_name

        if soup.find("span",class_="vert mobile"):
            phone_num = soup.find("span",class_="vert mobile").text.strip()
            item["landlord_phone"] = phone_num



        item["currency"] = "EUR"
        item["external_source"] = "immosquare_fr_PySpider_france_fr"
        item["external_link"] = response.url
        item["city"] = response.meta["city"]
        item["rent"] = response.meta["rent"]


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            item["property_type"] = property_type
            # print (item)
            yield item
