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

class laforet(scrapy.Spider):
    name = 'regiesaintlouis_PySpider_france_fr'
    allowed_domains = ['www.regiesaintlouis.com']
    start_urls = ['www.regiesaintlouis.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"http://www.regiesaintlouis.com/fr/louer"}]

        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        last_page = int(soup.find('li', attrs={'class': 'lastpage'}).find('a').get('href').split('/')[-1])

        for page_no in range(1, last_page+1):
            url_link = 'http://www.regiesaintlouis.com/fr/louer/' + str(page_no)
            yield scrapy.Request(
                url=url_link,
                callback=self.get_page_details
                )

    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        
        for row in soup.find('div', attrs={'class': 'layoutBig clearfix'}).find_all('li', attrs={'class': 'ad'}):
            external_link ='http://www.regiesaintlouis.com/' + row.find('a').get('href')
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )

       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)


        match = re.findall("= L.marker(.+);",str_soup)
        if match:
            lat_lng = eval(match[0].split(",{")[0].replace("(",""))
            latitude = str(lat_lng[0])
            longitude = str(lat_lng[1])
            item["latitude"] = latitude
            item["longitude"] = longitude


        title = soup.find('div', attrs={'class': 'title'}).find('h1').text.strip()
        item["external_link"] = response.url
        item['rent'] = getPrice(soup.find('div', attrs={'class': 'title'}).find('h2', attrs={'class': 'price'}).text.strip())
        item["title"]= title


        if "tudiant" in title.lower() or  "studenten" in title.lower() and "appartement" in title.lower():
            property_type = "student_apartment"
        elif "appartement" in title.lower():
            property_type = "apartment"
        elif "woning" in title.lower() or "maison" in title.lower() or "huis" in title.lower():
            property_type = "house"
        elif "chambre" in title.lower() or "kamer" in title.lower():
            property_type = "room"
        elif "studio" in title.lower():
            property_type = "studio"
        else:
            property_type = "NA"

        address1 = response.xpath("//p[@class='comment']/text()").extract()
        item['address'] = address1[0]

        rev_address = address1[0].split()[::-1]
        rev_address = [x for x in rev_address if x.strip()]
        for r in rev_address:
            if num_there(r):
                item['zipcode'] = r
                break
        item['city'] = rev_address[0]        


        photo_links = []
        for row in soup.find('aside', attrs={'class': 'showThumbs'}).find_all('div', attrs={'class': 'item resizePicture'}):
            photo_links.append(row.find('img').get('src'))
        if photo_links:
            item["images"] = photo_links
            item["external_images_count"] = len(photo_links)


        info_1 = soup.find('section', attrs={'class': 'main show'}).find('article')
        item['external_id']= info_1.find('p', attrs={'class': 'comment'}).find('span', attrs={'class': 'reference'}).text.replace("Ref.","").strip()
        desc=info_1.find('p', attrs={'class': 'comment'}).text.strip()
        item["description"]= desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"]=True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"]=True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"]=True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"]=True
        if "gemeubileerd" in desc.lower() or "furnished" in desc.lower():
            item["furnished"]=True
        if "machine à laver" in desc.lower():
            item["washing_machine"]=True
        if "lave" in desc.lower() and "vaisselle" in desc.lower():
            item["dishwasher"]=True
        if "lift" in desc.lower():
            item["elevator"]=True



        temp_dic = {}
        for row in info_1.find('div', attrs={'class': 'details clearfix'}).find_all('li'):
            if row.find('span'):
                temp_dic.update({str(row).split('<li>')[1].split('<span>')[0].strip(): row.find('span').text.strip()})

        temp_dic = cleanKey(temp_dic)
        if "disponiblele" in temp_dic and num_there(temp_dic["disponiblele"]):
            if "/2020" not in temp_dic["disponiblele"]:
                item["available_date"] = format_date(temp_dic["disponiblele"]+"20")
            elif "/21" in temp_dic["disponiblele"][-3:]:
                item["available_date"] = format_date(temp_dic["disponiblele"].replace("/21","/2021"))
            else:
                item["available_date"] = format_date(temp_dic["disponiblele"])

        if "etage" in temp_dic:
            item["floor"] = temp_dic["etage"]

        if "charges" in temp_dic and getPrice(temp_dic["charges"]):
            item["utilities"] = getPrice(temp_dic["charges"])

        if "surface" in temp_dic and getSqureMtr(temp_dic["surface"]):
            item["square_meters"] = getSqureMtr(temp_dic["surface"])

        if "pi_ces" in temp_dic and getSqureMtr(temp_dic["pi_ces"]):
            item["room_count"] = getSqureMtr(temp_dic["pi_ces"])

        if 'd_p_tdegarantie' in temp_dic:
            item['deposit'] = getPrice(temp_dic['d_p_tdegarantie'])
        if soup.find("img",alt="Énergie - Consommation conventionnelle"):
            text = soup.find("img",alt="Énergie - Consommation conventionnelle")["src"].split("/")[-1].strip()
            item["energy_label"] = text+" kWhEP/m².an"



        item["landlord_name"] = "RÉGIE SAINT-LOUIS"
        item["landlord_phone"] = "+33 4 72 84 52 05"
        item["landlord_email"] = "location@saintlouis.immo"
        item["currency"] = "EUR"
        item["external_source"] = "regiesaintlouis_PySpider_france_fr"
        item["external_link"] = response.url


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            item["property_type"] = property_type
            # print (item)
            yield item
