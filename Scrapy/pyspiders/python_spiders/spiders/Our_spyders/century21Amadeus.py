# -*- coding: utf-8 -*-
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date

import ssl,requests,json,time,csv,random
import re
from bs4 import BeautifulSoup
import sys
from multiprocessing import Process, Pool
import random
import os
from datetime import datetime
import geopy
from geopy.geocoders import Nominatim

locator = Nominatim(user_agent="myGeocoder")

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = locator.reverse(coordinates)
    return location

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date



class UpgradeimmoSpider(scrapy.Spider):
    name = 'century21_amadeus_PySpider_belgium_nl'
    allowed_domains = ['century21.be']
    start_urls = ['www.century21.be']
    execution_type = 'testing'
    country = 'belgium'
    locale ='nl'

    def start_requests(self):
        start_urls=[{"url":"https://api.prd.cloud.century21.be/api/v2/properties?facets=elevator%2Ccondition%2CfloorNumber%2Cgarden%2ChabitableSurfaceArea%2ClistingType%2CnumberOfBedrooms%2Cparking%2Cprice%2CsubType%2CsurfaceAreaGarden%2CswimmingPool%2Cterrace%2CtotalSurfaceArea%2Ctype&filter=eyJib29sIjp7ImZpbHRlciI6eyJib29sIjp7Im11c3QiOlt7Im1hdGNoIjp7Imxpc3RpbmdUeXBlIjoiRk9SX1JFTlQifX0seyJyYW5nZSI6eyJjcmVhdGlvbkRhdGUiOnsibHRlIjoiMjAyMC0wOS0zMFQwODo1NDoyOC43NjMifX19XX19fX0%3D&pageSize=800&sort=-creationDate",
            "property_type":''}]
        for urls in start_urls:
            yield scrapy.Request(url=urls.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': urls.get('property_type')})


    def parse(self, response, **kwargs):
        all_data = json.loads(response.body)

        count = 0
        for j_data in all_data["data"]:
            count+=1
            item = ListingItem()
            properties_id = j_data['id']
            p_city = j_data['address']['city'].lower().replace(' ','-')
            p_type = j_data['type']


            if ("student" in p_type.lower() or "étudiant" in p_type.lower() or  "studenten" in p_type.lower()) and ("apartment" in p_type.lower() or "appartement" in p_type.lower()):
                p_type = "student_apartment"
            elif "appartement" in p_type.lower() or "apartment" in p_type.lower():
                p_type ="apartment"
            elif "woning" in p_type.lower() or "maison" in p_type.lower() or "huis" in p_type.lower() or "house" in p_type.lower():
                p_type = "house"
            elif "chambre" in p_type.lower() or "kamer" in p_type.lower() or "room" in p_type.lower():
                p_type = "room"
            elif "studio" in p_type.lower():
                p_type = "studio"
            else:
                p_type = "NA"

            if j_data['type'] in ["APARTMENT","HOUSE"]:
                # print (count)

                if j_data['type'] == "APARTMENT":
                    type_txt = "appartement"
                else:
                    type_txt = "maison"

                item["external_link"] ='https://www.century21.be/fr/properiete/a-louer/'+type_txt+'/'+ p_city + '/'+properties_id
                item["property_type"] = j_data["type"].lower()
                item["city"] = j_data['address']['city'].lower().replace(' ','-')

                if "reference" in j_data and j_data['reference']:
                    item["external_id"] = j_data['reference']

                if "rooms" in j_data and "numberOfBedrooms" in j_data["rooms"]:
                    if int(j_data['rooms']['numberOfBedrooms']):
                        item["room_count"] = int(j_data['rooms']['numberOfBedrooms'])

                if "rooms" in j_data and "numberOfBathrooms" in j_data["rooms"]:
                    if int(j_data['rooms']['numberOfBathrooms']):
                        item["bathroom_count"] = int(j_data['rooms']['numberOfBathrooms'])


                if "energySpecifications" in j_data and "energyScore" in j_data["energySpecifications"] and "value" in j_data["energySpecifications"]["energyScore"]:
                    item["energy_label"] = str(j_data["energySpecifications"]["energyScore"]["value"])+" kw/m²/année"
                
                if "floorNumber" in j_data:
                    item["floor"] = j_data['floorNumber']

                if int(j_data['price']['amount']):
                    item["rent"] = int(j_data['price']['amount'])

                if "location" in j_data:
                    item["latitude"],item["longitude"] = str(j_data['location']['latitude']),str(j_data['location']['longitude'])

                    location = getAddress(item["latitude"],item["longitude"])
                    item["address"] = location.address
                
                if "address" not in item:
                    try:
                        item["address"] = j_data['address']['number']+' '+j_data['address']['street'] +', '+j_data['address']['city']+', '+j_data['address']['postalCode']+', '+j_data['address']['countryCode']
                    except:
                        pass

                item["external_source"] = 'century21_amadeus_PySpider_belgium_nl'



                if "fr" in j_data['title'] and j_data['title']['fr']:
                    item["title"] = j_data['title']['fr']
                elif "nl" in j_data['title'] and j_data['title']['nl']:
                    item["title"] = j_data['title']['nl']
                elif "en" in j_data['title'] and j_data['title']['en']:
                    item["title"] = j_data['title']['en']


                if "address" in j_data and "city" in j_data['address']:
                    item["city"] = j_data['address']['city']
                
                
                if "address" in j_data and "postalCode" in j_data['address']:
                    item["zipcode"] = j_data['address']['postalCode']

                agency_url = 'https://api.prd.cloud.century21.be'+j_data['_links']['agency']['href']

                if "amenities" in j_data and 'elevator' in j_data["amenities"]:
                    item["elevator"] = j_data["amenities"]["elevator"]


                try:        
                    pool = j_data['amenities']['swimmingPool']
                    if pool:
                        item["swimming_pool"] = True
                except:
                    pass

                try:    
                    parking = j_data['amenities']['parking']
                    if parking:
                        item["parking"] = True
                except:
                    pass

                try:    
                    terrace = j_data['amenities']['terrace']
                    if terrace:
                        item["terrace"] = True  
                except:
                    pass


                if "surfaceAreaLivingRoom" in j_data['surface']:
                    square_meters = j_data['surface']['surfaceAreaLivingRoom']['value']
                    if int(square_meters):
                        item["square_meters"] = int(square_meters)
                elif "habitableSurfaceArea" in j_data['surface']:
                    square_meters = j_data['surface']['habitableSurfaceArea']['value']
                    if int(square_meters):
                        item["square_meters"] = int(square_meters)
                     

                if "fr" in j_data['description'] and j_data['description']["fr"]:
                    description = j_data['description']['fr']
                    item["description"] = description.strip()
                elif "nl" in j_data['description'] and j_data['description']["nl"]:
                    description = j_data['description']['nl']
                    item["description"] = description.strip()
                elif "en" in j_data["description"] and j_data['description']["en"]:
                    description = j_data['description']['en']
                    item["description"] = description.strip()

                images = j_data['images']
                image_list = []
                for img in images:
                    try:
                        name = img['name']
                        img_id = j_data['id']
                        image = 'https://d1hhh7ugrdocx1.cloudfront.net/property-assets/'+img_id+'/'+name
                        image_list.append(image)
                    except:
                        continue        
                
                if image_list:
                    item["images"] = image_list
                    item["external_images_count"] = len(item["images"])

                item["currency"] = "EUR"
                try:
                    a_d = j_data['availableFrom']
                    date_time_obj = strToDate(a_d)
                    item["available_date"] = date_time_obj
                except:
                    pass

                print (agency_url)


                agency_res = requests.get(agency_url)
                js_d = json.loads(agency_res.content.decode("utf-8"))

                if "data" in js_d and "name" in js_d['data']:
                    item["landlord_name"] = js_d['data']['name']
                
                if "data" in js_d and "email" in js_d['data']:        
                    item["landlord_email"] = js_d['data']['email']
                
                if "data" in js_d and "phoneNumber" in js_d['data']:        
                    item["landlord_phone"] = js_d['data']['phoneNumber']

                yield item

    # def get_property_details(self, response):

    #     js_d = json.loads(response.body)
    #     print (response.meta.get("agency_url"),">>>>>",js_d)
    #     item = response.meta.get("item")
    
    #     if "data" in js_d and "name" in js_d['data']:
    #         item["landlord_name"] = js_d['data']['name']
        
    #     if "data" in js_d and "email" in js_d['data']:        
    #         item["landlord_email"] = js_d['data']['email']
        
    #     if "data" in js_d and "phoneNumber" in js_d['data']:        
    #         item["landlord_phone"] = js_d['data']['phoneNumber']

    #     yield item
