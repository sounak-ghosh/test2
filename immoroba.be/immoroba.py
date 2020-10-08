#!/usr/bin/env python
# coding: utf-8

import requests 
from bs4 import BeautifulSoup
import re,json
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import ast
from pprint import pprint
import pydash
from datetime import datetime


locator = Nominatim(user_agent="myGeocoder")


def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%d-%m-%Y').strftime('%Y-%m-%d')
    else:
        date = text
    return date


def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = locator.reverse(coordinates)
    return location


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

def latlong(text):
    res = ast.literal_eval(text)
    lat=res[0][1]
    lon=res[0][2]
    return lat,lon 


def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=None

    return output

def num_there(s):
    return any(i.isdigit() for i in s)

def scrapDetail(soup):

    dic = {}
    strSoup = str(soup)

    descrpt1 = soup.find("div",class_="eleven columns alpha").find("section").find("h2").text.strip()
    descrpt2 = soup.find("div",class_="eleven columns alpha").find("section").find("p",class_="description").text.strip()
    description = descrpt1+"\n"+descrpt2


    if "zwembad" in description.lower() or "swimming" in description.lower():
        pydash.set_(dic,"swimming_pool",True)
    if "gemeubileerd" in description.lower() or "furnished" in description.lower():
        pydash.set_(dic,"furnished",True)
    if "machine à laver" in description.lower():
      pydash.set_(dic,"washing_machine",True)
    if "lave" in description.lower() and "vaisselle" in description.lower():
      pydash.set_(dic,"dishwasher",True)


    all_tables = soup.findAll("table",class_="kenmerken")
    temp_dic = {}
    for table in all_tables:
        tds_keys = table.findAll("td",class_="kenmerklabel")
        tds_vals = table.findAll("td",class_="kenmerk")

        keys = [tag.text.strip() for tag in tds_keys]
        vals = [tag.text.strip() for tag in tds_vals]

        temp_dic.update(dict(zip(keys, vals)))

    temp_dic = cleanKey(temp_dic)

    if "epcindex" in temp_dic:
        pydash.set_(dic,"energy_label",temp_dic["epcindex"])

    if "badkamers" in temp_dic:
        if getSqureMtr(temp_dic["badkamers"]):
            pydash.set_(dic,"bathroom_count",getSqureMtr(temp_dic["badkamers"]))

    if "adres" in temp_dic:
        pydash.set_(dic,"address",temp_dic["adres"])

    if "terras" in temp_dic:
        pydash.set_(dic,"terrace",True)

    if "slaapkamers" in temp_dic:
        pydash.set_(dic,"room_count",int(temp_dic["slaapkamers"]))

    if "prijs" in temp_dic:
        rent = int(re.findall(r'\d+', temp_dic["prijs"])[0])
        pydash.set_(dic,"rent",rent)    

    if "parking" in temp_dic:
        pydash.set_(dic,"parking",True)

    if "type" in temp_dic:
        if "appartement" in temp_dic["type"].lower():
            pydash.set_(dic,"property_type","Apartment")
        else:
            pydash.set_(dic,"property_type",temp_dic["type"])


    pydash.set_(dic,"property_type","NA")
    if "type" in temp_dic:
        if ("student" in temp_dic["type"].lower() or "étudiant" in temp_dic["type"].lower() or  "studenten" in temp_dic["type"].lower()) and ("apartment" in temp_dic["type"].lower() or "appartement" in temp_dic["type"].lower()):
            pydash.set_(dic,"property_type","student_apartment")
        elif "appartement" in temp_dic["type"].lower() or "apartment" in temp_dic["type"].lower():
            pydash.set_(dic,"property_type","apartment")
        elif "woning" in temp_dic["type"].lower() or "maison" in temp_dic["type"].lower() or "huis" in temp_dic["type"].lower() or "house" in temp_dic["type"].lower():
            pydash.set_(dic,"property_type","house")
        elif "chambre" in temp_dic["type"].lower() or "kamer" in temp_dic["type"].lower() or "room" in temp_dic["type"].lower():
            pydash.set_(dic,"property_type","room")
        # elif "commerciale" in temp_dic["type"].lower() or "reclame" in temp_dic["type"].lower() or "commercial" in temp_dic["type"].lower():
        #     pydash.set_(dic,"property_type","property_for_sale")
        elif "studio" in temp_dic["type"].lower():
            pydash.set_(dic,"property_type","studio")
        else:
            pydash.set_(dic,"property_type","NA")



    if "lift" in temp_dic:
        if "Ja" == temp_dic["lift"]:
            pydash.set_(dic,"elevator",True)
        else:
            pydash.set_(dic,"elevator",False)

    if "beschikbaarvanaf" in temp_dic:
        if num_there(temp_dic["beschikbaarvanaf"]):
            pydash.set_(dic,"available_date",strToDate(temp_dic["beschikbaarvanaf"]))

    if "huisdierentoegelaten" in temp_dic:
        if "Neen" == temp_dic["huisdierentoegelaten"]:
            pydash.set_(dic,"pets_allowed",False)
        else:
            pydash.set_(dic,"pets_allowed",True)            

    if "bewoonbareopp" in temp_dic:
        if getSqureMtr(temp_dic["bewoonbareopp"]):
            square_meters = getSqureMtr(temp_dic["bewoonbareopp"])
            pydash.set_(dic,"square_meters",square_meters)


    

    m = re.search('infoPanden(.+?);', strSoup)
    text = m.group(1)
    textLst = text.strip().strip("=").strip()

    latitude,longitude=latlong(textLst)

    location = getAddress(latitude,longitude)
    zipcode = location.raw["address"]["postcode"]
    city=location.raw["address"]["city_district"]


    picturesLs = soup.find("div",   class_="eleven columns alpha").findAll("a",class_='slick_link',href=True)
    imgLst = []
    for img in picturesLs:
        imgLst.append(img["href"])

    dic.update({
        "description":description,
        "images":imgLst,
        "latitude":str(latitude),
        "longitude":str(longitude),
        "landlord_name":"IMMO ROBA",
        "landlord_phone":"09 / 388.53.53 (ZULTE OFFICE) 056 / 140.200",
        "landlord_email":"info@immoroba.be",
        "zipcode":zipcode,
        "city":city,
        "external_images_count":len(imgLst),
        "currency":"EUR"
    })

    return dic



