import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
from datetime import datetime
import math

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
    name = 'Propertystoplsm_PySpider_united_kingdom'
    allowed_domains = ['propertystoplsm.com']
    start_urls = ['propertystoplsm.com']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'
    
    def start_requests(self):
        prop_types = ["apartment", "flat", "house", "studio", "house-share"]
        for p_t in prop_types:
            start_url = f'https://propertystoplsm.com/properties-search/?status=for-rent&type={p_t}'
            yield scrapy.Request(url = start_url, callback = self.parse1, meta = {"property_type" : p_t})

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        if soup.find("figure", class_="rh_prop_card__thumbnail"):
            tot_prop = int(soup.find("h2", class_="rh_page__title").find("span", class_="sub").text)
            page_count = math.ceil(tot_prop/6)
            for ech_prop in soup.find_all("figure", class_="rh_prop_card__thumbnail"):
                external_link = ech_prop.find("a")["href"]
                yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

            for ech_pg in range(1,page_count):
                url = f"https://propertystoplsm.com/properties-search/page/{ech_pg+1}/?status=for-rent&type={property_type}"
                yield scrapy.Request(url = url, callback = self.parse2, meta = {"property_type" : property_type})

    def parse2(self, response, **kwargs):
        soup = BeautifulSoup(response.body)
        property_type = response.meta.get("property_type")
        for ech_prop in soup.find_all("figure", class_="rh_prop_card__thumbnail"):
            external_link = ech_prop.find("a")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details, meta = {"property_type" : property_type})

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body)
        print(response.url)

        item["external_link"] = response.url
        
        temp_prop_type = response.meta.get("property_type")
        if "apartment" in temp_prop_type or "flat" in temp_prop_type:
            property_type = "apartment"
        elif "house" in temp_prop_type:
            property_type = "house"
        elif "studio" in temp_prop_type:
            property_type = "studio"
        elif "house-share" in temp_prop_type:
            property_type = "room"
        item["property_type"] = property_type

        if "pcm" in soup.find("h1", class_="rh_page__title").text.lower():
            for index,finding_rent in enumerate(soup.find("h1", class_="rh_page__title").text.strip().split(" ")):
                if "£" in finding_rent and "pcm" in soup.find("h1", class_="rh_page__title").text.strip().split(" ")[index+1].lower():
                    rent = getPrice(finding_rent)
        elif "pppw" in soup.find("h1", class_="rh_page__title").text.lower():
            for finding_rent in soup.find("h1", class_="rh_page__title").text.strip().split(" "):
                if "£" in finding_rent:
                    rent = 4*getPrice(finding_rent)
        item["rent"] = rent

        item["title"] = soup.find("h1", class_="rh_page__title").text.strip()

        if soup.find("p", class_="rh_page__property_address").text.strip():     #problem in extracting address
            address = soup.find("p", class_="rh_page__property_address").text.strip()
            item["address"] = address
            
            if "," in address:
                temp_city_zip = address.split(",")
                if "uk" in temp_city_zip[-1].lower():
                    temp_city_zip = temp_city_zip[:-1]
                if len(temp_city_zip[-1].strip()) <= 3 and num_there(temp_city_zip[-1]):
                    zipcode = temp_city_zip[-1].strip()
                    item["zipcode"] = (zipcode)
                    city = temp_city_zip[-2].strip()
                    item["city"] = city
                elif len(temp_city_zip[-1].strip()) <= 7 and num_there(temp_city_zip[-1]):
                    zipcode = temp_city_zip[-1].strip()
                    item["zipcode"] = zipcode
                    city = temp_city_zip[-2].strip()
                    item["city"] = city
                elif len(temp_city_zip[-1].strip()) >=7 and num_there(temp_city_zip[-1]):
                    city_zip = temp_city_zip[-1].strip().split(" ")
                    if len(city_zip[-2]) <=3 and num_there(city_zip[-2]):
                        zipcode = city_zip[-2] + " " + city_zip[-1]
                        item["zipcode"] = zipcode
                        city = temp_city_zip[-1].replace(zipcode,"").strip()
                        item["city"] = city
                    elif len(city_zip[-1]) <=3 and num_there(city_zip[-1]):
                        zipcode = city_zip[-1]
                        item["zipcode"] = zipcode
                        city = temp_city_zip[-1].replace(zipcode,"").strip()
                        item["city"] = city
                else:
                    city = temp_city_zip[-1].strip()
                    item["city"] = city
            else:
                
                temp_city_zip = address.split(" ")
                if len(temp_city_zip) > 2:
                    pass
                else:
                    if len(temp_city_zip[-2]) <=3 and num_there(temp_city_zip[-2]):
                        zipcode = temp_city_zip[-2]+" "+temp_city_zip[-1]
                        item["zipcode"] = zipcode
                    elif len(temp_city_zip[-1]) <=3 and num_there(temp_city_zip[-1]):
                        zipcode = temp_city_zip[-1]
                        item["zipcode"] = zipcode
                        city = address.replace(zipcode,"")
                        item["city"] = city           

        external_id = soup.find("div", class_="rh_property__id").find("p", class_="id").text.strip()
        item["external_id"] = external_id

        for bed_bath in soup.find("div", class_="rh_property__row rh_property__meta_wrap").find_all("div", class_="rh_property__meta"):
            if "bedroom" in bed_bath.find("h4").text.lower():
                room_count = bed_bath.find("span", class_="figure").text
                if "/" in room_count:
                    room_count = room_count.split("/")[-1]
                item["room_count"] = int(room_count)

            if "bathroom" in bed_bath.find("h4").text.lower():
                bathroom_count = bed_bath.find("span", class_="figure").text
                item["bathroom_count"] = int(bathroom_count)

        desc = soup.find("div", class_="rh_content").text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terrace house" in desc.lower() or "end of terrace" in desc.lower() or "terraced house" in desc.lower(): #terrace mai error aa raha hai
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

        if soup.find("div", class_="rh_property__features_wrap"):
            for ech_feat in soup.find("div", class_="rh_property__features_wrap").find_all("li"):
                if "furnished" in ech_feat.text.strip().lower():
                    item["furnished"] = True
        
        image_list = []
        if soup.find("ul", class_="slides"):
            for ech_img in soup.find("ul", class_="slides").find_all("li"):
                image_list.append(ech_img.find("a")["href"])
        elif soup.find("div", id="property-featured-image"):
            image_list.append(soup.find("div", id="property-featured-image").find("a")["href"])
        if image_list:
            item["images"] = image_list
            item["external_images_count"] = len(image_list)

        extract_data = re.findall('var propertyMapData = {(.+)};',str(soup))
        if extract_data:
            lat_lng = extract_data[0].split(",")
            for ech_item_ll in lat_lng:
                if '"lat"' in ech_item_ll:
                    item["latitude"] = ech_item_ll.split(":")[-1].replace('"','')
                if '"lng"' in ech_item_ll:
                    item["longitude"] = ech_item_ll.split(":")[-1].replace('"','')

        item["currency"] = "GBP"
        item["landlord_phone"] = "0191 209 2395"
        item["landlord_name"] = "Property Shop LSM ©"
        item["external_source"] = auditaSpider.name

        print(item)
        yield item
