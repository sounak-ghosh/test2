import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests
import geopy
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="myGeocoder")

def get_lat_lon(_address):
    location = geolocator.geocode(_address)
    return location.latitude,location.longitude


def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

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


class QuotesSpider(scrapy.Spider):
    name = 'alanfrancis_co_uk_PySpider_unitedkingdom_en'
    allowed_domains = ['www.alanfrancis.co.uk']
    start_urls = ['www.alanfrancis.co.uk']
    execution_type = 'testing'
    country = 'unitedkingdom'
    locale ='en'

    def start_requests(self):
        url="https://www.alanfrancis.co.uk/property-search/?department=residential-lettings&address_keyword=&radius=&minimum_price=&maximum_price=&minimum_rent=&maximum_rent="

        yield scrapy.Request(
            url=url,
            callback=self.parse
            )


    def parse(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")


        if soup.find("div", class_="propertyhive-pagination"):
            all_pages = soup.find("div", class_="propertyhive-pagination").find("ul").find_all("li")
            if num_there(all_pages[-1].text):
                count = all_pages[-1].text
            elif num_there(all_pages[-2].text):
                count = all_pages[-2].text
            count = int(count)
            print(count)
            for c in range(count):
                if c == 0:
                    url = "https://www.alanfrancis.co.uk/property-search/?department=residential-lettings&address_keyword=&radius=&minimum_price=&maximum_price=&minimum_rent=&maximum_rent="
                else: 
                    url = "https://www.alanfrancis.co.uk/property-search/page/{}/?department=residential-lettings&address_keyword&radius&minimum_price&maximum_price&minimum_rent&maximum_rent".format(str(c+1))
                    
                yield scrapy.Request(
                    url=url,
                    callback=self.get_page_details
                    )
       
    def get_page_details(self, response, **kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        all_prop = soup.find("ul", class_="properties clear grid-view").find_all("li")
        for ech_prop in all_prop:
            external_link = ech_prop.find("div", class_="thumbnail").find("a")["href"]
            print(external_link)
            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details
                )


    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        str_soup = str(soup)
        print (response.url)

        title = soup.find("title").text.strip()
        item["title"] = title

        match = re.findall("var myLatlng = new google.maps.LatLng(.+);",str_soup)
        if match:
            lat_lon = (eval(match[0]))
            latitude = str(lat_lon[0])
            longitude = str(lat_lon[1])
            location = getAddress(latitude,longitude)
            address = location.address
            item["address"] = address
            item["latitude"] = latitude
            item["longitude"] = longitude

            if "city" in location.raw["address"]:
                item["city"] = location.raw["address"]["city"]
            if "town" in location.raw["address"]:
                item["city"] = location.raw["address"]["town"]
            if "village" in location.raw["address"]:
                item["city"] = location.raw["address"]["village"]
            if "postcode" in location.raw["address"]:
                item["zipcode"] = location.raw["address"]["postcode"]

        title = soup.find("h1", class_="property_title entry-title").find("span").text.strip()
        item["title"] = title

        rent = getPrice(soup.find("div",class_="price").text.strip())
        item["rent"] = rent

        image_list = []
        if soup.find("div", class_="images").find("ul"):
            imgs = soup.find("div", class_="images").find("ul").find_all("li")
            for im in imgs:
                image_list.append(im.find("img")["src"])
            if image_list:
                item["images"] = image_list

        if soup.find("div", class_="rooms").find("div", class_="room bedrooms"):
            rooms = soup.find("div", class_="rooms").find("div", class_="room bedrooms").text.strip()
            item["room_count"] = int(rooms)

        bathroom = soup.find("div", class_="rooms").find("div", class_="room bathrooms").text.strip()
        item["bathroom_count"] = int(bathroom)

        desc = soup.find("div", id="description").find_all("p")[0].text.strip()
        item["description"] = desc

        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = True
        if ("gemeubileerd" in desc.lower() or "furnished" in desc.lower() or "meublé" in desc.lower()) and "unfurnished" not in desc.lower():
            item["furnished"] = True
        if "machine à laver" in desc.lower() or ("washing" in desc.lower() and "machine" in desc.lower()):
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.lower():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "ascenseur" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True



        features = soup.find("div", class_="features").text.strip()
        floor_plan_list = []
        if soup.find("div", id="floorplans"):
            plan_imgs = soup.find("div", id="floorplans").find_all("a")
            for p_im in plan_imgs:
                floor_plan_list.append(p_im["href"])
            if floor_plan_list:
                item["floor_plan_images"] = floor_plan_list

        if floor_plan_list or image_list:
            item["external_images_count"] = len(floor_plan_list)+len(image_list)

        item["external_source"] = "alanfrancis_co_uk_PySpider_unitedkingdom_en"
        item["landlord_name"] = "Alan Francis Estate Agents"
        item["landlord_phone"] = "01908 675 747"
        item["landlord_email"] = "lettings@alanfrancis.co.uk"
        item["currency"] = "GBP"
        item["property_type"] = "apartment"
        item["external_link"] = response.url

        print(item)
        yield item
