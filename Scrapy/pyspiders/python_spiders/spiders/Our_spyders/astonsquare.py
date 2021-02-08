import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import math
import json


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
    name = 'Astonsquare_Co_PySpider_united_kingdom'
    allowed_domains = ['www.zoopla.co.uk']
    start_urls = ['www.zoopla.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        prop_types = ["flats","houses"]
        for p_t in prop_types:
            start_url = "https://www.zoopla.co.uk/to-rent/branch/aston-square-ltd-london-101758/?branch_id=101758&include_shared_accommodation=false&price_frequency=per_month&property_type={}&results_sort=newest_listings&search_source=refine".format(p_t)
            yield scrapy.Request(url = start_url, callback = self.parse1, meta = {"property_type":p_t})
    
    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")

        if num_there(soup.find("span", class_="listing-results-utils-count").text):
            total_props = int(soup.find("span", class_="listing-results-utils-count").text.split(" of ")[-1].strip())
            page_count = math.ceil(total_props/25)

            if page_count > 1:
                for ech_pg in range(1,page_count):
                    url = f"https://www.zoopla.co.uk/to-rent/branch/aston-square-ltd-london-101758/?branch_id=101758&include_retirement_homes=true&include_shared_accommodation=true&include_shared_ownership=true&new_homes=include&price_frequency=per_month&property_type={property_type}&results_sort=newest_listings&search_source=refine&pn={ech_pg+1}"
                    yield scrapy.Request(url = url, callback = self.parse2, meta = {"property_type":property_type})

        if soup.find("div", class_="status-wrapper"):
            for ech_prop in soup.find_all("div", class_="status-wrapper"):
                external_link = "https://www.zoopla.co.uk" + ech_prop.find("a", class_="photo-hover")["href"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        for ech_prop in soup.find_all("div", class_="status-wrapper"):
            external_link = "https://www.zoopla.co.uk" + ech_prop.find("a", class_="photo-hover")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body) 
        print(response.url)
        
        item["external_link"] = response.url

        if "flat" in response.meta.get("property_type"):
            property_type = "apartment"
        elif "house" in response.meta.get("property_type"):
            property_type = "house"
        item["property_type"] = property_type

        item["title"] = soup.find("h1", class_="ui-property-summary__title ui-title-subgroup").text

        address = soup.find("article", class_="dp-sidebar-wrapper__summary").find("h2", class_="ui-property-summary__address").text
        item["address"] = address

        item["zipcode"] = address.split(",")[-1].strip().split(" ")[1]

        item["city"] = address.split(",")[-1].strip().split(" ")[0]

        item["rent"] = getPrice(soup.find("article", class_="dp-sidebar-wrapper__summary").find("p", class_="ui-pricing__main-price ui-text-t4").text)

        for bed_bath in soup.find("ul", class_="dp-features-list dp-features-list--counts ui-list-icons").find_all("li"):
            if "bedroom" in bed_bath.find("span", class_="dp-features-list__text").text.lower():
                item["room_count"] = getSqureMtr(bed_bath.find("span", class_="dp-features-list__text").text)
            if "bathroom" in bed_bath.find("span", class_="dp-features-list__text").text.lower():
                item["bathroom_count"] = getSqureMtr(bed_bath.find("span", class_="dp-features-list__text").text)
            if "sq." in bed_bath.find("span", class_="dp-features-list__text").text.lower():
                item["square_meters"] = int(0.092903 * getSqureMtr(bed_bath.find("span", class_="dp-features-list__text").text))

        desc = soup.find("div", class_="dp-description__text").text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terrace house" in desc.lower() or "end of terrace" in desc.lower() or "terraced house" in desc.lower():
            pass
        elif "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "unfurnished" in desc.lower():
            pass
        elif "furnished" in desc.lower() or "furnishing" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        for ech_feat in soup.find("ul", class_="dp-features-list ui-list-icons").find_all("li", class_="dp-features-list__item"):
            
            if "Furnished" in ech_feat.find("span", class_="dp-features-list__text").text and "unfurnished" in ech_feat.find("span", class_="dp-features-list__text").text:
                item["furnished"] = True
            elif "Unfurnished" in ech_feat.find("span", class_="dp-features-list__text").text:
                item["furnished"] = False
            elif "Furnished" in ech_feat.find("span", class_="dp-features-list__text").text:
                item["furnished"] = True

        extract_data = re.findall('"coordinates": {(.+)},',str(soup))
        lat_lon = extract_data[0].split(",")
        item["latitude"] = lat_lon[-2].split(":")[-1].strip()
        item["longitude"] = lat_lon[-1].split(":")[-1].strip()

        images = []
        extract_data = re.findall('"contentUrl": "(.+)"',str(soup))
        for ech_img in extract_data:
            if ".jpg" in ech_img:
                images.append(ech_img)
        if images:
            item["images"] = images
            item["external_images_count"] = len(images)

        item["landlord_name"] = soup.find("h4", class_="ui-agent__name").text
        item["landlord_phone"] = soup.find("p", class_="ui-agent__tel ui-agent__text").find("a", class_="ui-link")["href"].replace("tel:","")
        item["external_source"] = auditaSpider.name
        item["currency"] = "GBP"

        print(item)
        yield item

