# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time
# from geopy.geocoders import Nominatim

# geolocator = Nominatim(user_agent="myGeocoder")

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng)
#     location = geolocator.reverse(coordinates)
#     return location

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


class laforet(scrapy.Spider):
    name = 'bonnabelle_PySpider_france_fr'
    allowed_domains = ['www.bonnabelle.fr']
    start_urls = ['www.bonnabelle.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'


    def start_requests(self):
        yield scrapy.Request(
            url = "http://www.bonnabelle.fr/louer.html",
            callback=self.parse
            )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        tot_prop = soup.find("div",class_="col-6 titreResultat").text
        tot_prop = getSqureMtr(tot_prop)

        count = tot_prop//100

        for i in range(count+1):
            url = "http://www.bonnabelle.fr/?c=categories&a=getProduitAjax&idc=1&numpage={}&nbpage=100&reference=&type_bien=&surface_min=&surface_max=&localisation=&budget_min=&budget_max=&c=categories&a=index&c=categories&a=getProduitAjax".format(i+1)
            yield scrapy.Request(
                url = url,
                callback=self.get_page_details
                )

    def get_page_details(self,response,**kwargs):

        soup = BeautifulSoup(response.body,"html.parser")
        article = soup.find_all("div",class_="vignette location")

        for ech_art in article:
            dic={}
            ap_type = ech_art.find("div",class_="lieu").find("span",class_="type").get_text()

            if "tudiant" in ap_type.lower() or  "studenten" in ap_type.lower() and "appartement" in ap_type.lower():
                property_type = "student_apartment"
            elif "appartement" in ap_type.lower():
                property_type = "apartment"
            elif "woning" in ap_type.lower() or "maison" in ap_type.lower() or "huis" in ap_type.lower():
                property_type = "house"
            elif "chambre" in ap_type.lower() or "kamer" in ap_type.lower():
                property_type = "room"
            elif "studio" in ap_type.lower():
                property_type = "studio"
            else:
                property_type = "NA"

            dic["property_type"] = property_type 

            if property_type in ["student_apartment","apartment","house","room","studio"]:
                desc = ech_art.find("div",class_="description").get_text().strip()
                dic["description"] = desc

                if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                    dic["parking"] = True
                if "terras" in desc.lower() or "terrace" in desc.lower():
                    dic["terrace"] = True
                if "balcon" in desc.lower() or "balcony" in desc.lower():
                    dic["balcony"] = True
                if "zwembad" in desc.lower() or "swimming" in desc.lower():
                    dic["swimming_pool"] = True
                if "gemeubileerd" in desc.lower() or "furnished" in desc.lower():
                    dic["furnished"] = True
                if "machine à laver" in desc.lower():
                    dic["washing_machine"] = True
                if "lave" in desc.lower() and "vaisselle" in desc.lower():
                    dic["dishwasher"] = True
                if "lift" in desc.lower():
                    dic["elevator"] = True

                area = ech_art.find("div",class_="dimension").find("span",class_="superficie").get_text()
                area = getSqureMtr(area)
                dic["square_meters"] = area
                
                rooms = ech_art.find("div",class_="dimension").find("span",class_="pieces").get_text()
                rooms = getSqureMtr(rooms)
                dic["room_count"] = rooms
                
                rent = ech_art.find("div",class_="detailLigne").find("span",class_="prix").get_text()
                rent = getSqureMtr(rent)
                dic["rent"] = rent
                
                ext_link = ech_art.find("div",class_="detailLigne").find("a")["href"]
                print (ext_link)
                yield scrapy.Request(
                    url = ext_link,
                    callback=self.get_property_details,
                    meta = dic
                    )



    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup1 = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup1)

        title = soup1.find("div", class_="col-12 col-lg-6 titreResultat").find("strong").get_text()
        item["title"] = title

        ref_num = soup1.find("div", class_="col-12 col-md-8").find("span").get_text()
        item["external_id"] = ref_num

        if soup1.find("div",class_="consommation").find("span",class_="valeur") != None:
            energy_lab = soup1.find("div",class_="consommation").find("span",class_="valeur").find("span").get_text().strip()
            if int(energy_lab.strip()) != 0:
                item["energy_label"] = energy_lab + " kWhEP/m².an"


        match = re.findall(r"center:(.+),",str_soup)
        if match:
            cordinates = eval(match[0])

            latitude = cordinates[1]
            longitude = cordinates[0]
            item["latitude"] = str(latitude)
            item["longitude"] = str(longitude)

            # location = getAddress(latitude,longitude)
            # postcode = location.raw["address"]["postcode"]
            # item["zipcode"] = postcode


        img = soup1.find("div", class_="owlImg owl-carousel owl-theme").find_all("source")
        images_list = []
        for i in img:
            images_list.append("http://www.bonnabelle.fr"+i["srcset"])
        if images_list:
            item["images"] = images_list
            item["external_images_count"] = len(images_list)


        if soup1.find("div",class_="caracteristiques"):
            charcteristic = soup1.find("div",class_="caracteristiques").find("div",class_="row")

            all_details = charcteristic.find_all("div","row")
            temp_dic= {}
            for divs in all_details:

                if divs.find("div",class_="col-4") and divs.find("div",class_="col-8"):
                    key = divs.find("div",class_="col-4").text
                    vals = divs.find("div",class_="col-8").text
                    temp_dic[key] = vals

            temp_dic = cleanKey(temp_dic)

            if "disponibilit" in temp_dic:
                date = temp_dic["disponibilit"].strip()
                item["available_date"] = format_date(date)
            
            if "adresse" in temp_dic:
                address = temp_dic["adresse"].strip()
                item["address"] = address

            if "charges" in temp_dic:
                utilities = temp_dic["charges"]
                utilities = getSqureMtr(utilities)
                item["utilities"] = utilities

            if "ville" in temp_dic:
                city = temp_dic["ville"].strip()
                item["city"] = city

            if "tage" in temp_dic:
                floor = temp_dic["tage"].strip()
                item["floor"] = floor


        main_details = response.meta

        if "rent" in main_details:
            item["rent"] = main_details["rent"]

        if "description" in main_details:
            item["description"] = main_details["description"]

        if "room_count" in main_details:
            item["room_count"] = main_details["room_count"]

        if "square_meters" in main_details:
            item["square_meters"] = main_details["square_meters"]

        if "washing_machine" in main_details:
            item["washing_machine"] = main_details["washing_machine"]

        if "elevator" in main_details:
            item["elevator"] = main_details["elevator"]

        if "dishwasher" in main_details:
            item["dishwasher"] = main_details["dishwasher"]

        if "parking" in main_details:
            item["parking"] = main_details["parking"]

        if "balcony" in main_details:
            item["balcony"] = main_details["balcony"]

        if "terrace" in main_details:
            item["terrace"] = main_details["terrace"]

        if "swimming_pool" in main_details:
            item["swimming_pool"] = main_details["swimming_pool"]

        if "furnished" in main_details:
            item["furnished"] = main_details["furnished"]


        item["external_link"] = response.url
        item["property_type"] = main_details["property_type"]
        item["currency"] = "EUR"
        item["landlord_name"] = "Marielle Peltier"
        item["landlord_phone"] = "0383175862"
        item["landlord_email"] = "mpeltier@bonnabelle.com"
        item["external_source"] = "bonnabelle_PySpider_france_fr"

        print (item)
        yield item
