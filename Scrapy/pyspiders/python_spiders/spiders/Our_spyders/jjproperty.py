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

class auditaSpider(scrapy.Spider):
    name = 'Jjproperty_Services_Co_PySpider_united_kingdom'
    allowed_domains = ['www.jjproperty-services.co.uk']
    start_urls = ['www.jjproperty-services.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        property_types = ["flats","houses"]
        for p_t in property_types:
            start_url = f'https://www.jjproperty-services.co.uk/properties-search/?address=&type={p_t}&min-price=&max-price=&bedrooms=&bathrooms=&status=sale&submit=Search'
            yield scrapy.Request(url = start_url, callback = self.parse1, meta = {"property_type":p_t})

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        property_type = response.meta.get("property_type")
        tot_prop = getSqureMtr(soup.find("h3", class_="heading results").text)
        page_count = math.ceil(tot_prop/6)
        for ech_prop in soup.find_all("div", class_="title-and-meta col-sm-8"):
            external_link = ech_prop.find("a", class_="btn-default visible-md-inline-block")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link, "property_type":property_type})
        
        if page_count > 1:
            for ech_pg in range(1,page_count):
                url = f"https://www.jjproperty-services.co.uk/properties-search/page/{ech_pg+1}/?address&type={property_type}&min-price&max-price&bedrooms&bathrooms&status=sale&submit=Search"
                yield scrapy.Request(url = url, callback = self.parse2, meta = {"property_type":property_type})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        property_type = response.meta.get("property_type")
        for ech_prop in soup.find_all("div", class_="title-and-meta col-sm-8"):
            external_link = ech_prop.find("a", class_="btn-default visible-md-inline-block")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"external_link":external_link, "property_type":property_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
    
        item["external_link"] = response.meta.get("external_link")
        print(response.meta.get("external_link"))
        
        if "flats" in response.meta.get("property_type"):
            property_type = "Apartment"
        elif "houses" in response.meta.get("property_type"):
            property_type = "House"
        item["property_type"] = property_type

        title = soup.find("h1", class_="entry-title single-property-title").text.strip()
        item["title"] = title

        if "(" in title:
            temp_zip = title.split("(")[0]
        else:
            temp_zip = title
        if "," in temp_zip:
            if num_there(temp_zip.split(",")[-1]):
                item["zipcode"] = temp_zip.split(",")[-1].strip()

        item["address"] = soup.find("h1", class_="entry-title single-property-title").text.strip()
        
        if ("let" in title.lower() and "(" in title) or ("APPLICATION".lower() in title.lower() and "RECEIVED".lower() in title.lower() and "(" in title):
            pass
        else:
            item["rent"] = 4*getPrice(soup.find("span", class_="single-property-price price").text)

            for ech_wrapper in soup.find("div", class_="single-property-wrapper").find_all("div", class_="meta-inner-wrapper"):
                if "bedroom" in ech_wrapper.find("span", class_="meta-item-label").text.lower():
                    item["room_count"] = int(ech_wrapper.find("span", class_="meta-item-value").text)

                if "bathroom" in ech_wrapper.find("span", class_="meta-item-label").text.lower():
                    item["bathroom_count"] = int(ech_wrapper.find("span", class_="meta-item-value").text)

                if "status" in ech_wrapper.find("span", class_="meta-item-label").text.lower():
                    if "rent" in ech_wrapper.find("span", class_="meta-item-value").text.lower():
                        
                        desc = soup.find("div", class_="property-content").text.strip()
                        item["description"] = desc

                        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
                            item["parking"] = True
                        if ("terras" in desc.lower() or "terrace" in desc.lower()) and "end of terrace" not in desc.lower() and "terrace house" not in desc.lower():
                            item["terrace"] = True
                        if "balcon" in desc.lower() or "balcony" in desc.lower():
                            item["balcony"] = True
                        if "zwembad" in desc.lower() or "swimming" in desc.lower():
                            item["swimming_pool"] = True
                        if "furnished" in desc.lower() or "furniture" in desc.lower(): 
                            item["furnished"] = True
                        if "machine à laver" in desc.lower() or"washing" in desc.lower():
                            item["washing_machine"] = True
                        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
                            item["dishwasher"] = True
                        if "lift" in desc.lower() or "elevator" in desc.lower():
                            item["elevator"] = True

                        image_list = []
                        for ech_img in soup.find("ul", id="image-gallery").find_all("li"):
                            image_list.append(ech_img.find("img")["src"])
                        if image_list:
                            item["images"] = image_list
                            item["external_images_count"] = len(image_list)

                        extract_data = re.findall("var propertyMarkerInfo = {(.+)}",str(soup))
                        if "lat" in extract_data[0].split(",")[0]:
                            item["latitude"] = extract_data[0].split(",")[0].split(":")[-1].replace('"','')
                        if "lang" in extract_data[0].split(",")[1]:
                            item["longitude"] = extract_data[0].split(",")[1].split(":")[-1].replace('"','')

                        item["currency"] = "GBP"
                        item["external_source"] = "Jjproperty_Services_Co_PySpider_united_kingdom"
                        item["landlord_name"] = "JJ Property Letting Services"
                        item["landlord_phone"] = "(01253) 291 654"
                        item["landlord_email"] = "info@jjproperty-services.co.uk"

                        print(item)
                        yield item


