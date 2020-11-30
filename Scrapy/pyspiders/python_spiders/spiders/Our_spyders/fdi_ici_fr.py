import scrapy
import js2xml
import re
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

locator = Nominatim(user_agent="myGeocoder")

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng) # "52","76"
    location = locator.reverse(coordinates)
    return location

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
    name = "fdi_ici_fr_PySpider_france_fr"
    allowed_domains = ['www.fdi-ici.fr']
    start_urls = ['www.fdi-ici.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        url ='https://www.fdi-ici.fr/rechercher?univers=louer&surface_min=&surface_max=&budget_min=&budget_max='

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body)

        for xl in soup.findAll("div", class_= "lot"):
            yield scrapy.Request(
                url='https://www.fdi-ici.fr' + xl.find("a")["href"], 
                callback=self.get_property_details, 
                meta={'external_link': 'https://www.fdi-ici.fr' + xl.find("a")["href"],
                      'title' : xl.find("div", class_= "info").find("h4").text})

    def get_property_details(self, response):
        item = ListingItem()
        sub_soup = BeautifulSoup(response.body)

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["title"] = response.meta.get('title')

        description1 = ''
        description2 = ''
        description1 = sub_soup.find("div", class_="col-md-6 annonce").find("p").text 
        try:
            description2 = sub_soup.find("div", class_="col-md-6 annonce").find("div", id="ville").text 
        except Exception as e:
            description2 = ''
        description = description1 + ' ' + description2
        item["description"] = description
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True
        if "terras" in description.lower():
            item["terrace"] = True
        if "zwembad" in description.lower() or "swimming" in description.lower():
            item["swimming_pool"] = True
        if "gemeubileerd" in description.lower()or "aménagées" in description.lower() or "furnished" in description.lower():
            item["furnished"]=True
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True

        images = []
        for img in sub_soup.find("div", class_="images").findAll("a"):
            images.append('https://www.fdi-ici.fr' + img['href'])
        item["images"]= images
        item["external_images_count"]= len(images)

        temp_dic = {}
        for tr in sub_soup.find("table", class_="table").find("tbody").findAll("tr"):
            temp_dic[tr.findAll("td")[0].text]= tr.findAll("td")[1].text 
        temp_dic = cleanKey(temp_dic)

        item["external_id"] = temp_dic["r_f_rence"]
        if "surface" in temp_dic:
            item["square_meters"] = getSqureMtr(temp_dic["surface"])
        for note in str(sub_soup.find("p", class_="note")).replace('<p class="note">', '').split('<br/>'):
            if ":" in note:
                temp_dic[note.split(':')[0]] = note.split(':')[1]
        temp_dic = cleanKey(temp_dic)

        if "lift" in temp_dic and temp_dic["lift"] == "ja":
            item["elevator"]=True
        elif "lift" in temp_dic and temp_dic["lift"] == "nee":
            item["elevator"]=False

        if "verdieping" in temp_dic:
            item["floor"]=temp_dic["verdieping"]

        if "balkon" in temp_dic and temp_dic["balkon"] == "ja":
            item["balcony"]=True
        elif "balkon" in temp_dic and temp_dic["balkon"] == "nee":
            item["balcony"]=False

        item["deposit"] = int(temp_dic["d_p_tdegarantie"].split(',')[0].replace(' ',  ''))

        item["utilities"] = int(temp_dic["honoraireschargelocataire"].split(',')[0].replace(' ',  ''))

        item["currency"]='EUR'

        item["external_source"] = 'fdi_ici_fr_PySpider_france_fr'

        item["landlord_name"] = sub_soup.find("div", class_="agence").text

        if sub_soup.find("span", class_="code"):
            item["energy_label"] = sub_soup.find("span", class_="code").text + ' kWhEP/m2'
                 
        property_type = sub_soup.find("div", class_="info").find("h3").text
        if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
            property_type = "student_apartment"
        elif "appartement" in property_type.lower():
            property_type = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "villa" in property_type.lower():
            property_type = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
            property_type = "room"
        elif "studio" in property_type.lower():
            property_type = "studio"
        else:
            property_type = "NA"
        item["property_type"] = property_type

        item["rent"] = int(sub_soup.find("div", class_="info").find("h4").text.split(',')[0].replace(' ',  ''))
        
        try:
            item["room_count"] = int(re.findall('\d+',sub_soup.find("div", class_="info").find("ul").find("li").text)[0])
        except Exception as e:
            pass

        
        if "salledebain" in temp_dic:
            item["bathroom_count"] = int(temp_dic["salledebain"])
        if "terrasse" in temp_dic:
            item["terrace"] = True

        if sub_soup.find("div", id="map"):
            item["latitude"] = sub_soup.find("div", id="map")['data-latitude']
            item["longitude"] = sub_soup.find("div", id="map")['data-longitude']
            location = getAddress(item["latitude"],item["longitude"])
            item["city"]= location.raw["address"]["municipality"]
            # print(location.raw)
            item["zipcode"]= location.raw["address"]["postcode"]
            item["address"] = location.address
        else:
            item["city"] = str(sub_soup.find("small", class_="text-uppercase").text).split(' ')[0]
            item["zipcode"] = re.findall('\d+',sub_soup.find("small", class_="text-uppercase").text)[0]

        if "cuisine_quip_e" in temp_dic:
            item["furnished"]=True

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item

