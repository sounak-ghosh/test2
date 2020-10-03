# -*- coding: utf-8 -*-
import ssl,requests,json,time,csv,random
import re
from bs4 import BeautifulSoup
import sys
from multiprocessing import Process, Pool
import random
import json
import os
from geopy.geocoders import Nominatim
# import pandas as pd
from datetime import datetime
import time 


FILE_NAME = "direct-immo"


headers={
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"

}

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date

    
def get_page_response(url,postmethod,data):
    # making a request here to the webpageoko
    Flag=True
    while Flag:
        try:
            session=requests.session()
            if postmethod == "get":
                    response=session.get(url, headers=headers)
            if postmethod == "post":
                    response=session.post(url, headers=headers,data=data)
            if response.status_code == 200 or response.status_code == 404:
                Flag=False
        except Exception as e:
            print(e)
    return response


def get_data(my_property,j_data,scraped_data):
    print (my_property)

    try:
        scraped_data["external_id"] = j_data['reference']
    except:
        pass
    try:
        if int(j_data['rooms']['numberOfBedrooms']):
            scraped_data["room_count"] = int(j_data['rooms']['numberOfBedrooms'])
    except:
        pass

    try:
        floor = j_data['floorNumber']
        scraped_data.update({'floor':floor})
    except:
        pass
    if int(j_data['price']['amount']):
        scraped_data["rent"] = int(j_data['price']['amount'])
    try:
        address = j_data['address']['number']+' '+j_data['address']['street'] +', '+j_data['address']['city']+', '+j_data['address']['postalCode']+', '+j_data['address']['countryCode']
    except:
        pass
    try:
        scraped_data["latitude"],scraped_data["longitude"] = str(j_data['location']['latitude']),str(j_data['location']['longitude'])
    except:
        pass

    scraped_data["external_link"] = my_property
    scraped_data["external_source"] = 'century21.be'



    if "fr" in j_data['title'] and j_data['title']['fr']:
        scraped_data["title"] = j_data['title']['fr']
    elif "nl" in j_data['title'] and j_data['title']['nl']:
        scraped_data["title"] = j_data['title']['nl']
    elif "en" in j_data['title'] and j_data['title']['en']:
        scraped_data["title"] = j_data['title']['en']
    else:
        url = my_property
        response = get_page_response(url,'get',None) 
        soup = BeautifulSoup(response.content,'html.parser')
        try:
            scraped_data["title"] = soup.find('span',class_='f61e46832046785f6884705d5b7e07b3').text
            if len(scraped_data["title"]):
                scraped_data["title"] = soup.find('span',class_='ee76812d104f99f75eff83f78d84039d').text
        except:
            pass


    try:
        scraped_data["city"] = j_data['address']['city']
    except:
        pass
    try:
        scraped_data["zipcode"] = j_data['address']['postalCode']
    except:
        pass
    
    agency_url = 'https://api.prd.cloud.century21.be'+j_data['_links']['agency']['href']
    resp = get_page_response(agency_url,'get',None)

    js_d = json.loads(resp.text)
    
    try:
        scraped_data["landlord_name"] = js_d['data']['name']
    except:
        pass
    try:        
        scraped_data["landlord_email"] = js_d['data']['email']
    except:
        pass
    try:    
        scraped_data["landlord_phone"] = js_d['data']['phoneNumber']
    except:
        pass
    try:
        lift = j_data['amenities']['elevator']
        if lift:
            scraped_data.update({'elevator':lift})
    except:
        pass    
    try:        
        pool = j_data['amenities']['swimmingPool']
        if pool:
            scraped_data.update({'swimming_pool':pool})
    except:
        pass
    try:    
        parking = j_data['amenities']['parking']
        if parking:
            scraped_data["parking"] = True
    except:
        pass
    try:    
        terrace = j_data['amenities']['terrace']
        if terrace:
            scraped_data["terrace"] = True  
    except:
        pass


    if "surfaceAreaLivingRoom" in j_data['surface']:
        square_meters = j_data['surface']['surfaceAreaLivingRoom']['value']
        if int(square_meters):
            scraped_data.update({'square_meters':int(square_meters)})
    elif "habitableSurfaceArea" in j_data['surface']:
        square_meters = j_data['surface']['habitableSurfaceArea']['value']
        if int(square_meters):
            scraped_data.update({'square_meters':int(square_meters)})   
         

    if "fr" in j_data['description']:
        description = j_data['description']['fr']
        scraped_data["description"] = description.strip()
    elif "nl" in j_data['description']:
        description = j_data['description']['nl']
        scraped_data["description"] = description.strip()
    elif "en" in j_data["description"]:
        description = j_data['description']['en']
        scraped_data["description"] = description.strip()

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
        
    scraped_data["images"] = image_list
    scraped_data["external_images_count"] = len(scraped_data["images"])

    property_types = j_data['type'].lower()
    try:
        a_d = j_data['availableFrom']
        date_time_obj = strToDate(a_d)
        scraped_data.update({'available_date':date_time_obj})
    except:
        pass    
    return scraped_data
    

