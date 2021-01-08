# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import time
from word2number import w2n


def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
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

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    return date


class laforet(scrapy.Spider):
    name = 'newtonfallowell_co_uk_PySpider_uk_en'
    allowed_domains = ['www.newtonfallowell.co.uk']
    start_urls = ['www.newtonfallowell.co.uk']
    execution_type = 'testing'
    country = 'uk'
    locale ='en'


    def start_requests(self):
        url = "https://www.newtonfallowell.co.uk/properties/lettings/"
        yield scrapy.Request(
            url = url,
            callback=self.parse
            )

    def parse(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        count = int(soup.find("ul", class_="pagination").find("select").find_all("option")[-1].text)

        for c in range(count):
            if c == 0:
                url = "https://www.newtonfallowell.co.uk/properties/lettings/"
            else:
                url = "https://www.newtonfallowell.co.uk/properties/lettings/?pg={}&drawMap=".format(str(c+1))

            yield scrapy.Request(
                url = url,
                callback=self.get_page_details
                )


    def get_page_details(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        
        all_prop = soup.find_all("a", class_="text-link no-underline")
        for ech_prop in all_prop:
            external_link = ech_prop["href"]

            yield scrapy.Request(
                url = external_link,
                callback=self.get_property_details
                )

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print (response.url)

        rent = getPrice(soup.find("section",class_="background-default property-header").find("div",class_="property-price-availability flex-grow-1").find("span",class_="amount").text)
        if rent:
            item["rent"] = rent*4

        if soup.find("section",class_="background-default property-header").find("div",class_="property-meta").find("span",title="Bedrooms"):
            room = soup.find("section",class_="background-default property-header").find("div",class_="property-meta").find("span",title="Bedrooms").find("span").text
            item["room_count"] = int(room)
        else:
            if soup.find("div",id="property-features-accordion"):
                for o_r_m in soup.find("div",id="property-features-accordion").find("div",class_="accordion-content").find("ul").find_all("li"):
                    if "bedroom" in o_r_m.text.lower():
                        room = w2n.word_to_num(o_r_m.text.lower().split(" ")[0])
                        if room:
                            item["room_count"] = room
                    if "deposit" in o_r_m.text.lower() and getSqureMtr(o_r_m.text):
                        item["deposit"] = getSqureMtr(o_r_m.text)

        if soup.find("section",class_="background-default property-header").find("div",class_="property-meta").find("span",title="Bathrooms"):
            bathroom = soup.find("section",class_="background-default property-header").find("div",class_="property-meta").find("span",title="Bathrooms").find("span").text
            if int(bathroom):
                item["bathroom_count"] = int(bathroom)

        if soup.find("div", id="property-overview"):
            overview = soup.find("div", id="property-overview").find("div",class_="accordion-content").find("ul").find_all("li")
            for ech_over in overview:
                if "deposit" in ech_over.text.lower():
                    deposit = getSqureMtr(ech_over.text)
                    if deposit:
                        item["deposit"] = deposit

                if (("unfurnished" or "un-furnished") not in ech_over.text.lower()) and "furnished" in ech_over.text.lower():
                    item["furnished"] = True

        if soup.find("div",id="property-features-accordion"):
            features = soup.find("div",id="property-features-accordion").find("ul").find_all("li")
            for ech_ftr in features:
                if "deposit" in ech_ftr.text.lower():
                    deposit = getSqureMtr(ech_ftr.text)
                    if deposit:
                        item["deposit"] = deposit

                if (("unfurnished" or "un-furnished") not in ech_ftr.text.lower()) and "furnished" in ech_ftr.text.lower():
                    item["furnished"] = True


        desc = ""
        description = soup.find("div", id="property-description").find("div",class_="readmore").find_all("p")
        for des in description:
            desc = desc+des.text
        if soup.find("div", id="property-description").find("div",class_="readmore").find("div",class_="fees"):
            desc = desc.replace(soup.find("div", id="property-description").find("div",class_="readmore").find("div",class_="fees").text,"").strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = Tru
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True

        energy = soup.find_all("div",class_="icon-wrapper d-flex")
        for en in energy:
            if "EE" in en.find("div").text:
                energy_cur_pot = en.find("div").find("a")["href"]
                energy_cur = energy_cur_pot.split("_")[-2] 
                item["energy_label"] = energy_cur

        images_list = []
        imgs = soup.find("section",id="property-gallery").find_all("div",class_="slide-main-wrapper")
        for im in imgs:
            images_list.append(im.find("a")["href"])
        if images_list:
            item["images"]=images_list

        plan_images_list = []
        if soup.find("div",class_="floor-plans-container"):    
            plan_img = soup.find("div",class_="floor-plans-container").find_all("div",class_="floor-plan-wrapper")
            for p_im in plan_img:
                plan_images_list.append(p_im.find("a")["href"])
            if plan_images_list:
                item["floor_plan_images"] = plan_images_list

        if images_list or plan_images_list:
            item["external_images_count"] = len(images_list)+len(plan_images_list)

        if soup.find("div", class_="contact-name"):
            landlord_name = soup.find("div", class_="contact-name").find("strong").text.strip()
            item["landlord_name"] = landlord_name

        landlord_phone = soup.find("a",class_="contact-text-link")["href"].replace("tel:","")
        item["landlord_phone"] = landlord_phone

        lat = soup.find("div", id="property-map")["data-lat"]
        lon = soup.find("div", id="property-map")["data-lng"]

        item["latitude"] = lat
        item["longitude"] = lon

        title = soup.find("h1", class_="property-address").text.strip()
        city = title.split(",")[-2]
        zipcode = title.split(",")[-1]
        item["city"] = city
        item["zipcode"] = zipcode
        item["landlord_name"]="Newton Fallowell"
        item["address"] = title
        item["title"] = title
        item["external_link"] = response.url
        item["external_source"] = "newtonfallowell_co_uk_PySpider_uk_en"
        item["property_type"] = "apartment"
        item["currency"] = "GBP"
        # print (item)
        yield item
