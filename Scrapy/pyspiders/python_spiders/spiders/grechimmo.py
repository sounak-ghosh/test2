import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests
import geopy
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



    if len(list_text) == 3:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 2:
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

class laforet(scrapy.Spider):
    name = 'grechimmo'
    allowed_domains = ['www.grechimmo.fr']
    start_urls = ['www.grechimmo.fr']
    execution_type = 'testing'
    country = 'french'
    locale ='fr'

    def start_requests(self):
        start_urls = [{"url":"https://www.grechimmo.fr/catalog/advanced_search_result.php?keywords=&C_33_search=SUPERIEUR&C_33_type=NUMBER&C_33_MIN=&C_33_tmp=0&C_34_search=COMPRIS&C_34_type=NUMBER&C_34_MIN=&C_34_MAX=&action=update_search&search_id=1681040143212908&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_28_tmp=Location&C_27_search=EGAL&C_27_type=TEXT&C_27=2&C_27_tmp=2&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MIN=0&C_30_MAX=0&C_65_search=CONTIENT&C_65_type=TEXT&C_65=",
        "property_type":"house"},
        {"url":"https://www.grechimmo.fr/catalog/advanced_search_result.php?keywords=&C_33_search=SUPERIEUR&C_33_type=NUMBER&C_33_MIN=&C_33_tmp=0&C_34_search=COMPRIS&C_34_type=NUMBER&C_34_MIN=&C_34_MAX=&action=update_search&search_id=1681040143212908&C_28_search=EGAL&C_28_type=UNIQUE&C_28=Location&C_28_tmp=Location&C_27_search=EGAL&C_27_type=TEXT&C_27=1&C_27_tmp=2&C_30_search=COMPRIS&C_30_type=NUMBER&C_30_MIN=0&C_30_MAX=0&C_65_search=CONTIENT&C_65_type=TEXT&C_65=",
        "property_type":"apartment"}]

        for urls in start_urls:
            yield scrapy.Request(
                url=urls.get('url'),
                callback=self.parse,
                meta = {"url":urls.get("url"),"property_type":urls.get("property_type")}
                )



    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        all_page = soup.find("ul",class_="pagination").find_all("li")

        property_type = response.meta.get("property_type")

        if num_there(all_page[-1].text.strip()):
            pages = int(all_page[-1].text.strip())
        else:
            pages = int(all_page[-2].text.strip())

        for pg in range(1,pages+1):
            page_url = response.meta.get("url")+"&page="+str(pg)

            yield scrapy.Request(
                url=page_url,
                callback=self.get_page_details,
                meta = {"property_type":property_type}
                )


    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")

        list_urls = []
        if soup.find("div",id="listing_bien"):
            all_list = soup.find("div",id="listing_bien").find_all("div",class_="product-infos")
            for ech_p in all_list:
                external_link = "https://www.grechimmo.fr/"+ech_p.find("a",recursive =False)["href"].replace("../","")
                title = ech_p.find("a",recursive =False)["title"]
                print (external_link)
                yield scrapy.Request(
                    url = external_link,
                    callback =self.get_property_details,
                    meta = {"property_type":property_type,"external_link":external_link,"title":title}
                    )


       
    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        str_soup = str(soup)

        item["external_link"] = response.meta.get("external_link")
        item["title"] = response.meta.get("title")
        item["property_type"] = response.meta.get("property_type")
        item["currency"] = "EUR"
        item["external_source"] = "grechimmo.fr"


        extract_ref_id = re.findall("Ref. :(.+)<",str_soup)
        item["external_id"] = extract_ref_id[0].strip()


        extract_lat_lon = re.findall("var myLatlng = new google.maps.LatLng(.+);",str_soup)

        latitude = eval(extract_lat_lon[0])[0]
        longitude = eval(extract_lat_lon[0])[1]
        location = getAddress(latitude,longitude)

        item["address"] = location.address
        item["latitude"] = str(latitude)
        item["longitude"] = str(longitude)



        if soup.find("div",class_="container-slider"):
            img_lst = []
            for pics in soup.find("div",class_="container-slider").find_all("a"):
                if pics["href"]!="#":
                    img_lst.append("https://www.grechimmo.fr/"+pics["href"].replace("../",""))

            if img_lst:
                item["images"] = img_lst
                item["external_images_count"] = len(img_lst)


        if soup.find("div",class_="infos-biens-right"):
            item["description"] = soup.find("div",class_="infos-biens-right").text.strip()


        if soup.find("ul",class_="detail-panel"):
            temp_dic = {}
            all_det = soup.find("ul",class_="detail-panel").find_all("div",class_="infos-bien")
            for ech_d in all_det:
                if ech_d.find("div",class_="text") and ech_d.find("div",class_="value"):
                    ky=ech_d.find("div",class_="text").text.strip()
                    vals = ech_d.find("div",class_="value").text.strip()
                    temp_dic.update({ky:vals})

            temp_dic = cleanKey(temp_dic)
            
            if "ville" in temp_dic:
              item["city"] = temp_dic["ville"]

            if "codepostal" in temp_dic:
              item["zipcode"] = temp_dic["codepostal"]

            if "surface" in temp_dic:
              item["square_meters"] = getSqureMtr(temp_dic["surface"])

            if "provisionsurcharges" in temp_dic:
              item["utilities"] = getSqureMtr(temp_dic["provisionsurcharges"])

            if "d_p_tdegarantie" in temp_dic:
              item["deposit"] = getSqureMtr(temp_dic["d_p_tdegarantie"])

            if "nombrepi_ces" in temp_dic:
                item["room_count"] = getSqureMtr(temp_dic["nombrepi_ces"])

            if "salle_s_debains" in temp_dic:
                item["bathroom_count"] = getSqureMtr(temp_dic["salle_s_debains"])

            if "etage" in temp_dic:
                item["floor"] = temp_dic["etage"]

            if "valeurconsoannuelle_nergie" in temp_dic:
                item["energy_label"] = temp_dic["valeurconsoannuelle_nergie"]

            if "disponibilit" in temp_dic and num_there(temp_dic["disponibilit"]):
                item["available_date"] = format_date(temp_dic["disponibilit"])


            if "nombreplacesparking" in temp_dic:
                item["parking"] = True

            if "nombrebalcons" in temp_dic:
                item["balcony"] = True

            if "nombredeterrasses" in temp_dic:
                item["terrace"] = True

            if "piscine" in temp_dic and temp_dic["piscine"] == "Non":
                item["swimming_pool"] = False
            if "piscine" in temp_dic and temp_dic["piscine"] == "Oui":
                item["swimming_pool"] = True

            if "ascenseur" in temp_dic and temp_dic["ascenseur"] == "Non":
                item["elevator"] = False
            elif "ascenseur" in temp_dic and temp_dic["ascenseur"] == "Oui":
                item["elevator"] = True


        print (item)
        yield item