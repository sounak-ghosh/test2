import scrapy
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
    coordinates = str(lat)+","+str(lng) 
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
    name = "citya"
    allowed_domains = ['www.citya.com']
    start_urls = ['www.citya.com']
    execution_type = 'testing'
    country = 'dutch'
    locale ='nl'

    def start_requests(self):
        url = 'https://www.citya.com/annonces/agence/177/location?page=1'
        yield scrapy.Request(
            url=url,
            callback=self.parse)

    def parse(self,response):
        soup = BeautifulSoup(response.body)

        if soup.find("div",class_="pagination").find_all("li")[-1].find("a"):
            page_count = int(soup.find("div",class_="pagination").find_all("li")[-1].find("a").text)
        elif soup.find("div",class_="pagination").find_all("li")[-2].find("a"):
            page_count = int(soup.find("div",class_="pagination").find_all("li")[-3].find("a").text)
        elif soup.find("div",class_="pagination").find_all("li")[-3].find("a"):
            page_count = int(soup.find("div",class_="pagination").find_all("li")[-3].find("a").text)

        for ech_page in range(1,page_count+1):
            url = 'https://www.citya.com/annonces/agence/177/location?page={}'.format(ech_page)
            print (url)
            yield scrapy.Request(
                url=url,
                callback=self.get_page_detail
                )



    def get_page_detail(self, response):
        soup=BeautifulSoup(response.body)
        # print (soup)

        all_article = soup.find_all("div",class_="informations")
        # print (all_article)
        for ech_art in all_article:
            title = ech_art.find("a").find("h3").get_text().strip()
            
            if "parking" not in title.lower():

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

                if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:

                    external_link = "https://www.citya.com"+ech_art.find("a")["href"]
                    yield scrapy.Request(
                        url=external_link,
                        callback=self.get_property_details,
                        meta = {"external_link":external_link,"property_type":property_type,"title":title}
                        )

    def get_property_details(self, response):
        item = ListingItem()
        soup=BeautifulSoup(response.body)

        external_link = response.meta.get("external_link")
        property_type = response.meta.get("property_type")
        title = response.meta.get("title")

        print (external_link)

        desc=soup.find("article",class_="description").find("p").getText()
        item["description"] = desc


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

        ap_type=soup.find("section",class_="otherDetail").find("ul").find_all("li")
        details = []
        for i in ap_type:
            details.append(i.getText().strip())

        external_id = details[0].replace("Réf :","")
        item["external_id"] = external_id

        for det in details:
            if "salle d'eau" in det:
                bathroom_count = getSqureMtr(det)
                item["bathroom_count"] = bathroom_count

        if soup.find("section",class_="energie") != None:
            energy = soup.find("section",class_="energie").find("div",class_="bilan").find("img")["src"]
            eng = (energy.split("/")[2])
            if eng.strip() != "0":
                item["energy_label"] = eng + " kWhEP/m².an"


        rents = soup.find("section",class_="detailPrix").find("ul").find_all("li")
        for r in rents:
            text = r.getText().strip()
            if "de dépôt de garantie" in text and getSqureMtr(text):
                item["deposit"] =getSqureMtr(text)
            if "Libre le" in text:
                available_date = text.replace("Libre le","").strip()
                item["available_date"] = format_date(available_date)


        
        if soup.find("section", class_="slider"):
            images_list =[]
            image=soup.find("section", class_="slider").find("div", class_="slider-for").find_all("img")
            for i in image:
                images_list.append("https://www.citya.com" + (i["src"]))

            if images_list:
                item["images"]= images_list            
                item["external_images_count"] = len(images_list)


        room_Nd_suface = soup.find("span", class_="typeBien").getText().strip()
        split_text = room_Nd_suface.split("pièce")

        item["room_count"] = getSqureMtr(split_text[0])
        item["square_meters"] = getSqureMtr(split_text[1])

        rent = soup.find("h2", class_="icon").find("span").getText()
        item["rent"] = getSqureMtr(rent)


        lat = soup.find("section", {"id":"modal-map"}).find("div", {"id":"map"})["data-latitude"]
        lon = soup.find("section", {"id":"modal-map"}).find("div", {"id":"map"})["data-longitude"]
        location = getAddress(lat,lon)
        address = location.address

        item["address"] = address
        item["latitude"] = lat
        item["longitude"] = lon 

        if "city" in location.raw["address"]:
            city = location.raw["address"]["city"]
            item["city"] = city
        elif "village" in location.raw["address"]:
            city = location.raw["address"]["village"]
            item["city"] = city


        postcode = location.raw["address"]["postcode"]
        item["zipcode"] = postcode

        item["landlord_name"] = "Citya Sogexfo"
        item["landlord_phone"] = "0549881861"
        item["currency"] = "EUR"
        item["external_source"] = "citya.com"
        item["external_link"] = external_link
        item["property_type"] = property_type
        item["title"] = title

        print(item)

        yield item