def getPropertyDetails(url):
    count = 0
    while  count < 5:
        try:
            response = requests.get(url,timeout=30)
            count = 5
        except Exception as e:
            print (e)
        count +=1

    soup = BeautifulSoup(response.content,"html.parser")
    all_page = soup.find("div",class_="paging").findAll("div",class_="paging-box")[-2].text.strip()


    list_property = []
    for page in range(1,int(all_page)+1):

        url = "http://www.immoroba.be/te-huur?pageindex={}".format(str(page))
        count = 0
        while  count < 5:
            try:
                response = requests.get(url,timeout=30)
                count = 5
            except Exception as e:
                print (e)
            count +=1

        soup = BeautifulSoup(response.content,"html.parser")

        all_proprty = soup.find("div",class_="container offer").findAll("div",id=True,recursive=False)



        for proprty in all_proprty:

            if  proprty.find("a",class_="img"):

                external_link = "http://www.immoroba.be"+proprty.find("a",class_="img")["href"]
                external_source = "immoroba.be"

                title = proprty.find("div",class_="info").find("h3").text.strip()

                count = 0
                while  count < 5:
                    try:
                        response = requests.get(external_link,timeout=30)
                        count = 5
                    except Exception as e:
                        print (e)
                    count +=1

                print (external_link)

                soup2 = BeautifulSoup(response.content,"html.parser")


                dict_detail = scrapDetail(soup2)

                dict_detail.update({"external_link":external_link,"external_source":external_source})

                if dict_detail["property_type"] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                    list_property.append(dict_detail)

    return list_property




url = "http://www.immoroba.be/te-huur"

data = json.dumps(getPropertyDetails(url),indent=4, sort_keys=True, default=str)

# print (data)

with open('immoroba.json','w') as f:
    f.write(data)