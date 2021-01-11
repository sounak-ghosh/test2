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
    name = 'audras_delaunois_PySpider_france_fr'
    allowed_domains = ['audras-delaunois.com']
    start_urls = ['audras-delaunois.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://audras-delaunois.com/location-immobiliere-isere.php"}]

        for url in start_urls:
            yield scrapy.Request(
                url = url.get("url"),
                callback = self.parse
                ) 

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
      
        all_ext_link = soup.find_all("div",class_="column col-md-12 col-6 search-result")
        for a_e_l in all_ext_link:
            prop_typ = a_e_l.find("div",class_="card-title h5").text.strip()
            if "tudiant" in prop_typ.lower() or  "studenten" in prop_typ.lower() and "appartement" in prop_typ.lower():
                property_type = "student_apartment"
            elif "appartement" in prop_typ.lower():
                property_type = "apartment"
            elif "woning" in prop_typ.lower() or "maison" in prop_typ.lower() or "huis" in prop_typ.lower() or "duplex" in prop_typ.lower():
                property_type = "house"
            elif "chambre" in prop_typ.lower() or "kamer" in prop_typ.lower():
                property_type = "room"
            elif "studio" in prop_typ.lower():
                property_type = "studio"
            else:
                property_type = "NA"

            if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                external_link = "https://audras-delaunois.com"+a_e_l.find("a")["href"]

                yield scrapy.Request(
                    url=external_link,
                    callback=self.get_property_details,
                    meta = {"property_type":property_type}
                    )


       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        str_soup = str(soup)

        external_link = response.url
        property_type = response.meta.get("property_type")

        title = soup.find("div",class_="section-bien-title bg-light-gray").find("h2").text.strip()
        item["title"]=title

        ref_no = soup.find("div", class_="bread").find("li").get_text()
        ref_no = ref_no.replace("Référence :","").strip()
        item["external_id"]=ref_no

        power = soup.find("div", class_="panel").find("img")["src"].split("=")
        if len(power) > 1:
            item["energy_label"] = power[1] + " kWhEP/m².an"


        extract_text = re.findall("var bienLatLng =(.+);",str_soup)
        lat_lon = extract_text[0].strip()
        lat_lon = eval(lat_lon.replace("lat",'"latitude"').replace("lng",'"longitude"'))

        if lat_lon["latitude"] and lat_lon["longitude"]:
            lat=str(lat_lon["latitude"])
            lon=str(lat_lon["longitude"])

            # location=getAddress(lat,lon)
            item["latitude"] = lat
            item["longitude"] = lon

            # if "city" in location.raw["address"]:
            #     city = location.raw["address"]["city"]
            #     item["city"] = city
            # elif "town" in location.raw["address"]:
            #     city = location.raw["address"]["town"]
            #     item["city"] = city
            # elif "village" in location.raw["address"]:
            #     city = location.raw["address"]["village"]
            #     item["city"] = city

            # postcode = location.raw["address"]["postcode"]
            # item["zipcode"] = postcode
        

        d = soup.find("div", class_="column col-md-12 col-8").find_all("h2")
        p = soup.find("div", class_="column col-md-12 col-8").find_all("p")

        for index,value in enumerate(d):
            if "Description".lower() in value.text.lower(): 
                desc = p[index].text.strip()
                item["description"] = desc
                if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                    item["parking"] = True
                if "terras" in desc.lower() or "terrace" in desc.lower():
                    item["terrace"] = True
                if "balcon" in desc.lower() or "balcony" in desc.lower():
                    item["balcony"] = True
                if "zwembad" in desc.lower() or "swimming" in desc.lower():
                    item["swimming_pool"] = True
                if "gemeubileerd" in desc.lower() or "furnished" in desc.lower() or "meublé" in desc.lower():
                    item["furnished"] = True
                if "machine à laver" in desc.lower():
                    item["washing_machine"] = True
                if "lave" in desc.lower() and "vaisselle" in desc.lower():
                    item["dishwasher"] = True
                if "lift" in desc.lower():
                    item["elevator"] = True

            if "Adresse".lower() in value.text.lower():
                address = p[index].text.strip()
                item["address"] = address
            try:
                item['city'] = title.split("·")[0]
            except:
                pass    
            try:
               zp = address.split()[::-1]
               for z in zp:
                if num_there(z):
                    item['zipcode'] = z
                    break
            except:
                pass    

        all_li = soup.find("div",class_="columns details").find("ul").find_all("li")
        temp_dic = {}
        for a_l in all_li:
            temp_det = a_l.text
            temp_det = temp_det.split(":")
            if len(temp_det) == 2:
                key = temp_det[0]
                value = temp_det[1].strip()
                temp_dic[key] = value
        temp_dic = cleanKey(temp_dic)
        print(">>>>>>>>>>>",temp_dic)
        if "disponibilit" in temp_dic:
            if num_there(temp_dic["disponibilit"]):
                date = temp_dic["disponibilit"].replace("Le ","").strip()
                date = format_date(date)
                item["available_date"] = date

        if "surfacehabitable" in temp_dic or 'Surface habitable' in temp_dic:
            try:
                area = temp_dic["Surface habitable"]
            except:
                area = temp_dic["surfacehabitable"]
                    
            area = getSqureMtr(area)
            item["square_meters"] = area

        if "d_p_tdegarantie" in temp_dic or "Dépôt de garantie" in temp_dic:
            try:
                deposit = getSqureMtr(temp_dic["Dépôt de garantie"].replace(" ","")) 
                
            except:
                deposit = getSqureMtr(temp_dic["d_p_tdegarantie"].replace(" ",""))   
            item["deposit"]=deposit

        if "loyerchargescomprises" in temp_dic or "Loyer charges comprises" in temp_dic:
            try:
                rent = getSqureMtr(temp_dic["Loyer charges comprises"].replace(" ","")) 
            except:
                rent = getSqureMtr(temp_dic["loyerchargescomprises"].replace(" ",""))   
            item["rent"] = rent

        if "dontprovisionsurcharges" in temp_dic:
            utilities = getSqureMtr(temp_dic["dontprovisionsurcharges"])
            item["utilities"]=utilities



        for li in soup.find("ul",class_="details-list").find_all("li"):
            temp_dic[str(li).split("</i>")[0].split('">')[1]]  = str(li).split("</i>")[1].replace("</li>","")
        temp_dic = cleanKey(temp_dic)

        if "swap_vert" in temp_dic:
            floor = temp_dic["swap_vert"].strip()
            item["floor"]=floor

        if "hotel" in temp_dic:
            rooms = getSqureMtr(temp_dic["hotel"])
            item["room_count"] = rooms


        if soup.find("div",class_="section-slider section-slider-nav") != None: 
            img = soup.find("div",class_="section-slider section-slider-nav").find_all("img")
            image_list = []
            for i in img:
                image_list.append(i["src"])

            if image_list:
                item["images"] = image_list
                item["external_images_count"]= len(image_list)


        item["currency"] = "EUR"
        item["landlord_name"] = "Grenette Agency"
        item["landlord_phone"] = "0476447628"
        item["landlord_email"] = "grenette@audras-delaunois.com"
        item["external_source"] = "audras_delaunois_PySpider_france_fr"
        item["external_link"] = external_link
        item["property_type"] = property_type

        print (item)
        yield item
