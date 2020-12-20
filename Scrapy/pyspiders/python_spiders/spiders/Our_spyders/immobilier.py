# Author: Sounak Ghosh
import scrapy
import re, json
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
# import geopy
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter
from scrapy.http import FormRequest

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output

class QuotesSpider(scrapy.Spider):
    name = "immobilier_PySpider_france_fr"
    allowed_domains = ['www.lg-immobilier.fr']
    start_urls = ['www.lg-immobilier.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        url = "http://www.lg-immobilier.fr/location/biens"

        yield scrapy.Request(
            url=url,
            callback=self.sub_request)

    def sub_request(self, response):
        bsoup = BeautifulSoup(response.body)
        imax = int(re.findall('\d+',bsoup.find("div", id="selection").find("span", id="nb-res").text)[0])

        i = 0
        while i <= imax:
            frmdata  = {"ajax": '1',
            "nb_locations": "0"}
            frmdata.update(nb_locations = str(i))
            i = i + 10
            headr = {"X-Requested-With": "XMLHttpRequest",
                    "Referer": "http://www.lg-immobilier.fr/location/biens",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"}
            url = 'http://www.lg-immobilier.fr/locations/ajax'
            yield scrapy.FormRequest(url=url,
                                 callback=self.parse,
                                 headers = headr,
                                 formdata = frmdata)


    def parse(self, response):
        soup = BeautifulSoup(response.body)
        links = []
        for link in soup.find_all("a"):
            links.append(link["href"].replace('\/', '/')[2:-2])

        for j in range(0, len(links)):
            yield scrapy.Request(
                url=links[j],
                callback=self.get_property_details,
                meta={'external_link':links[j]})

    def get_property_details(self, response):
        item = ListingItem()

        external_link = response.meta.get('external_link')
        item["external_link"] = external_link

        sub_soup = BeautifulSoup(response.body)

        city = sub_soup.find("div", {"class" : "row"}).find("ul").find("li").text
        item["city"] = city

        item["title"] = sub_soup.find("div", {"class" : "row"}).find("h2").text

        item["rent"] = getSqureMtr(sub_soup.find("strong", {"class" : "price"}).text.replace(',', '.').split(' ')[0].split('\xa0')[0])
        
        description = ''
        for desc in sub_soup.find("div", {"class" : "col-md-10"}).findAll("p"):
            description = description+' '+desc.text
        item["description"] = description
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True
        if "zwembad" in description.lower() or "swimming" in description.lower():
            item["swimming_pool"] = True
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True

        images = []
        for img in sub_soup.find("div", {"class":"col-sm-5"}).findAll("img"):
            images.append(img.get("src"))
        item["images"]= images
        item["external_images_count"]= len(images)

        item["currency"]='EUR'

        for li in sub_soup.find("div", {"class" : "row"}).find("ul").findAll("li"):
            if "Maison" in li.text:
                property_type = "house"
                item["property_type"] = property_type
                item["room_count"] = int(sub_soup.find("div", {"class" : "row"}).find("h2").text[-1])
            if "Terrasse" in li.text:
                item["terrace"] = True
            if "balcon" in li.text:
                item["balcony"] = True
            if "Ascenseur" in li.text:
                item["elevator"] = True
            if "Meublé" in li.text:
                item["furnished"] = True
            if "T1" in li.text:
                property_type = "studio"
                item["property_type"] = property_type
                item["room_count"] = 1
            if "T2" in li.text:
                property_type = "apartment"
                item["property_type"] = property_type
                item["room_count"] = 1
            if "T3" in li.text:
                property_type = "apartment"
                item["property_type"] = property_type
                item["room_count"] = 2
            if "Parkin" in li.text:
                property_type = "parking"
                item["property_type"] = property_type
        item["property_type"] = property_type   

        item["landlord_phone"] = sub_soup.find("ul", {"class" : "list-unstyled list-inline link"}).find("a")['href'][4:]
        
        item["external_id"] = sub_soup.find("div", {"class": "col-md-2"}).find("h1").text.split(' ')[-1].split('°')[-1]
        
        item["external_source"] = 'immobilier_PySpider_france_fr'

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item




