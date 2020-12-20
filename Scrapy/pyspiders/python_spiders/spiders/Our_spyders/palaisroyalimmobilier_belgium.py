# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time
# from geopy.geocoders import Nominatim

# geolocator = Nominatim(user_agent="myGeocoder")

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


class laforet(scrapy.Spider):
    name = 'palaisroyalimmobilier_PySpider_belgium_fr'
    allowed_domains = ['www.palaisroyalimmobilier.com']
    start_urls = ['www.palaisroyalimmobilier.com']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'


    def start_requests(self):
        start_urls = [{"url":"https://www.palaisroyalimmobilier.com/offres-locations/appartement-vide","property_type":"apartment"},
        {"url":"https://www.palaisroyalimmobilier.com/offres-locations/appartement-meuble","property_type":"apartment"},
        {"url":"https://www.palaisroyalimmobilier.com/offres-locations/loft","property_type":"apartment"}]

        for urls in start_urls: 
            yield scrapy.Request(
                url = urls.get("url"),
                callback=self.parse,
                meta = {"property_type":urls.get("property_type")}
                )

    def parse(self,response,**kwargs):
        url = response.url
        soup = BeautifulSoup(response.body,"html.parser")
        page_sp = soup.find("div",class_="pages").find_all("a")

        if page_sp:
            if num_there(page_sp[-1].text):
                count=int(page_sp[-1].text)
            elif num_there(page_sp[-2].text):
                count=int(page_sp[-2].text)
            else:
                count=0
        else:
            count = int(soup.find("div",class_="pages").find("span",class_="page active").text)
        
        for c in range(count):
            if c ==0:
                pass
            else:
                url = url+"/"+str(c+1)

            yield scrapy.Request(
                url = url,
                callback=self.get_page_details
                )


    def get_page_details(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        articles = soup.find_all("div",class_="offreitem")

        for ech_art in articles:
            furnished = False
            if "appartement meublé" in ech_art.find("div",class_="h2").text.strip().lower():
                furnished = True
            
            external_link = ech_art.find("div",class_="photo").find("a")["href"]
            print(external_link)

            yield scrapy.Request(
                url = external_link,
                callback=self.get_property_details,
                meta = {"furnished":furnished}
                )



    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")

        print (response.url)

        if soup.find("div",itemprop="description"):
            description = soup.find("div",itemprop="description").text.strip()
            if "garage" in description.lower() or "parking" in description.lower() or "autostaanplaat" in description.lower():
                item["parking"]=True
            if "terras" in description.lower() or "terrace" in description.lower():
                item["terrace"]=True
            if "balcon" in description.lower() or "balcony" in description.lower():
                item["balcony"]=True
            if "zwembad" in description.lower() or "swimming" in description.lower():
                item["swimming_pool"]=True
            if "gemeubileerd" in description.lower() or "furnished" in description.lower():
                item["furnished"]=True
            if "machine à laver" in description.lower():
                item["washing_machine"]=True
            if "lave" in description.lower() and "vaisselle" in description.lower():
                item["dishwasher"]=True
            if "lift" in description.lower():
                item["elevator"]=True

        item["external_link"] = response.url
        item["property_type"] = "apartment"
        item["description"] = description
        title = soup.find("h1", class_="desc noprint").text.strip()
        item["title"] = title

        if response.meta["furnished"]:
            item["furnished"] = True


        images_list = []
        plan_img_list = []
        if soup.find("div",class_="photo"):
            images_list.append("https://www.palaisroyalimmobilier.com"+soup.find("div",class_="photo").find("a")["href"])
            imgs = soup.find("div", class_="gallery").find_all("td")
            for im in imgs:
                images_list.append("https://www.palaisroyalimmobilier.com"+im.find("a")["href"])
            if images_list:
                item["images"] = images_list


        if soup.find_all("div",class_="photo")[1].find("a"):
            plan_img_list.append("https://www.palaisroyalimmobilier.com"+soup.find_all("div",class_="photo")[1].find("a")["href"])
            if plan_img_list:
                item["floor_plan_images"] = plan_img_list

        if images_list or plan_img_list:
            item["external_images_count"] = len(images_list)+len(plan_img_list)


        header = soup.find("div", class_="col-sm-7").find_all("h2")
        for h in header:
            if "Surface" in h.text:
                area = getSqureMtr(soup.find("div", class_="col-sm-7").find("strong").text)#.split("+")[0])
                if area:
                    item["square_meters"] = area

            if "Situation" in h.text:
                address = soup.find("div",itemprop="location").text.strip()
                item["address"] = address

            if "Performance énergétique" in h.text:
                energy = soup.find("div", class_="energie").find("span").text
                if num_there(energy):
                    item["energy_label"]= energy+" kWhEP/m².an"

            if "Réf." in h.text:
                ext_id = soup.find("input",type="hidden")["value"]
                item["external_id"]=ext_id

            if "Conditions de location" in h.text:
                d_key = soup.find("dl").find_all("dt")
                d_val = soup.find("dl").find_all("dd")

                temp_dic = {}
                for index,value in enumerate(d_key):
                    temp_dic[d_key[index].text.replace(" : ","")] = d_val[index].text
                temp_dic = cleanKey(temp_dic)


                if "charges" in temp_dic:
                    utilities = getPrice(temp_dic["charges"].split("€")[0])
                    if utilities:
                        item["utilities"]=utilities

                if "totalloyer" in temp_dic:
                    rent = getPrice(temp_dic["totalloyer"])
                    if rent:
                        item["rent"] = rent

                if"disponibilit" in temp_dic:
                    if num_there(temp_dic["disponibilit"]):
                        date = format_date(temp_dic["disponibilit"].strip())
                        item["available_date"]=date

        item["currency"] = "EUR"
        item["external_source"] = "palaisroyalimmobilier.com"
        item["landlord_name"]='"A1" Palais - Royal immobilier'
        item["landlord_phone"]="0033(0).142.615.615"
        # print (item)
        yield item
