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
    name = 'Century21_Jaures_Boulogne_PySpider_france'
    allowed_domains = ['century21-jaures-boulogne.com']
    start_urls = ['century21-jaures-boulogne.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.century21-jaures-boulogne.com/annonces/location/"}]
        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        url = 'https://www.century21-jaures-boulogne.com/annonces/location/page-'
        tot_page = int(soup.find("div",class_="btnNB_PAGE xl:tw-w-full").find_all("li")[-4].text.strip())
        for page in range(1,tot_page+1):
            yield scrapy.Request(
                url=url+str(page),
                callback=self.get_property_link,
                dont_filter = True
                )

    def get_property_link(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for row in soup.find('div', id='blocANNONCES').find('ul').find_all('li'):
            property_url = row.find('a').get('href')
            if 'https://' in property_url:
                continue
            external_link = 'https://www.century21-jaures-boulogne.com' + property_url

            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )

    def get_property_details(self, response, **kwargs):
        print (response.url)
        item = ListingItem()
        
        soup = BeautifulSoup(response.body,"html.parser")
        text_soup = soup.text.lower()

        photo_links = []
        for row in soup.find('div', id='formatL') .find_all('div', class_='gal-item'):
            if row.find('img').get('src'):
                photo_links.append("https://www.century21-jaures-boulogne.com/" + row.find('img').get('src'))

        splt_spce = soup.find('div', id='filAriane').find_all('li')[-1].text.strip().split(" ")
        address = splt_spce[-2]+splt_spce[-1]
        zipcode = splt_spce[-1].strip("(").strip(")")
        city = splt_spce[-2].strip()

        item["address"] = address
        item["zipcode"] = zipcode
        item["city"] = city
        item["external_link"] = response.url
        item["zipcode"] = zipcode
        item["city"] = city
        item["external_id"] = soup.find('span', class_='tw-text-c21-gold font20 margL20 tw-font-semibold').text.split(':')[1].encode('utf-8').decode('ascii', 'ignore').strip()
        item["title"] = soup.find('h1', class_='h1_page tt').text.strip()
        item["description"] = soup.find('div', class_='desc-fr').find('p').text.strip()
        item["images"] = photo_links
        item["external_images_count"] = len(photo_links)
        item["landlord_name"] = "CENTURY 21"
        item["external_source"] = "Century21_Jaures_Boulogne_PySpider_france"
        item["rent"] = getPrice(soup.find('span', class_='tw-text-c21-gold').text.encode('utf-8').decode('ascii', 'ignore').strip())
        item["currency"] = "EUR"
        info_dict = {}
        for row in soup.find('div', class_='zone-contenu-slide').find_all('div', class_='box'):
            for r in row.find_all('li'):
                text = r.text.strip()
                if ':' in text:
                    text = text.split(':')
                    info_dict.update({text[0].split('\n')[-1].strip(): clean_value(text[1].strip())})

        info_dict = cleanKey(info_dict)

        if "surfacetotale" in info_dict and getSqureMtr(info_dict["surfacetotale"]):
            item["square_meters"] = getSqureMtr(info_dict["surfacetotale"])

        if "d_p_tdegarantie" in info_dict and getPrice(info_dict["d_p_tdegarantie"]):
            item["deposit"] = getPrice(info_dict["d_p_tdegarantie"])

        if "dontprovisionpourcharges" in info_dict and getPrice(info_dict["dontprovisionpourcharges"]):
            item["utilities"] = getPrice(info_dict["dontprovisionpourcharges"])

        if "nombredepi_ces" in info_dict and getSqureMtr(info_dict["nombredepi_ces"]):
            item["room_count"] = getSqureMtr(info_dict["nombredepi_ces"])

        if "ascenseur" in text_soup:
            item["elevator"] = True

        if "garage" in text_soup or "parking" in text_soup:
            item["parking"] = True


        if "parking" in item["title"].lower():
            pass
        else:
            item["property_type"] = "apartment"
            print (item)
            yield item