# -*- coding: utf-8 -*-
import ssl,requests,json,time,csv,random
import re
from bs4 import BeautifulSoup
import sys
from multiprocessing import Process, Pool
import random
import json
import os,re
from lxml.html import fromstring
from geopy.geocoders import Nominatim
import pandas as pd
from datetime import datetime
import time 

FILE_NAME = "deboerenpartners"
locator = Nominatim(user_agent="myGeocoder")

headers={
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"

}

def cleanText(text):
    text = ''.join(text.split())
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text).strip()
    return text.replace(" ","_").lower()



def cleanKey(data):
    if isinstance(data,dict):
        dic = {}
        for k,v in data.items():
            dic[cleanText(k)]=cleanKey(v)
        return dic
    else:
        return data


def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = locator.reverse(coordinates)
    return location


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


def get_geo_location(soup):
    
    our_text = str(soup)

    m = re.search('var estatemarker =(.+?);', our_text)
    found = m.group(1)
    res = eval(found)
    
    lat = str(res[1])
    lon = str(res[2])

    location = getAddress(lat,lon)
    address = location.address
    return lat,lon,address

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%d-%m-%Y').strftime('%Y-%m-%d')
    else:
        date = text
    return date
def num_there(s):
    return any(i.isdigit() for i in s)
def numfromStr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text)>0:
		output = int(list_text[0])
	else:
		output=0

	return output
def get_data(my_property,scraped_data):
    # function for scraping all required data
    url = my_property
    print(url)
    
    response = get_page_response(url,'get',None)                     
    ps = fromstring(response.text) 
    soup = BeautifulSoup(response.content,'html.parser')


    rec_info = {}
    if soup.find("div",id="details"):
        all_detail_line = soup.find("div",id="details").findAll("div",class_="detail-line")
        for line in all_detail_line:
            if line.find("div",class_="left") and line.find("div",class_="right"):
                rec_info.update({line.find("div",class_="left").text:line.find("div",class_="right").text.strip()})

    rec_info = cleanKey(rec_info)

    print (">>>>>>>>>>>>> Here I AM",rec_info)    
    if 'badkamers' in rec_info:
        scraped_data.update({'bathroom_count':int(rec_info['badkamers'])})
    if 'epc' in rec_info and  num_there(rec_info['epc']) :
        scraped_data.update({'energy_label':rec_info['epc']})
    if 'lasten_maand' in rec_info :
        scraped_data.update({'utilities':numfromStr(rec_info['lasten_maand'])})    
             
    try:
        room_count = ps.xpath("//div[@class='bed']/following-sibling::div[1]//text()")
        room_count = [x.strip() for x in room_count if x.strip()][0]
    except:
        room_count = None
    if room_count:
        scraped_data.update({'room_count':int(room_count)}) 

    rent = ps.xpath("//div[@class='col-sm-3 price']//text()")
    rent = [y.strip() for y in rent if y.strip()][0].replace(u'€','').replace('.','')
    try:
        rent = int(rent)
    except:
        rent = None
    if rent:
        scraped_data.update({'rent':rent})      


    # calling functions to get latitute and longitute data
    try:
        latitude,longitude,address = get_geo_location(soup)
    except:
      latitude,longitude,address = None,None,None

    if latitude:
        scraped_data.update({'latitude':latitude})  
    if longitude:
        scraped_data.update({'longitude':longitude})    
    if address:
        scraped_data.update({'address':address})    



    scraped_data["external_link"] = url
    scraped_data["external_source"] = 'deboerenpartners.be'

    scraped_data["title"] = ps.xpath("//div[@class='col-lg-7 col-md-8']//text()")
    scraped_data["title"] = [z.strip() for z in scraped_data["title"] if z.strip()][0].strip()


    
    try:
        city = address.split(',')[-3].strip()
    except:
        city = None
    try:
        zipcode = address.split(',')[-2].strip()
    except:
        zipcode = None
    if city:
        scraped_data.update({'city':city})  
    if zipcode:
        scraped_data.update({'zipcode':zipcode})        

    
    
    try:
        scraped_data["landlord_name"] = ps.xpath("//p[@class='agent-name']//text()")[0]
    except:
        scraped_data["landlord_name"] = 'deboerenpartners'
    try:        
        scraped_data["landlord_email"] = ps.xpath("//a[@class='blue-link-box black']/@href")[0].split(":")[1].split("?")[0]
    except:
        try:
            ld_details = ps.xpath("//div[@class='col-lg-5 col-lg-offset-1']//text()")
            for l in ld_details:
                if '@' in l:
                    scraped_data["landlord_email"] = l.strip()
                    break
        except:
            pass            

    try:    
        scraped_data["landlord_phone"] = ps.xpath("//a[@class='blue-link-box black visible-xs']/@href")[0].split(":")[1]
    except:
        try:
            ld_details = ps.xpath("//div[@class='col-lg-5 col-lg-offset-1']//text()")
            for l in ld_details:
                if '+' in l:
                    scraped_data["landlord_phone"] = l.strip()
                    break
        except:
            pass    
    specs = soup.findAll('div',class_='detail-line')
    for s in specs:
        attribute = s.find('div',class_='left').get_text()
        value = s.find('div',class_='right').get_text()
        if 'bemeubeld' in attribute.lower():
            if 'ja' in value.lower():
                furnished = True
                scraped_data.update({'furnished':furnished})
        if 'terras' in attribute.lower():
            if 'ja' in value.lower():
                scraped_data.update({'terrace':True})   
        if 'lift' in attribute.lower():
            if 'ja' in value.lower():
                scraped_data.update({'elevator':True})  
        if 'parkings' in attribute.lower() or 'garages' in attribute.lower():
            if 'ja' in value.lower():
                parking = True  
                scraped_data.update({'parking':parking})
        if 'grond opp.' in attribute.lower():
            value = value.split('.')[1].replace(u'm²','').strip()   
            scraped_data.update({'square_meters':int(value)})
        if 'referentie nr.' in attribute.lower(): 
            value = value.strip()   
            scraped_data.update({'external_id':value})
        if 'lasten / maand' in attribute.lower():
            value = value.replace(u'€','').replace('.','')
            scraped_data.update({'utilities':int(value)})   
        if 'verdieping' in attribute.lower():
            value = value
            scraped_data.update({'floor':value})                            

    if 'balkon' in soup.get_text().lower():
        balcony = True
        scraped_data.update({'balcony':balcony})
    if 'zwembad' in soup.get_text().lower():
        scraped_data.update({'swimming_pool':True})

    available_date = ps.xpath("//font[contains(text(),'Beschikbaar')]/text()")
    if not available_date:
        available_date = ps.xpath("//h3[contains(text(),'Beschikbaar')]/text()")
    # print(available_date)
    for av in available_date:
        if '/' in av:
            a_d = av.split(":")[1].strip()
            date_time_obj = strToDate(a_d)
            scraped_data.update({'available_date':date_time_obj})
            break
        elif '-' in av:
            a_d = av.split(":")[1].strip()
            # print("=======>",a_d)
            date_time_obj = strToDate(a_d)
            scraped_data.update({'available_date':date_time_obj})
            break
        else:
            a_d = av.split(":")[1].strip()
            scraped_data.update({'available_date':a_d}) 
    
    

    description = ps.xpath("//div[@class='col-lg-10 col-lg-offset-2 col-md-12']//font[contains(@style,'vertical')]/text()")
    if not description:
        description = ps.xpath("//div[@class='col-lg-10 col-lg-offset-2 col-md-12']//text()")
    description = [x.strip() for x in description if x.strip()] 
    description = ''.join(description)
        
    scraped_data["description"] = description.strip().split('Contacteer')[0]


    images = ps.xpath("//div[contains(@class,'foto-box-slider slide')]//a/@href")

    image_list = []
    for img in images:
        if 'https:' in img:
            image_list.append(img)
        else:
            im = 'https://www.deboerenpartners.be'+img
            image_list.append(im)   
    image_list = list(set(image_list))
    scraped_data["images"] = image_list
    scraped_data["external_images_count"] = len(scraped_data["images"])

    if 'appartement' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'apartment' 
    elif 'binnenstaanplaats' in scraped_data["title"].lower():
        return None
    elif 'kantoor' in scraped_data["title"].lower():
        return None 
    elif 'bedrijfsgebouw' in scraped_data["title"].lower():
        return None
    elif 'handelszaak' in scraped_data["title"].lower():
        return None
    elif 'villa' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'house'
    elif 'huis' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'house'
    elif 'garage' in    scraped_data["title"].lower():
        return None
    elif 'duplex te huur' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'room'
    elif 'bel-etage te huur' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'room'  
    elif 'gelijkvloerse verdieping te huur' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'room'  
    elif 'studio' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'studio'
    elif 'eengezinswoning'  in scraped_data["title"].lower():
        scraped_data['property_type'] = 'house' 
    elif 'penthouse' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'house' 
    elif 'assistentiewoning' in scraped_data["title"].lower():
        scraped_data['property_type'] = 'room'  

    else:
        return 'not required'


    try:
        check = scraped_data['utilities']
    except:
        check = False

    # print(scraped_data)
    return scraped_data
    

