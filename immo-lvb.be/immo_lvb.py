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
import base64
import pydash
from datetime import datetime

def numfromStr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text)==2:
        output = list_text[0]+list_text[1]
    elif len(list_text)==1:
        output = list_text[0]
    else:
        output=None

    return output


#============================================================================================================

def getImgList(soup):

    imgUrls = soup.findAll("meta" ,property="og:image")

    imgLst = []

    for img in imgUrls:
        imgLst.append(img["content"])


    return imgLst

#============================================================================================================
def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    else:
        date = text
    return date

#============================================================================================================
def getEpcNdDate(text):
    energy_lb = None
    splt_text=text.lower().split(" epc ")
    if len(splt_text) > 1:
        energy_lb = re.findall(r'\d+',splt_text[-1])[0]+" kWh/m²"


    date=None
    m = re.findall(r'([0-9]{1,2}\/[0-9]{1,2}\/[0-9]{4})',text)
    if m:
        date = strToDate(m[0])

    return energy_lb,date

#============================================================================================================

def scrapePropDetail(listPropty):

    list_data = []
    for index,echData in enumerate(listPropty):

        print(">>>>>>>",index)

        dic = {}

        external_id = echData["FortissimmoID"]
        external_link = "https://www.immo-lvb.be/nl"+echData["Property_URL"]
        external_source ="immo-lvb.be"
        zipcode = echData["Property_Zip"]
        city = echData["Property_City_Value"]
        description = echData["Property_Description"]
        latitude = str(echData["Property_Lat"])
        longitude= str(echData["Property_Lon"])
        title = echData["Property_Title"]
        address = echData["Property_Reference"]+","+zipcode+" "+city
        landlord_name = "Katrien Kerckaert"
        landlord_phone = "+32 56 21 81 00"
        landlord_email = "info@immo-lvb.be"

        property_type = echData["Property_HeadType_Value"]

        if "étudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
            property_type = "student_apartment"
        elif "appartement" in property_type.lower():
            property_type = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower():
            property_type = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
            property_type = "room"
        elif "studio" in property_type.lower():
            property_type = "studio"
        else:
            property_type = "NA"


        epc,date = getEpcNdDate(description)
        if epc:
            pydash.set_(dic,"energy_label",epc)
        if date:
            pydash.set_(dic,"available_date",date)


        rent = int(numfromStr(echData["Property_Price"]))
        if rent or rent!=0:
            pydash.set_(dic,"rent",rent)

        bedCount = int(echData["bedrooms"])
        if bedCount or bedCount!=0:
            pydash.set_(dic,"room_count",bedCount)




        if "garage" in description.lower() or "parkeerplaat" in description.lower():
            pydash.set_(dic,"parking",True)
        if "lift" in description.lower() or "elevator" in description.lower():
            pydash.set_(dic,"elevator",True)
        if "terras" in description.lower():
            pydash.set_(dic,"terrace",True)
        if "balcon" in description.lower() or "balcony" in description.lower():
            pydash.set_(dic,"balcony",True)
        if "zwembad" in description.lower() or "swimming pool" in description.lower():
            pydash.set_(dic,"swimming_pool",True)
        if "gemeubileerd" in description.lower() or "furnished" in description.lower():
            pydash.set_(dic,"furnished",True)
        # if "lave" in description.lower() and "vaisselle" in description.lower():
        #   pydash.set_(dic,"dishwasher",True)
        # if "machine à laver" in description.lower():
        #   pydash.set_(dic,"washing_machine",True)



        count = 0
        while count < 5:
            try:
                response = requests.get(external_link,timeout=30)
                count = 5
            except Exception as e:
                print (e)
            count+=1


        soup = BeautifulSoup(response.content,"html.parser")
        imgLst = getImgList(soup)



        dic.update({"property_type":property_type,"address":address,"city":city,"zipcode":zipcode,"latitude":latitude,"title":title,
            "longitude":longitude,"landlord_name":landlord_name,"landlord_email":landlord_email,"landlord_phone":landlord_phone,
            "description":description,"images":imgLst,"external_link":external_link,"external_source":external_source,
            "external_images_count":len(imgLst),"external_id":external_id,"currency":"EUR"})


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            list_data.append(dic)

    return list_data

#============================================================================================================


def scrapProprty(url):

    count = 0
    while count < 5:
        try:
            response = requests.get(url,timeout=30)
            count = 5
        except Exception as e:
            print (e)
        count+=1

    m = re.search('var mediatoken(.+?);', response.content.decode("utf-8"))
    text = m.group(1)
    tokenVal = text.strip().strip("=").strip()


    listPropty = []
    for i in range(1,100):

        url = "https://www.immo-lvb.be/Modules/ZoekModule/RESTService/SearchService.svc/GetPropertiesJSON/0/0"

        data = {"Transaction":"2","Type":"0","City":"0","MinPrice":"0","MaxPrice":"0","MinSurface":"0","MaxSurface":"0","MinSurfaceGround":"0","MaxSurfaceGround":"0",
        "MinBedrooms":"0","MaxBedrooms":"0","Radius":"0","NumResults":"15","StartIndex":i,"ExtraSQL":"0","ExtraSQLFilters":"0","NavigationItem":"0","PageName":"0",
        "Language":"NL","CountryInclude":"0","CountryExclude":"0","Token":"YPFHLEWQXCTQYUHJEYGQUQTQENJRSSQPLEXHMCNUKBJXVLZMUU","SortField":"1","OrderBy":1,"UsePriceClass":False,
        "PriceClass":"0","SliderItem":"0","SliderStep":"0","CompanyID":"0","SQLType":"3","MediaID":"0","PropertyName":"0","PropertyID":"0","ShowProjects":False,
        "Region":"0","currentPage":"0","homeSearch":"0","officeID":"0","menuIDUmbraco":"0","investment":False,"useCheckBoxes":False,"CheckedTypes":"0","newbuilding":False,
        "bedrooms":0,"latitude":"0","longitude":"0","ShowChildrenInsteadOfProject":False,"state":"0","FilterOutTypes":""}


        count = 0
        while count < 5:
            try:
                response = requests.post(url,json=data,timeout=30)
                count = 5
            except Exception as e:
                print (e)
            count+=1

        list_data = (json.loads(response.content.decode("utf-8")))



        if len(list_data) > 0:
            listPropty.extend(list_data)
        else:
            break

    return scrapePropDetail(listPropty)



#============================================================================================================
url = "https://www.immo-lvb.be/nl/te-huur/"
data = json.dumps(scrapProprty(url),indent=4, sort_keys=True, default=str)

# print (data)

with open('immo_lvb.json','w') as f:
    f.write(data)