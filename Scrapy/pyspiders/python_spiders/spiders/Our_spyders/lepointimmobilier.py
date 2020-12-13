import scrapy
import js2xml
import re
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
# import geopy
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter

# locator = Nominatim(user_agent="myGeocoder")

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng) # "52","76"
#     location = locator.reverse(coordinates)
#     return location

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getSqureMtr(text):
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

class QuotesSpider(scrapy.Spider):
    name = "lepointimmobilier_PySpider_france_fr"
    allowed_domains = ['www.lepointimmobilier-agence.fr']
    start_urls = ['www.lepointimmobilier-agence.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        url ='https://www.lepointimmobilier-agence.fr/liste-annonces?from=search&type=rent'

        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        my_final_link = []

        soup = BeautifulSoup(response.body)

        external_link = soup.findAll("div",{"class":"actions-bien-liste"})

        for xl in external_link:
            my_link = xl.find_all('a', {"class" : "big-link"})
            my_final_link = 'https://www.lepointimmobilier-agence.fr' + my_link[0].attrs['href']
            
            yield scrapy.Request(
                url=my_final_link, 
                callback=self.get_property_details, 
                meta={'external_link': my_final_link})
                

    def get_property_details(self, response):
        item = ListingItem()

        sub_soup = BeautifulSoup(response.body)

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        item["title"] = sub_soup.find("p", {"class" : "taille"}).text

        item["description"] =  sub_soup.find("div", {"class" : "desc-produit"}).text

        images = []
        for img in sub_soup.findAll("a",{"class" : "see-photos"}):
            images.append(img.find("img").get("src"))
        item["images"]= images
        item["external_images_count"]= len(images)

        temp_dic = {}
        all_li = sub_soup.findAll("div", {"class" : "block-caracteristique"})
        for al in all_li:
            for l in al.findAll("li"):
                temp_dic[l.text.split(':')[0]] = l.text.split(':')[1]
        temp_dic = cleanKey(temp_dic)

        if "beschikbaarheid" in temp_dic and num_there(temp_dic["beschikbaarheid"]):
            item["available_date"] = temp_dic["beschikbaarheid"]

        if "kosten" in temp_dic:
            text_list = re.findall('\d+',temp_dic["kosten"])
            if int(text_list[0]):
                item["utilities"]=int(text_list[0])

        if "gemeubeld" in temp_dic and temp_dic["gemeubeld"] == "ja":
            item["furnished"]=True
        elif "gemeubeld" in temp_dic and temp_dic["gemeubeld"] == "nee":
            item["furnished"]=False

        if "lift" in temp_dic and temp_dic["lift"] == "ja":
            item["elevator"]=True
        elif "lift" in temp_dic and temp_dic["lift"] == "nee":
            item["elevator"]=False

        if "verdieping" in temp_dic:
            item["floor"]=temp_dic["verdieping"]

        if "balcon" in temp_dic and temp_dic["balcon"] == "Oui":
            item["balcony"]=True
        elif "balcon" in temp_dic and temp_dic["balcon"] == "Non":
            item["balcony"]=False

        if "epc" in temp_dic:
            item["energy_label"]=temp_dic["epc"]

        if "badkamers" in temp_dic and getSqureMtr(temp_dic["badkamers"]):
            item["bathroom_count"]=getSqureMtr(temp_dic["badkamers"])
        if "parking" in temp_dic:
            item["parking"]=True

        item["room_count"] = int(re.findall('\d+',temp_dic["nombrepi_ces"])[0])

        item["square_meters"] = int(re.findall('\d+',temp_dic["surface"])[0])

        item["rent"] = int(re.findall('\d+',temp_dic["prix"])[0].replace('€',''))

        city = sub_soup.find("p", {"class" : "taille"}).text.split(' ')[-1]
        item["city"] = city

        str_soup = str(sub_soup)
        extract_text = re.findall("var myLatLng = {(.+)",str_soup)
        lat_lon = extract_text[0].strip()+"}"
        lat_lon = lat_lon[:-3].split(',')
        for l in lat_lon:
            if "lat" in l:
                item["latitude"]= l.split(':')[-1]
                lat = l.split(':')[-1]
            else:
                item["longitude"]= l.split(':')[-1]
                lon = l.split(':')[-1]

        # location = getAddress(lat,lon)

        # item["zipcode"]= location.raw["address"]["postcode"]
        # item["address"] = location.address

        property_type = temp_dic["typedebien"]

        if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
            property_type = "student_apartment"
        elif "appartement" in property_type.lower():
            property_type = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower():
            property_type = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
            property_type = "room"
        elif "studio" in property_type.lower():
            property_type = "studio"
        else:
            property_type = "NA"
        item["property_type"] = property_type

        item["external_id"] = temp_dic["r_f_annonce"]

        item["external_source"] = 'lepointimmobilier_PySpider_france_fr'

        item["landlord_name"] = sub_soup.find("p", {"class" : "nom-agence"}).text
        item["landlord_phone"] = sub_soup.find("span", {"class":"tel"}).text.split(':')[-1]
        item["landlord_email"] = sub_soup.find("span", {"class":"email"}).find("a").text

        item["currency"]='EUR'

        item["utilities"] = int(re.findall('\d+',temp_dic["chargeslocatives"])[0].replace('€',''))
        item["deposit"] =  int(re.findall('\d+',temp_dic["d_p_tdegarantie"])[0].replace('€',''))

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item

