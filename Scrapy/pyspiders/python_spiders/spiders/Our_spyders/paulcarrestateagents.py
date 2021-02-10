import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
from datetime import datetime
import math
import json


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

    # if len(list_text) == 2:
    #     output = int(list_text[0])
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
    name = 'Paulcarrestateagents_Co_PySpider_united_kingdom'
    allowed_domains = ['www.paulcarrlettings.co.uk']
    start_urls = ['www.paulcarrlettings.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_url = "http://www.paulcarrlettings.co.uk/propertylist.php?txtbudgetlow=0&txtbudgethigh=99999999&txtnobed=9"
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        total_prop = int(soup.find("h4").text.split("Total -")[-1].strip())
        page_count = math.ceil(total_prop/24)
        if page_count > 1:
            for ech_pg in range(1,page_count):
                url = f"http://www.paulcarrlettings.co.uk/propertylist.php?pageid={ech_pg+1}&txtbudgethigh=99999999&txtbudgetlow=0&txtnobed=9&pageorder=Price%20High-%3ELow"
                yield scrapy.Request(url = url, callback = self.parse2)

        for ech_prop in soup.find_all("div", class_="custom-searchresbox custom-blue-border"):
            if ech_prop.find("div", style="background-color:#FF0000;font-weight:bold;padding:5px;width:296px;color:#FFFFFF;margin-bottom:0px;position:absolute;margin-top:-30px;"):
                pass
            else:
                title = ech_prop.find("div", class_='custom-blueboxtitle custom-blueboxtitle-blue').find("div").text.strip()
                external_link = "http://www.paulcarrlettings.co.uk/" + ech_prop.find("div", class_='custom-center-cropped').find("a")["href"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"title" : title})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        for ech_prop in soup.find_all("div", class_="custom-searchresbox custom-blue-border"):
            if ech_prop.find("div", style="background-color:#FF0000;font-weight:bold;padding:5px;width:296px;color:#FFFFFF;margin-bottom:0px;position:absolute;margin-top:-30px;"):
                pass
            else:
                title = ech_prop.find("div", class_='custom-blueboxtitle custom-blueboxtitle-blue').find("div").text.strip()
                external_link = "http://www.paulcarrlettings.co.uk/" + ech_prop.find("div", class_='custom-center-cropped').find("a")["href"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"title" : title})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body) 
        print(response.url)

        item["external_link"] = response.url

        item["title"] = response.meta.get("title")

        external_id = soup.find("div", class_="custom-bluetopcurved custom-bluetopcurved-blue custom-price col-xs-12").find("div").find("span", recursive = False).text.strip()
        item["external_id"] = external_id

        item["rent"] = getPrice(soup.find("div", class_="custom-bluetopcurved custom-bluetopcurved-blue custom-price col-xs-12").find("div").text.replace(external_id,""))
        
        rc_pt_add = soup.find("div", class_="custom-blueboxtitlenoncurved custom-blueboxtitlenoncurved-blue col-xs-12" ).text

        if "flat" in rc_pt_add.lower():
            property_type = "apartment"
        elif "house" in rc_pt_add.lower():
            property_type = "house"
        item["property_type"] = property_type

        temp_rc = getSqureMtr(rc_pt_add.split("(")[0])
        if temp_rc > 0:
            item["room_count"] = temp_rc

        item["address"] = rc_pt_add.split("(")[-1].replace(")","").strip()

        desc = soup.find("div", class_="col-sm-5").find("p").text.strip()
        item["description"] = desc

        if "GARAGE EXCLUDED".lower() in desc.lower():
            pass
        elif "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terrace house" in desc.lower() or ("end" in desc.lower() and "terrace" in desc.lower()) or "terraced house" in desc.lower():
            pass
        elif "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "part furnished" in desc.lower() and "unfurnished" in desc.lower():
            item["furnished"] = True
        elif "unfurnished" in desc.lower():
            item["furnished"] = False
        elif "furnished" in desc.lower() or "furnishing" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.lower():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        images = []
        for ech_img in soup.find("ul", id="photolist_thumbs").find_all("li"):
            images.append(ech_img.find("img")["src"])
        if images:
            item["images"] = images
            item["external_images_count"] = len(images)

        item["landlord_name"] = "Paul Carr Estate Agents"
        item["landlord_phone"] = "0121 726 9417"
        item["landlord_email"] = "info@paulcarrlettings.co.uk"
        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"

        print(item)
        yield item
