import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime
# from geopy.geocoders import Nominatim

# geolocator = Nominatim(user_agent="test_app")

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date

def num_there(s):
    return any(i.isdigit() for i in s)

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

    if len(list_text) == 2:
        output = int(list_text[0])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = int(float(list_text[0]+list_text[1]))
    elif len(list_text) == 2:
        output = int(float(list_text[0]+list_text[1]))
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0
    return output

def getRent(text):
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

class auditaSpider(scrapy.Spider):
    name = 'Immoexpat_PySpider_france'
    allowed_domains = ['www.immoexpat.be']
    start_urls = ['www.immoexpat.be']
    execution_type = 'testing'
    country = 'fr'
    locale ='en'

    global i 
    i = 0
    global all_external_links 
    all_external_links = []

    start_urls = ["https://www.immoexpat.be/en-GB/List/PartialListEstate?EstatesList=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.Estate%5D&EstateListForNavigation=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.Estate%5D&SelectedType=System.Collections.Generic.List%601%5BSystem.String%5D&Categories=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&MinPrice=0&MaxPriceSlider=10000&ListID=21&SearchType=ToRent&SearchTypeIntValue=0&Cities=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&SelectedRegion=0&Regions=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&SortParameter=Date_Desc&Furnished=False&InvestmentEstate=False&NewProjects=False&CurrentPage={}".format(i)]

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        if response.meta.get('j'):
            j = response.meta.get('j')
        else:
            j = 0
        if soup.find("a",class_="estate-card estate-card---description-on-over"):
            for ech_prop in soup.find_all("a",class_="estate-card estate-card---description-on-over"):
                if "flat" in ech_prop["href"] or "house" in ech_prop["href"]:
                    all_external_links.append("https://www.immoexpat.be"+ech_prop["href"])
            j = j + 1
            link = "https://www.immoexpat.be/en-GB/List/PartialListEstate?EstatesList=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.Estate%5D&EstateListForNavigation=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.Estate%5D&SelectedType=System.Collections.Generic.List%601%5BSystem.String%5D&Categories=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&MinPrice=0&MaxPriceSlider=10000&ListID=21&SearchType=ToRent&SearchTypeIntValue=0&Cities=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&SelectedRegion=0&Regions=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&SortParameter=Date_Desc&Furnished=False&InvestmentEstate=False&NewProjects=False&CurrentPage={}".format(j)
            yield scrapy.Request(url=link,
                             callback=self.parse, meta={'j': j})
                    
        else:
            for l in all_external_links:
                yield scrapy.Request(url=l,
                             callback=self.get_property_details, meta={'external_link': l})

    def get_property_details(self, response):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        item["external_link"] = response.meta.get('external_link')

        temp_title = soup.find("div", class_="section-intro estate-detail-intro").text.splitlines()
        temp_title = list(filter(None, temp_title))
        title = ""
        for t in temp_title:
            if t:
                title = title+t.strip()+" "
        
        item["title"] = title
        item["rent"] = getPrice(title.split("-")[-1])

        item["description"] = soup.find("div", class_="col-md-9").find("p").text.strip()
        
        item["address"] = soup.find("div", class_="col-md-9").find("h3").find_next_sibling().text

        temp_dic = {}
        for ech_h2 in soup.find("div", class_="col-md-9").find_all("h2"):
            if "general" in ech_h2.text.lower():
                for ech_tr in ech_h2.find_next_sibling().find_all("tr"):
                    temp_dic[ech_tr.find("th").text] = ech_tr.find("td").text
            if "exterior" in ech_h2.text.lower():
                for ech_tr in ech_h2.find_next_sibling().find_all("tr"):
                    temp_dic[ech_tr.find("th").text] = ech_tr.find("td").text
            if "interior" in ech_h2.text.lower():
                for ech_tr in ech_h2.find_next_sibling().find_all("tr"):
                    temp_dic[ech_tr.find("th").text] = ech_tr.find("td").text
            if "ground" in ech_h2.text.lower():
                for ech_tr in ech_h2.find_next_sibling().find_all("tr"):
                    temp_dic[ech_tr.find("th").text] = ech_tr.find("td").text
            if "communication" in ech_h2.text.lower():
                for ech_tr in ech_h2.find_next_sibling().find_all("tr"):
                    temp_dic[ech_tr.find("th").text] = ech_tr.find("td").text

        temp_dic = cleanKey(temp_dic)
        
        if "reference" in temp_dic:
            item["external_id"] = temp_dic["reference"]

        if "category" in temp_dic:
            if "house" in temp_dic["category"] or "villa" in temp_dic["category"] or "bel-etage" in temp_dic["category"]:
                property_type = "house"
            elif "flat" in temp_dic["category"] or "studio" in temp_dic["category"] or "ground" in temp_dic["category"] or "duplex" in temp_dic["category"]:
                property_type = "apartment"
            else:
                property_type = "NA"
            item["property_type"] = property_type

        if "numberofbedrooms" in temp_dic:
            item["room_count"] = int(temp_dic["numberofbedrooms"])
            
        if "numberofbathrooms" in temp_dic:
            item["bathroom_count"] = int(temp_dic["numberofbathrooms"])
            
        if "habitablesurface" in temp_dic:
            item["square_meters"] = getSqureMtr(temp_dic["habitablesurface"])
            
        if "availability" in temp_dic:
            if num_there(temp_dic["availability"]):
                item["available_date"] = strToDate(temp_dic["availability"])
                
        if "floors_number" in temp_dic:
            item["floor"] = temp_dic["floors_number"]
        
        if "elevator" in temp_dic:
            if "yes" in temp_dic["elevator"].lower():
                item["elevator"] = True
            if "no" in temp_dic["elevator"].lower():
                item["elevator"] = False
            
        if "parking" in temp_dic:
            if "yes" in temp_dic["parking"].lower():
                item["parking"] = True
            if "no" in temp_dic["parking"].lower():
                item["parking"] = False
            
        if "terrace" in temp_dic:
            if "yes" in temp_dic["terrace"].lower():
                item["terrace"] = True
            if "no" in temp_dic["terrace"].lower():
                item["terrace"] = False
            
        if "furnished" in temp_dic:
            if "yes" in temp_dic["furnished"].lower():
                item["furnished"] = True
            if "no" in temp_dic["furnished"].lower():
                item["furnished"] = False
        
        if "pool" in temp_dic:
            if "yes" in temp_dic["pool"].lower():
                item["swimming_pool"] = True
            if "no" in temp_dic["pool"].lower():
                item["swimming_pool"] = False

        extract_text = re.findall("myLatLng = new google.maps.LatLng(.+)",str(soup))
        lat_lon = eval(extract_text[0])
        item["latitude"] = str(lat_lon[0])
        
        item["longitude"] = str(lat_lon[1])

        # location = getAddress(lat_lon[0],lat_lon[1])
        # address = location.address
        # if "city" in location.raw["address"]:
        #     city = location.raw["address"]["city"]
        #     item["city"] = city
        # elif "town" in location.raw["address"]:
        #     city = location.raw["address"]["town"]
        #     item["city"] = city
        # elif "village" in location.raw["address"]:
        #     city = location.raw["address"]["village"]
        #     item["city"] = city
        # if "postcode" in location.raw["address"]:
        #     postcode = location.raw["address"]["postcode"]
        #     item["zipcode"] = postcode

        image_list = []
        for ech_img in soup.find("div", class_="estate-detail-carousel__body").find_all("div", class_="item"):
            image_list.append(ech_img.find("a")["href"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        item["landlord_phone"] = "+32 470 10 11 00"
        item["landlord_email"] = "info@immoexpat.be"
        item["currency"] = "EUR"
        item["external_source"] = "Immoexpat_PySpider_france"
        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item