def get_all_property_links():
    # scraping property links and addresses
    all_properties = []
    print('getting all property links...')
    i = 1
    while True:
        next_url = 'https://www.deboerenpartners.be/ajax/estates/'+str(i)+'?term=&status=te+huur&bedrooms=&sort=null&view=gall&_=1600660207870'
        print(next_url)
        response = get_page_response(next_url,'get',None)
        try:                     
            ps = fromstring(response.text) 
        except:
            break   
        property_urls = ps.xpath("//a[@class='content']/@href")
        if property_urls:
            for index, p in enumerate(property_urls):
                p = 'https://www.deboerenpartners.be'+p
                all_properties.append(p)
        else:
            break       
        i += 1  
        

    print(len(all_properties))
    return all_properties       




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
        "currency":"EUR"
        }
    global json_list    
    json_list = []

    # calling get_all_property_links function first to scrape all required property links
    all_properties = get_all_property_links()
    print('property links extraction completed...')

    print("Starting data extraction...")
    #calling get data function to scrape required data from each links

    for ind, each_property in enumerate(all_properties[:]):
        scraped_data = scraped_data_all.copy()
        if each_property == 'https://www.deboerenpartners.be':
            continue
        json_object = get_data(each_property,scraped_data)
        if not json_object or json_object == 'not required':
            continue
        print(ind)
        # print(json_object)
        json_list.append(json_object)   
    json_object = json.dumps(json_list,indent=4, sort_keys=True, default=str)
    # json_object = json.dumps(json_list)
    with open("deboerenpartners.json", "w") as outfile: 
        outfile.write(json_object) 

if __name__ == "__main__":
    main()
  
