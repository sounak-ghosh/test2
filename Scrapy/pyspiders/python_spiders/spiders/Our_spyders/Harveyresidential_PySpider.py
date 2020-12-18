import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

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


class harveyResidental(scrapy.Spider):
    name = 'Harveyresidential_PySpider_united_kingdom'
    allowed_domains = ['harveyresidential.com']
    start_urls = ['harveyresidential.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_urls = ["http://harveyresidential.com/?s&post_type=listing&lookingto=rent"]

        for url in start_urls:
            yield scrapy.Request(
                url = url,
                callback = self.parse
                ) 

    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        linked = soup.find("div", class_="archive-pagination pagination").find("ul").find_all("li")
        tot_page = int(linked[-2].text)

        for x in range(1,tot_page + 1):
            url = "http://harveyresidential.com/page/" + str(x) + "/?s&post_type=listing&lookingto=rent"
            yield scrapy.Request(url = url, callback = self.get_pageDetails) 


    def get_pageDetails(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        link_ = soup.find("main", class_="content").find_all("a", class_="more-link")

        for i in link_:
            link_in = i["href"]
            yield scrapy.Request(url=link_in, callback = self.get_property_details)

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
      
        print (response.url)

        item["external_link"] = response.url
        item["external_source"] = "Harveyresidential_PySpider_united_kingdom"
        item["landlord_name"] = "London Hackney"
        item["landlord_phone"] = "0207 249 1110"
        item["property_type"] = "apartment"
        item["currency"] = "GBP"



        title = (soup.find("header", class_="entry-header"))
        item["title"] = title.text.strip()
        description = (soup.find("div", class_="entry-content").find_all("p"))
        desc = ""
        for x in description:
            desc = desc + " " + x.text
        item["description"] = desc.strip()


        if "terrace" in desc.lower():
            item["terrace"] = True
        if "swimming" in desc.lower():
            item["swimming_pool"] = True
        if "furnish" in desc.lower():
            item["furnished"]=True
        if "parking" in desc.lower():
            item["parking"] = True
        if "balcony" in desc.lower():
            item["balcony"]=True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"]=True


        detail = (str(soup.find("div", class_="property-details")).replace("<br/>","$$"))
        soup2 = BeautifulSoup(detail,"html.parser")

        deat1=soup2.find("div", class_="property-details-col1 one-half first")
        tmp_dic = {}
        if deat1!=None:
            var = deat1.text.split("$$")
            for a in var:
                data = (a.split(":"))
                if len(data) > 1:
                    tmp_dic[data[0]] = data[1]

        deat2=soup2.find("div", class_="property-details-col2 one-half")
        if deat2!=None:
            var = deat2.text.split("$$")
            for a in var:
                data = (a.split(":"))
                if len(data) > 1:
                    tmp_dic[data[0]] = data[1]

        tmp_dic = cleanKey(tmp_dic)

        if "price" in tmp_dic and num_there(tmp_dic["price"]):
            if "pw" in tmp_dic["price"]:
                item["rent"] = getPrice(tmp_dic["price"])*4
            if "pm"  in tmp_dic["price"]:
                item["rent"] = getPrice(tmp_dic["price"])


        if "address" in tmp_dic:
            item["address"] = tmp_dic["address"].strip()

        if "city" in tmp_dic and tmp_dic["city"].strip():
            item["city"] = tmp_dic["city"].strip()

        if "postcode" in tmp_dic:
            item["zipcode"] = tmp_dic["postcode"].strip()

        if "squarefeet" in tmp_dic and num_there(tmp_dic["squarefeet"]):
            item["square_meters"] = getSqureMtr(tmp_dic["squarefeet"])

        if "bedrooms" in tmp_dic and num_there(tmp_dic["bedrooms"]):
            item["room_count"] = int(tmp_dic["bedrooms"])

        if "bathrooms" in tmp_dic and num_there(tmp_dic["bathrooms"]):
            item["bathroom_count"] = int(tmp_dic["bathrooms"])

        if "basement" in tmp_dic and "no" not in tmp_dic["basement"].lower() and tmp_dic["basement"].strip():
            item["floor"] = tmp_dic["basement"].strip()

        image = (soup.find("div", class_ ="entry-content").find_all("img"))
        list_img = []
        for y in image:
            img = y["src"] 
            img_url = img
            list_img.append(img_url)
        if list_img:
            item["images"] = list_img
            item["external_images_count"] = len(list_img)

        print (item)
        yield item