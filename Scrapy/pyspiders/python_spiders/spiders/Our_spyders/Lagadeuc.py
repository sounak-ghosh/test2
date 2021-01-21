# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

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

class spiderQoutes(scrapy.Spider):
    name = 'Lagadeuc_PySpider_france'
    allowed_domains = ['lagadeuc.fr']
    start_urls = ['lagadeuc.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='en'

    def start_requests(self):
        start_urls = [{"url":'https://www.lagadeuc.fr/immobilier/locations/'}]
        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse
                )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for row in eval(str(soup).split("result=")[1].split(";")[0]):
            url_1 = "https://www.lagadeuc.fr/lagad-content/themes/kompromis/getAnnonceList.php?id="
            url = url_1 + row['id'] + "&index=0&show=0"
            yield scrapy.Request(
                url=url,
                callback=self.get_property_details
                )

    def get_property_details(self, response, **kwargs):
        print (response.url)
        item = ListingItem()
        
        soup = BeautifulSoup(response.body,"html.parser")

        soup.info = soup.find('div', id='fiche-print')
        photo_links = []
        if soup.info.find('div', class_='miniatures'):
            for row in soup.info.find('div', class_='miniatures').find_all('img'):
                photo_links.append(row.get('src'))
        
        desc = soup.info.find('div', id='description').text.strip()

        item["external_link"] = response.url
        item["rent"] = getPrice(soup.find('div', class_='h1').text.strip())
        item["room_count"] = getSqureMtr(soup.find('div', class_='h2').text.strip())
        item["description"] = desc
        item["images"] = photo_links
        item["external_images_count"] = len(photo_links)
        item["landlord_phone"] = "02 35 15 72 72"
        item["landlord_name"] = "THE CABINETS LAGADEUC & BOURDON LAGADEUC"
        item["landlord_email"] = "location@lagadeuc.fr"
        item["external_source"] = "Lagadeuc_PySpider_france"
        item["property_type"] = "apartment"
        item["currency"] = "EUR"

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if ("terras" in desc.lower() or "terrace" in desc.lower()) and "end of terrace" not in desc.lower() and "terrace house" not in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "furnished" in desc.lower() or "furniture" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True


        for row in soup.info.find('div', class_='infosPrinc').find_all('div'):
            name = row.text.strip()
            if "Ref :" in name:
                item['external_id']= name.split(':')[1].strip()
                continue
            if "m²" in name:
                item["square_meters"] = getSqureMtr(name)
                continue
        print(item)
        yield item