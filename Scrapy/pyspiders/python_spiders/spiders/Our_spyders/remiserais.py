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


class QuotesSpider1(scrapy.Spider):
    name = "remiserais"
    allowed_domains = ['www.remiserais-immobilier.fr']
    start_urls = ['www.remiserais-immobilier.fr']
    execution_type = 'testing'
    country = 'french'
    locale ='fr'

    def start_requests(self):
        url ='http://www.remiserais-immobilier.fr/annonces/transaction/Location.html'

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body)
        max_page = 0
        for page in soup.find("ul", class_="pagination").findAll("li"):
            if re.findall('\d+',page.text):
                if int(re.findall('\d+',page.text)[0]) > max_page:
                    max_page = int(re.findall('\d+',page.text)[0])

        for i in range(1,max_page+1):
            sub_url = 'http://www.remiserais-immobilier.fr/annonces/transaction/Location.html?manufacturers_id=transaction&&page={}'.format(i)
            yield scrapy.Request(
                url=sub_url, 
                callback=self.get_external_link)

    def get_external_link(self, response):
        soup1 = BeautifulSoup(response.body)

        for el in soup1.find("div", id="listing_bien").findAll("div", class_="col-xs-12 col-sm-12 no-padding"):
            yield scrapy.Request(
                url=el.find("div").find("a")['href'].replace('..', 'http://www.remiserais-immobilier.fr'), 
                callback=self.get_property_details, 
                meta={'external_link': el.find("div").find("a")['href'].replace('..', 'http://www.remiserais-immobilier.fr')})

    def get_property_details(self, response):
        item = ListingItem()
        soup2 = BeautifulSoup(response.body)

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["title"] = soup2.find("div", id="content_intro_header").text
        description = soup2.find("div", class_="col-sm-12 content_details_description").text
        item["description"] = description
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True
        if "terras" in description.lower():
            item["terrace"] = True
        if "zwembad" in description.lower() or "swimming" in description.lower():
            item["swimming_pool"] = True
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True

        images = []
        for img in soup2.find("ul", class_="slides").findAll("li"):
            images.append(img.find("a")['href'].replace('..', 'http://www.remiserais-immobilier.fr'))
        item["images"]= images
        item["external_images_count"]= len(images)

        temp_dic = {}
        for li in soup2.find("div", id="content_details").findAll("li"):
            temp_dic[li.text.split(':')[0]] = li.text.split(':')[1]

        if soup2.find("div", class_="General"):
            for li in soup2.find("div", class_="General").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        if soup2.find("div", class_="localisation"):
            for li in soup2.find("div", class_="localisation").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        if soup2.find("div", class_="aspects_financiers"):
            for li in soup2.find("div", class_="aspects_financiers").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        if soup2.find("div", class_="interieur"):
            for li in soup2.find("div", class_="interieur").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        if soup2.find("div", class_="surfaces"):
            for li in soup2.find("div", class_="surfaces").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        if soup2.find("div", class_="autres"):
            for li in soup2.find("div", class_="autres").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        if soup2.find("div", class_="diagnostics"):
            for li in soup2.find("div", class_="diagnostics").findAll("li"):
                for l in li.findAll("div", class_="row"):
                    temp_dic[l.findAll("div")[0].text] = l.findAll("div")[1].text.strip()

        temp_dic = cleanKey(temp_dic)
        # print(temp_dic)

        item["external_id"] = temp_dic["r_f_rence"]

        property_type = temp_dic["typedebien"]
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

        if "pi_ces" in temp_dic:
            item["room_count"] = int(temp_dic["pi_ces"])

        if "ville" in temp_dic:
            item["city"] = temp_dic["ville"].strip()

        if "surfacehabitable" in temp_dic:
            item["square_meters"] = getSqureMtr(temp_dic["surfacehabitable"])

        if "loyermensuelhc" in temp_dic:
            item["rent"]  = getSqureMtr(temp_dic["loyermensuelhc"])

        if "d_p_tdegarantie" in temp_dic:
            item["deposit"]  = getSqureMtr(temp_dic["d_p_tdegarantie"])

        if "honoraireslocataire" in temp_dic:
            item["utilities"] = getSqureMtr(temp_dic["honoraireslocataire"])

        if "valeurconsoannuelle_nergie" in temp_dic:
            item["energy_label"] = temp_dic["valeurconsoannuelle_nergie"]

        if "etage" in temp_dic:
            item["floor"] = temp_dic["etage"].strip()

        item["currency"]='EUR'

        if "codepostal" in temp_dic:
            item["zipcode"] = temp_dic["codepostal"]

        item["external_source"] = 'remiserais-immobilier.fr'

        if "meubl" in temp_dic:
            if temp_dic["meubl"] == "Oui":
                item["furnished"] = True
            if temp_dic["meubl"] == "Non":
                item["furnished"] = False

        if "ascenseur" in temp_dic:
            if temp_dic["ascenseur"] == "Oui":
                item["elevator"] = True
            if temp_dic["ascenseur"] == "Non":
                item["elevator"] = False

        if "piscine" in temp_dic:
            if temp_dic["piscine"] == "Oui":
                item["swimming_pool"] = True
            if temp_dic["piscine"] == "Non":
                item["swimming_pool"] = False


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item