def get_all_property_links(scraped_data_all):
    # scraping property links and addresses
    global json_list    
    json_list = []
    print('getting all property links...')
    
    # url = 'https://api.century21.be/api/v1/agencies/18c616bd-e09d-4a42-b2c5-61b06fd94e2f/properties?transferType=RENT&orderBy=updatedAt&fullText=true&start=0&nbResults=30'
    url = 'https://api.prd.cloud.century21.be/api/v2/properties?facets=elevator%2Ccondition%2CfloorNumber%2Cgarden%2ChabitableSurfaceArea%2ClistingType%2CnumberOfBedrooms%2Cparking%2Cprice%2CsubType%2CsurfaceAreaGarden%2CswimmingPool%2Cterrace%2CtotalSurfaceArea%2Ctype&filter=eyJib29sIjp7ImZpbHRlciI6eyJib29sIjp7Im11c3QiOlt7Im1hdGNoIjp7Imxpc3RpbmdUeXBlIjoiRk9SX1JFTlQifX0seyJyYW5nZSI6eyJjcmVhdGlvbkRhdGUiOnsibHRlIjoiMjAyMC0wOS0zMFQwODo1NDoyOC43NjMifX19XX19fX0%3D&pageSize=800&sort=-creationDate'
    response = get_page_response(url,'get',None)
        
    j_data = json.loads(response.text)
    properties = j_data['data']
    for p in properties[:]:
        scraped_data = scraped_data_all.copy()
        properties_id = p['id']
        p_type = p['type']

        if ("student" in p_type.lower() or "étudiant" in p_type.lower() or  "studenten" in p_type.lower()) and ("apartment" in p_type.lower() or "appartement" in p_type.lower()):
            p_type = "student_apartment"
        elif "appartement" in p_type.lower() or "apartment" in p_type.lower():
            p_type ="apartment"
        elif "woning" in p_type.lower() or "maison" in p_type.lower() or "huis" in p_type.lower() or "house" in p_type.lower():
            p_type = "house"
        elif "chambre" in p_type.lower() or "kamer" in p_type.lower() or "room" in p_type.lower():
            p_type = "room"
        # elif "commerciale" in p_type.lower() or "reclame" in p_type.lower() or "commercial" in p_type.lower():
        #     p_type = "property_for_sale"
        elif "studio" in p_type.lower():
            p_type = "studio"
        else:
            p_type = "NA"


        p_city = p['address']['city'].lower().replace(' ','-')

        prop_link = 'https://www.century21.be/nl/pand/te-huur/'+p_type+'/'+ p_city + '/'+properties_id
        json_object = get_data(prop_link,p,scraped_data)

        if p_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print (True)
            json_list.append(json_object)   
  
    json_object = json.dumps(json_list,indent=4, sort_keys=True, default=str)
    with open("century21expo.json", "w") as outfile: 
        outfile.write(json_object) 

    
            




def main():
    # required dictionary
    scraped_data_all = {
        "external_link": "",
        "external_source": "",
        "title": "",
        "description": "",
        "images": "",
        "landlord_name": "",
        "landlord_phone": "",
        "landlord_email": "",
        "external_images_count": None,
        }
    

    # calling get_all_property_links function first to scrape all required property links
    get_all_property_links(scraped_data_all)


if __name__ == "__main__":
    main()
  
