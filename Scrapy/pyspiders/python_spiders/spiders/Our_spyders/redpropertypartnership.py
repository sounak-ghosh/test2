# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
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
    name = 'Redpropertypartnership_Co_PySpider_united_kingdom'
    allowed_domains = ['redpropertypartnership.co.uk']
    start_urls = ['redpropertypartnership.co.uk']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'
    
    def start_requests(self):
        data = {"radius": "3", "location": "", "area": "To Rent"}
        start_url = 'https://redpropertypartnership.co.uk/property-search/'
        yield scrapy.FormRequest(url = start_url, callback = self.parse1, method = "POST", formdata = data)

    def parse1(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        page_count = int(soup.find("div", class_ = "properties-paging").text.split(" of ")[-1])
        print(page_count)
        
        for ech_prop in soup.find_all("section", class_="listingResult clearfix To_Let"):
            external_link = ech_prop.find("a", class_ = "clearfix")["href"]
            yield scrapy.Request(url = external_link, callback = self.get_property_details)
        

    def get_property_details(self,response,**kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print(response.url)
        item["external_link"] = response.url
        
        item["title"] = soup.find("div", class_="span6 propertyHeader").find("h1").text.strip()

        address = soup.find("div", class_="span6 propertyHeader").find("h1").text.strip()
        item["address"] = address

        city_zip = address.split(",")
        item["zipcode"] = city_zip[-1].strip()
        item["city"] = city_zip[-2].strip()

        temp_dic = {}
        for ech_detail in soup.find("div", class_="span4 table right hidemobile").find_all("tr"):
            temp_dic[ech_detail.find("td").text.strip()] = ech_detail.find("td", class_="alignright").text.strip()
        temp_dic = cleanKey(temp_dic)
        # {'price': '£1,620 pw', 'location': 'Baker Street', 'propetytype': 'Flat', 'bedrooms': '2', 'bathrooms': '2', 'receptionrooms': '1'}
        if "price" in temp_dic:
            if "pw" in temp_dic["price"]:
                rent = 4*getPrice(temp_dic["price"])
            elif "pcm" in temp_dic["price"]:
                rent = getPrice(temp_dic["price"])
            item["rent"] = rent
        if "propetytype" in temp_dic:
            if "apartment" in temp_dic["propetytype"].lower() or "flat" in temp_dic["propetytype"].lower():
                property_type = "apartment"
            elif "house" in temp_dic["propetytype"].lower():
                property_type = "house"
            item["property_type"] = property_type
        if "bedrooms" in temp_dic:
            item["room_count"] = int(temp_dic["bedrooms"])
        if "bathrooms" in temp_dic:
            item["bathroom_count"] = int(temp_dic["bathrooms"])

        floor_image_list = []
        if soup.find("div", class_="span12 clear floorplansShow"):
            if "http://red.ultidev.co.uk/wp-content/uploads/2014/11/placeholder-nofloorplan.jpg" in soup.find("div", class_="span12 clear floorplansShow").find("img")["src"]:
                pass
            else:
                floor_image_list.append(soup.find("div", class_="span12 clear floorplansShow").find("img")["src"])
        if floor_image_list:
            item["floor_plan_images"] = floor_image_list

        image_list = []
        for ech_img in soup.find("ul", class_="slides").find_all("li"):
            image_list.append(ech_img.find("div")["style"].split(": ")[-1].replace("url(","").replace(")",""))
        if image_list:
            item["images"] = image_list

        if image_list or floor_image_list:
            item["external_images_count"] = len(image_list) + len(floor_image_list)

        desc = soup.find("div", class_="span8 clearfix").find("p").text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terrace house" in desc.lower() or "end of terrace" in desc.lower() or "terraced house" in desc.lower() or "wrap-around terrace" in desc.lower():# wrap-around terrace mai terrace nahi hai phir bhi pass nahi ho raha hai, terrace:true aa raha hai
            pass
        elif "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "unfurnished" in desc.lower():
            pass
        elif "furnished" in desc.lower() or "furniture" in desc.lower(): 
            item["furnished"] = True
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        extract_data = re.findall('var myLatlng = new google.maps.LatLng(.+);',str(soup))
        lat_lon = extract_data[0].replace("(","").replace(")","").split(",")
        item["latitude"] = lat_lon[0].strip()
        item["longitude"] = lat_lon[1].strip()

        item["landlord_email"] = "info@redpropertypartnership.co.uk"
        item["landlord_phone"] = "0207 485 1332"
        item["landlord_name"] = "RED Property Partnership Ltd."
        item["currency"] = "GBP"
        item["external_source"] = "Redpropertypartnership_Co_PySpider_united_kingdom"

        print(item)
        yield item

