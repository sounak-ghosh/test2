# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
from datetime import datetime
import math

def num_there(s):
    return any(i.isdigit() for i in s)

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)
    if len(list_text) > 0:
        output = int(list_text[0])
    else:
        output=0

    return output

def getPrice(text):
    list_text = re.findall(r'\d+',text)
    if "." in text:
        if len(list_text) == 3:
            output = int(float(list_text[0]+list_text[1]))
        elif len(list_text) == 2:
            output = int(float(list_text[0]))
        elif len(list_text) == 1:
            output = int(list_text[0])
        else:
            output=0
    else:
        if len(list_text) == 2:
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

class spiderQoutes(scrapy.Spider):
    name = 'Talbies_Co_PySpider_united_kingdom'
    allowed_domains = ['talbies.co.uk']
    start_urls = ['talbies.co.uk']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'

    header = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36/8mqLkJuL-86"}

    def start_requests(self):
        start_url = 'https://talbies.co.uk/residential-lettings'
        yield scrapy.Request(url = start_url, callback = self.parse1)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        tot_prop = int(soup.find("div", class_="col-md-12").find("h1").text.split(" of ")[-1].strip())
        page_count = math.ceil(tot_prop/12)        
        for ech_pg in range(1,page_count):
            url = f"https://talbies.co.uk/notices?c=44&p={ech_pg+1}"
            yield scrapy.Request(url = url, callback = self.parse2)

        for ech_prop in soup.find("div", class_="row properties-grid content").find_all("div", class_="property_thumb"):
            external_link = "https://talbies.co.uk"+ech_prop.find("a")["href"]
            # print(external_link)
            if ech_prop.find("div", class_="property_badge"):
                if "let" in ech_prop.find("div", class_="property_badge").text.lower() or "withdrawn" in ech_prop.find("div", class_="property_badge").text.lower():
                    pass
                else:
                    print(ech_prop.find("div", class_="property_badge").text)
                    yield scrapy.Request(url = external_link, headers = self.header, callback = self.get_property_details, meta = {"external_link":external_link, 'dont_redirect': True})
            else:
                yield scrapy.Request(url = external_link, headers = self.header, callback = self.get_property_details, meta = {"external_link":external_link,'dont_redirect': True})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        for ech_prop in soup.find("div", class_="row properties-grid content").find_all("div", class_="property_thumb"):
            external_link = "https://talbies.co.uk"+ech_prop.find("a")["href"]

            if ech_prop.find("div", class_="property_badge"):
                if "let" in ech_prop.find("div", class_="property_badge").text.lower() or "withdrawn" in ech_prop.find("div", class_="property_badge").text.lower():
                    pass
                else:
                    yield scrapy.Request(url = external_link, headers = self.header, callback = self.get_property_details, meta = {"external_link":external_link,'dont_redirect': True})
            else:
                yield scrapy.Request(url = external_link, headers = self.header, callback = self.get_property_details, meta = {"external_link":external_link,'dont_redirect': True})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print(response.url)

        item["external_link"] = response.url

        for ech_h5 in soup.find("div", class_="ch_col_6").find_all("h5"):
            if "£" in ech_h5.text:
                item["rent"] = getPrice(ech_h5.text.strip())
            else:
                address = ech_h5.text.strip()
                item["address"] = address

        if "," in address:
            if len(address.split(",")[-1].strip()) <= 3:
                
                zipcode = address.split(",")[-1].strip()
                item["zipcode"] = zipcode
                city = address.split(",")[-2].strip()
        
            else:
                temp_city_zip = address.split(",")[-1].split(" ")
                if len(temp_city_zip[-1]) <= 3 and num_there(temp_city_zip[-1]):
                    
                    zipcode = temp_city_zip[-1]
                    item["zipcode"] = zipcode
                    city = address.split(",")[-1].replace(zipcode,"").strip()
                else:
                    city = address.split(",")[-1].strip()
        else:
            temp_city_zip = address.split(" ")
            if len(temp_city_zip[-1]) <= 3 and num_there(temp_city_zip[-1]):
                
                zipcode = temp_city_zip[-1]
                item["zipcode"] = zipcode
                city = address.replace(zipcode,"").strip()
            else:
                city = address
        item["city"] = city

        for ech_li in soup.find("ul", class_="featuresul").find_all("li"):
            if "Property Type" in ech_li.find("div", class_="feature-info").text.strip():
                temp_prop_type = ech_li.find("div", class_="feature-info").text.strip().split(":")[-1].lower().strip()
                if "Room".lower() in temp_prop_type:
                    property_type = "room"
                elif "Studio".lower() in temp_prop_type:
                    property_type = "studio"
                elif "Flat".lower() in temp_prop_type:
                    property_type = "apartment"
                elif "Maisonette".lower() in temp_prop_type or "Semi Detached".lower() in temp_prop_type:
                    property_type = "house"
                item["property_type"] = property_type
            
            if "Bathroom".lower() in ech_li.find("div", class_="feature-info").text.strip().lower():
                item["bathroom_count"] = getSqureMtr(ech_li.find("div", class_="feature-info").text.strip())
            
            if "Bedroom".lower() in ech_li.find("div", class_="feature-info").text.strip().lower():
                item["room_count"] = getSqureMtr(ech_li.find("div", class_="feature-info").text.strip())

            if "Furnishing" in ech_li.find("div", class_="feature-info").text.strip() and "Furnished" in ech_li.find("div", class_="feature-info").text.strip():
                item["furnished"] = True

            if "Pets" in ech_li.find("div", class_="feature-info").text.strip():
                item["pets_allowed"] = True

            if "Parking" in ech_li.find("div", class_="feature-info").text.strip():
                item["parking"] = True

            if "Washing" in ech_li.find("div", class_="feature-info").text.strip():
                item["washing_machine"] = True

        for ech_template in soup.find_all("div", class_="template1_available_date"):

            if "Reference" in ech_template.text:
                item["external_id"] = ech_template.text.split(":")[-1].strip()

        item["title"] = soup.find("div", class_="ch_detail_heading").text.strip()

        desc = soup.find("div", class_="ch_detail_content").text.strip()
        item["description"] = desc

        if ("terras" in desc.lower() or "terrace" in desc.lower()) and "end of terrace" not in desc.lower() and "terrace house" not in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        floor_image_list = []
        if soup.find("div", class_="ch_detail_back ch_floor_plan"):
            floor_image_list.append(soup.find("div", class_="ch_detail_back ch_floor_plan").find("img")["src"])
        if floor_image_list:
            item["floor_plan_images"] = floor_image_list

        image_list = []
        for ech_img in soup.find("div",id="property_gallery").find_all("a"):
            image_list.append(ech_img["href"])
        if image_list:
            item["images"] = image_list
        
        if image_list or floor_image_list:
            item["external_images_count"] = len(image_list)+len(floor_image_list)

        extract_lat = re.findall("var mymap_lat=(.+);",str(soup))
        extract_lon = re.findall("var mymap_lng=(.+);",str(soup))
        if extract_lat and extract_lon:
            item["latitude"] = extract_lat[0]
            item["longitude"] = extract_lon[0]

        item["external_source"] = "Talbies_Co_PySpider_united_kingdom"
        item["currency"] = "GBP"
        item["landlord_phone"] = "020 3397 2474"
        item["landlord_email"] = "justask@talbies.co.uk"

        print(item)
        yield item

