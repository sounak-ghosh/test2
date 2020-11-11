import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="myGeocoder")

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
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
    name = 'immobilier_net_PySpider_france_fr'
    allowed_domains = ['www.immobilier.net']
    start_urls = ['www.immobilier.net']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'


    def start_requests(self):
        yield scrapy.Request(
            url = "http://www.immobilier.net/rechercher.asp?genre=LOCATION&budgetmax=0",
            callback=self.parse
            )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        tot_prop = soup.find("ul",class_="pagination").find_all("li")[-2].text
        tot_prop = int(tot_prop)

        for i in range(1,tot_prop+1):
            url = "http://www.immobilier.net/rechercher.asp?budgetmin=0&budgetmax=0&type=&type=&type=&type=&type=&genre=LOCATION&cp=&cp=&cp=&cp=&cp=&categorie=&categorie=&categorie=&categorie=&categorie=&lieu=&lieu=&lieu=&lieu=&lieu=&page={}".format(i)
            yield scrapy.Request(
                url = url,
                callback=self.get_page_details
                )

    def get_page_details(self,response,**kwargs):

        soup = BeautifulSoup(response.body,"html.parser")
        all_property = soup.find_all("div",class_="col-md-12 enginebackground")

        for ech_prop in all_property:
            external_link = "http://www.immobilier.net/"+ech_prop.find("a",class_="btn btn-primary")["href"]

            yield scrapy.Request(
                url = external_link,
                callback=self.get_property_details
                )

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)


        item["landlord_name"] = "AFDI Martinique"
        item["landlord_phone"] = "0596 70 1000"
        item["landlord_email"] = "martinique@immobilier.net"
        item["external_source"] = "immobilier_net_PySpider_france_fr"
        item["currency"] = "EUR"
        item["external_link"] = response.url
        item["title"] = soup.find("h2",class_="page-header").text.split("\n")[0].strip()
        # item["square_meters"] = getSqureMtr(soup.find("h2",class_="page-header").find("a",href=False).text)

        property_type = soup.find("h2",class_="page-header").text.split("\n")[0].strip()

        if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
            property_type = "student_apartment"
        elif "appartement" in property_type.lower():
            property_type = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "house" in property_type.lower():
            property_type = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower() or "room" in property_type.lower():
            property_type = "room"
        elif "studio" in property_type.lower():
            property_type = "studio"
        else:
            property_type = "NA"



        all_div = soup.find_all("div",class_="col-lg-4")
        item["rent"] = getPrice(all_div[0].text)

        all_imgs = soup.find_all("div",class_="col-md-3")
        images_list = []
        for img in all_imgs:
            if img.find("a",class_=False).find("img",class_="img-responsive thumbnail"):
                images_list.append(img.find("a",class_=False)["href"])
        if images_list:
            item["images"] = images_list
            item["external_images_count"] = len(images_list)


        all_divs = soup.find_all("div",class_="col-md-12")
        description = all_divs[1].find("p").text.strip()
        item["description"] = description

        if "garage" in description.lower() or "parking" in description.lower() or "autostaanplaat" in description.lower():
            item["parking"]=True
        if "terras" in description.lower() or "terrace" in description.lower():
            item["terrace"]=True
        if "balcon" in description.lower() or "balcony" in description.lower():
            item["balcony"]=True
        if "zwembad" in description.lower() or "swimming" in description.lower():
            item["swimming_pool"]=True
        if "gemeubileerd" in description.lower() or "furnished" in description.lower():
            item["furnished"]=True
        if "machine à laver" in description.lower():
            item["washing_machine"]=True
        if "lave" in description.lower() and "vaisselle" in description.lower():
            item["dishwasher"]=True
        if "lift" in description.lower():
            item["elevator"]=True



        all_li = all_div[1].find_all("li")
        temp_dic = {}
        for ech_li in all_li:
            text_data = ech_li.text.strip().split(":")
            if len(text_data) == 2:
                key = text_data[0]
                vals = text_data[1].strip()
                temp_dic[key]=vals

        temp_dic = cleanKey(temp_dic)
        if "ville" in temp_dic:
            item["city"] = temp_dic["ville"]
            item["address"] = temp_dic["ville"]
        if "ref" in temp_dic:
            item["external_id"] = temp_dic["ref"]



        all_li = all_divs[2].find_all("li")
        temp_dic1 = {}
        for li in all_li:
            text_data = li.text.strip().split("\n")
            if len(text_data) == 2:
                keys = text_data[1].strip()
                vals = text_data[0].strip()
                temp_dic1[keys] = vals
            elif len(text_data) == 1:
                keys = text_data[0].strip()
                temp_dic1[keys] = None
            else:
                pass

        temp_dic1 = cleanKey(temp_dic1)

        if "surfacehabitable" in temp_dic1 and getSqureMtr(temp_dic1["surfacehabitable"]):
            item["square_meters"] = getSqureMtr(temp_dic1["surfacehabitable"])
        if "etage" in temp_dic1 :
            item["floor"] = temp_dic1["etage"]
        if "nombredepi_ces" in temp_dic1 and getSqureMtr(temp_dic1["nombredepi_ces"]):
            item["room_count"] = getSqureMtr(temp_dic1["nombredepi_ces"])
        if "nombredeterrasses" in temp_dic1 and temp_dic1["nombredeterrasses"]:
            item["terrace"] = True
        if "monte_charge" in temp_dic1 and temp_dic1["monte_charge"]:
            item["elevator"] = True
        if  "piscine" in temp_dic1 and temp_dic1["monte_charge"] == "Non":
            item["swimming_pool"] = False
        if  "piscine" in temp_dic1 and temp_dic1["monte_charge"] == "Oui":
            item["swimming_pool"] = True
        if "nombredebalcons" in temp_dic1 and temp_dic1["nombredebalcons"]:
            item["balcony"] = True
        if ("nombredeparkingint_rieur" in temp_dic1 and temp_dic1["nombredeparkingint_rieur"]) or ("nombredeparkingext_rieur" in temp_dic1 and temp_dic1["nombredeparkingext_rieur"]):
            item["parking"] = True


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            item["property_type"] = property_type
            print (item)
            yield item
