#filepath=>>>> /Scrapy/pyspiders/python_spiders/spiders/filename.py
# Author: Sounak Ghosh
import scrapy
import js2xml
import re
from bs4 import BeautifulSoup
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)


def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if "." in text:
        if len(list_text) > 0:
            output = int(list_text[0])
        else:
            output=0
        return output
    elif "," in text:
        if len(list_text) > 1:
            output = int(list_text[0]+list_text[1])
        else:
            output=0
        return output
    else:
        if len(list_text) > 0:
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

class QuotesSpider(scrapy.Spider):
    name = "finders_co_uk_PySpider_united_kingdom_en"
    allowed_domains = ['www.finders.co.uk']
    start_urls = ['www.finders.co.uk']
    execution_type = 'testing'
    country = 'United Kingdom'
    locale ='en'


    def start_requests(self):

        start_url ="https://www.finders.co.uk/search/oxfordshire#"

        yield scrapy.Request(
            url=start_url,
            callback=self.parse,
            )


    def parse(self, response):
        dic = {}

        soup = BeautifulSoup(response.body,"html.parser")

        divs = soup.find("div",id="search_results")
        list_property = divs.find_all("div",class_="property")

        for index,items in enumerate(list_property):
            title_tag = items.find("p",class_ = "propertytitle none")
            if title_tag:
                dic["title"] = title_tag.text.strip()
                dic["address"] = dic["title"].replace(dic["title"].split("-")[0],"").strip()
            
            price = items.find("strong").text
            dic["rent"] = getPrice(price)

            ul_detaiils = items.find("ul",class_ = "details none").find_all("li")

            temp_dic = {}
            for each_li in ul_detaiils:
                split_txt = each_li.text.split(":")
                temp_dic[split_txt[0].strip()]= split_txt[1].strip()


            temp_dic = cleanKey(temp_dic)
            # print(temp_dic)
            if "propertytype" in temp_dic:
                if temp_dic["propertytype"] == "house":
                    dic["property_type"] = temp_dic["propertytype"].lower().strip()
                else:
                    dic["property_type"] = "apartment"
            if "ref" in temp_dic:
                dic["external_id"] = temp_dic["ref"]
            if "availabledate" in temp_dic and num_there(temp_dic["availabledate"]):
                dic["available_date"] = format_date(temp_dic["availabledate"])
            elif "availabledate" in temp_dic:
                dic["available_date"] = "immediately"


            if "furnishing" in temp_dic and "unfurnished" in temp_dic["furnishing"].lower():
                dic["furnished"] = False
            elif "furnishing" in temp_dic and "furnished" in (temp_dic["furnishing"].lower()  or "flexible" in temp_dic["furnishing"].lower()):
                dic["furnished"] = True

            if "bedrooms" in temp_dic and num_there(temp_dic["bedrooms"]):
                dic["room_count"] = int(temp_dic["bedrooms"])


            ###################################### Add Landlord Details###################################################
            
            text_url = items.find("a")["href"]
            external_link = "https://www.finders.co.uk/" + text_url
            dic["external_link"] = external_link

            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details,
                meta = dic
                )
            
    def get_property_details(self,response,**kwargs):
        item = ListingItem()

        soup = BeautifulSoup(response.body,"html.parser")

        for  key,value in response.meta.items():
            try:
                item[key] = value
            except:
                pass

        dtls = soup.find("p",class_="location_details_introduction_full").text

        if soup.find("input",id="maplat"):
            item["latitude"] = soup.find("input",id="maplat")["value"]
        if soup.find("input",id="maplng"):
            item["longitude"] = soup.find("input",id="maplng")["value"]

        item["description"] = dtls
        item["currency"] = "GBP"
        item["landlord_phone"] = "01865 311011"
        item["landlord_name"] = "Finders Keepers"
        item["external_source"] = "finders_co_uk_PySpider_unitedkingdom_en"
        pic = soup.find("div",class_="image_block fleft")
        picture = pic.find_all("div",class_="item")
        list_img = []
        for items in picture:
            image_link = "https://www.finders.co.uk" + items.find("img")["src"]
            list_img.append(image_link)
        if list_img:
            item["images"] = list_img

        floor_plan = []
        fp = soup.find("ul",class_="options none")
        flr_link = "https://www.finders.co.uk/" + fp.find("a")["href"]
        floor_plan.append(flr_link)


        if list_img or floor_plan:
            item["external_images_count"] = len(list_img)+len(floor_plan)

        print (item)
        yield item
