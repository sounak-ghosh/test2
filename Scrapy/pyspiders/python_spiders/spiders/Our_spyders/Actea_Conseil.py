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
    name = 'Actea_Conseil_PySpider_france'
    allowed_domains = ['actea-conseil.fr']
    start_urls = ['actea-conseil.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.actea-conseil.fr/louer/"}]
        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for row in soup.find('div', class_='rh_pagination').find_all('a'):
            url_link=row.get('href')
            yield scrapy.Request(
                url=url_link,
                callback=self.get_page_details,
                dont_filter = True
                )

    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for row in soup.find_all('div', class_='rh_overlay__contents rh_overlay__fadeIn-bottom'):
            external_link = row.find('a').get('href')
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )

    def get_property_details(self, response, **kwargs):
        print (response.url)
        item = ListingItem()
        
        soup = BeautifulSoup(response.body,"html.parser")

        address =  soup.find("nav",class_ = "property-breadcrumbs").find_all("li")[-1].text.strip()


        split_space = address.split(" ")
        zipcode = split_space[0].strip(",").strip()
        city = split_space[-1].strip(",").strip()

        imgs = []
        try:
            for row in soup.find('div', class_='flexslider').find_all('li'):
                imgs.append(row.find('img').get('src'))
        except:
            imgs.append(soup.find('div', id='property-featured-image').find('img').get('src'))


        item["address"] = address
        item["city"] = city
        item["zipcode"] = zipcode
        item["external_link"] = response.url
        item["external_id"] = soup.find('div', class_='rh_property__id').text.split(':')[1].encode('utf-8').decode('ascii', 'ignore').strip()
        item["title"] = soup.find('h1', class_='rh_page__title').text.strip()
        item["description"] = soup.find('div', class_='rh_content').find('p').text.strip()
        item["images"] = imgs
        item["external_images_count"] = len(imgs)
        item["landlord_phone"] = "+33 (0)1 53 70 60 40"
        item["landlord_name"] = "ACTEA"
        item["landlord_email"] = "contact@actea-conseil.fr"
        item["external_source"] = "Actea_Conseil_PySpider_france"
        item["property_type"] = "apartment"
        item["currency"] = "EUR"

        info_dict = {}
        for prices_info in soup.find('div', class_='rh_page__property_price').find_all('p'):
            info_dict.update({prices_info.get('class')[0]: clean_value(prices_info.text.strip())})
        for row in soup.find('div', class_='rh_property__row rh_property__meta_wrap').find_all('div', recursive=False):
            span = row.find_all('span')
            key = span[0].text.strip()
            value = ' '.join([r1.text.strip() for r1 in span[1:]])
            info_dict.update({key: value})
        for row in soup.find('ul', class_='rh_property__additional clearfix').find_all('li'):
            key = row.find('span', class_='title').text.strip()
            value = row.find('span', class_='value').text.strip()
            info_dict.update({key: value})

        info_dict = cleanKey(info_dict)

        if "sallesdebain" in info_dict:
            item["bathroom_count"] = int(info_dict["sallesdebain"])

        if "surface" in info_dict and getSqureMtr(info_dict["surface"]):
            item["square_meters"] = getSqureMtr(info_dict["surface"])

        if "price" in info_dict and getPrice(info_dict["price"]):
            item["rent"] = getPrice(info_dict["price"])

        if "etage" in info_dict:
            item["floor"] = info_dict["etage"]

        if "pieces" in info_dict and getSqureMtr(info_dict["pieces"]):
            item["room_count"] = getSqureMtr(info_dict["pieces"])

        if "garage" in info_dict:
            item["parking"] = True

        for r in soup.find_all('li', class_='rh_property__feature'):
            if "ascenseur" in r.text.strip().lower():
                item["elevator"] = True
            if "balcon" in r.text.strip().lower():
                item["balcony"] = True
            if "terrasse" in r.text.strip().lower():
                item["terrace"] = True

        print (item)
        yield item