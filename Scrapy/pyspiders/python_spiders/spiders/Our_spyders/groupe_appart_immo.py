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
    name = 'groupe_appart_immo_PySpider_france_fr'
    allowed_domains = ['www.groupe-appart-immo.com']
    start_urls = ['www.groupe-appart-immo.com']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'


    def start_requests(self):
        for i in range(1,3):
            
            if i==1:
                property_type = "apartment"
            elif i==2:
                property_type = "house"
                
            url = "https://www.groupe-appart-immo.com/catalog/advanced_search_result.php?action=update_search&search_id=1681977458717769&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_27_search=EGAL&C_27_type=TEXT&C_27={}&C_27_tmp={}&C_33_search=COMPRIS&C_33_type=NUMBER&C_33_MIN=&C_33_MAX=&C_30_MIN=&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MAX=&C_65_search=CONTIENT&C_65_type=TEXT&C_65=".format(i,i)
            
            yield scrapy.Request(
                url = url,
                callback=self.parse,
                meta = {"property_type":property_type,"index":i}
            )

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        index_val = response.meta["index"]

        if soup.find("div",class_="openSans"):
            all_li = soup.find("div",class_="openSans").find("ul").find_all("li")
            count=int(all_li[-2].text)

            for c in range(count):
                url = "https://www.groupe-appart-immo.com/catalog/advanced_search_result.php?action=update_search&search_id=1681977458717769&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_27_search=EGAL&C_27_type=TEXT&C_27={}&C_27_tmp={}&C_33_search=COMPRIS&C_33_type=NUMBER&C_33_MIN=&C_33_MAX=&C_30_MIN=&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MAX=&C_65_search=CONTIENT&C_65_type=TEXT&C_65=&&page={}".format(index_val,index_val,c+1)
                yield scrapy.Request(
                    url = url,
                    callback=self.get_page_details,
                    meta = {"property_type":response.meta["property_type"]}
                    )


    def get_page_details(self,response,**kwargs):

        soup = BeautifulSoup(response.body,"html.parser")

        ext_link = soup.find_all("div", class_="display-cell w100 verticalTop")
        for e_x in ext_link:
            external_link="https://www.groupe-appart-immo.com"+e_x.find("a")["href"].replace("..","")

            yield scrapy.Request(
                url = external_link,
                callback=self.get_property_details,
                meta = {"property_type":response.meta["property_type"]}
                )


    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)

        title = soup.find("div", class_="col-xs-12 col-sm-12 col-md-6 col-lg-6").find("h2").text
        item["title"] = title

        ref = soup.find("div",class_="col-xs-12 col-sm-12 col-md-12 col-lg-12").find_all("li")
        for r in ref:
            if "Ref.".lower() in r.text.lower():
                reference = r.text.replace("Ref. :","").strip()
                item["external_id"] = reference

        extract_text = re.findall("var myLatlng = new google.maps.LatLng(.+);",str_soup)
        lat_long1 = eval(extract_text[0])
        lat1 = str(lat_long1[0])
        long1 = str(lat_long1[1])

        item["latitude"] = lat1
        item["longitude"] = long1
        
        # location = getAddress(lat1,long1)
        # address = location.address
        # item["address"]=address


        desc = soup.find("div",class_="product-desc").text.strip()
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



        details = soup.find("div", class_="detail-panel").find_all("div",class_="infos-bien")
        temp_dic = {}
        for d in details:
            text = (d.find("div",class_="text").text.replace(" : ",""))
            value = (d.find("div",class_="value").text)
            temp_dic[text] = value
        temp_dic = cleanKey(temp_dic)

        # if "typedebien" in temp_dic:
        #     ap_type = temp_dic["typedebien"].strip().lower()
            # print(ap_type)

        if "ville" in temp_dic:
            city = temp_dic["ville"].strip().lower()
            item["city"]=city

        if "codepostal" in temp_dic:
            postcode = temp_dic["codepostal"]
            item["zipcode"]=postcode

        if "etage" in temp_dic:
            floor = temp_dic["etage"]
            item["floor"]=floor

        if "provisionsurcharges" in temp_dic:
            utilities = getSqureMtr(temp_dic["provisionsurcharges"])
            item["utilities"]=utilities

        if "d_p_tdegarantie" in temp_dic:
            deposit = getSqureMtr(temp_dic["d_p_tdegarantie"])
            item["deposit"]=deposit

        if "nombrepi_ces" in temp_dic:
            rooms = getSqureMtr(temp_dic["nombrepi_ces"])
            item["room_count"]=rooms

        if "salle_s_debains" in temp_dic:
            bathrooms = getSqureMtr(temp_dic["salle_s_debains"])
            item["bathroom_count"]=bathrooms
            

        if "surface" in temp_dic:
            area = getSqureMtr(temp_dic["surface"].strip())
            item["square_meters"]=area
            

        if "disponibilit" in temp_dic:
            date = format_date(temp_dic["disponibilit"])
            item["available_date"]=date

        if "valeurconsoannuelle_nergie" in temp_dic:
            power = str(getSqureMtr(temp_dic["valeurconsoannuelle_nergie"]))
            if int(power.strip()) != 0:
                item["energy_label"]= power+" kWhEP/m².an"

        image_list = []
        img = soup.find("div", class_="container-fluid").find_all("li")
        for im in img:
            image_list.append("https://www.groupe-appart-immo.com"+im.find("a")["href"].replace("..",""))
        if image_list:
            item["images"]=image_list
            item["external_images_count"]=len(image_list)


        rent =getPrice(soup.find("div", class_="col-xs-12 col-sm-12 col-md-6 col-lg-6").find("div", class_="prix loyer").text)
        item["rent"]=rent
        item["currency"] = "EUR"
        item["external_source"] = "groupe_appart_immo_PySpider_france_fr"
        item["external_link"] = response.url
        item["property_type"] = response.meta["property_type"]

        print (item)
        yield item
