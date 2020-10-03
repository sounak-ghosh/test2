#!/usr/bin/env python
# coding: utf-8

import requests 
from bs4 import BeautifulSoup
import re,json
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import ast
import base64
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


def numfromStr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text)==2:
		output = int(list_text[0]+list_text[1])
	elif len(list_text)==1:
		output = int(list_text[0])
	else:
		output=None

	return output



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

#============================================================================================================

def getSubInfo(soup):

	dic ={}

	title = soup.find("div",class_="row divDetailTxt").find("div",class_="col-md-4").find("h1").text.strip()

	description = soup.find("div",class_ = "divTxt").text.strip()

	if "lift" in description.lower() and "geen lift" not in description.lower():
		pydash.set_(dic,"elevator",True)
	if "garage" in description.lower():
		pydash.set_(dic,"parking",True)
	if "terras" in description.lower():
		pydash.set_(dic,"terrace",True)
	if "balcon" in description.lower() or "balcony" in description.lower():
		pydash.set_(dic,"balcony",True)
	if "zwembad" in description.lower() or "swimming pool" in description.lower():
		pydash.set_(dic,"swimming_pool",True)
	if "gemeubileerd" in description.lower() or "furnished" in description.lower():
		pydash.set_(dic,"furnished",True)

	landlordDiv = soup.find("div",class_="divSR")
	if landlordDiv:
		landlord_name = landlordDiv.find("h3").text.strip()
		landlord_email = landlordDiv.find("a",title = "email").text.strip()
		landlord_phone  = landlordDiv.find("a",title = "tel").text.strip()

		pydash.set_(dic,"landlord_name",landlord_name)
		pydash.set_(dic,"landlord_email",landlord_email)
		pydash.set_(dic,"landlord_phone",landlord_phone)



	imgLst = []
	pictures = soup.findAll("picture", class_ = "")
	for pics in pictures:
		imgLst.append(pics.find("img")["src"])


	rec_dic = {}
	table_div = soup.find("div",class_ = "tabs-content")
	if table_div:
		for ech_tab in table_div.findAll("table"):
			all_tr = ech_tab.findAll("tr")
			for tr in all_tr:
				keys = tr.find("td",class_= "kenmerklabel").text.strip()
				values = tr.find("td",class_= "kenmerk").text.strip()
				rec_dic.update({keys:values})

	rec_dic = cleanKey(rec_dic)


	if "beschikbaarvanaf" in rec_dic:
		pydash.set_(dic,"available_date",strToDate(rec_dic["beschikbaarvanaf"]))
	if "huisdierentoegelaten" in rec_dic:
		if "Neen" in rec_dic["huisdierentoegelaten"]:
			pydash.set_(dic,"pets_allowed",False)
		else:
			pydash.set_(dic,"pets_allowed",True)
	if "slaapkamers" in rec_dic:
		pydash.set_(dic,"room_count",int(rec_dic["slaapkamers"]))

	dic.update({
		"title":title,
		"description" : description,
		"images" : imgLst,
		"external_images_count" : len(imgLst),
		"currency": "EUR"
	})

	return dic


#============================================================================================================

def getProptyInfo(list_propty):

	list_data=[]
	for index,eachData in enumerate(list_propty):

		print (">>>>>>",index)
		zipcode = None
	
		address = eachData["address"]
		city = eachData["city"]
		rent = numfromStr(eachData["price"])
		external_link = "https://www.vastgoedsinnaeve.be"+eachData["detailLink"]
		external_source = "vastgoedsinnaeve.be"
		latitude = eachData["latitude"]
		longitude = eachData["longitude"]

		property_type=eachData["type"]
		if ("student" in property_type.lower() or "étudiant" in property_type.lower() or  "studenten" in property_type.lower()) and ("apartment" in property_type.lower() or "appartement" in property_type.lower()):
		    property_type = "student_apartment"
		elif "appartement" in property_type.lower() or "apartment" in property_type.lower():
		    property_type ="apartment"
		elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "house" in property_type.lower():
		    property_type = "house"
		elif "chambre" in property_type.lower() or "kamer" in property_type.lower() or "room" in property_type.lower():
		    property_type = "room"
		# elif "commerciale" in property_type.lower() or "reclame" in property_type.lower() or "commercial" in property_type.lower():
		#     property_type = "property_for_sale"
		elif "studio" in property_type.lower():
		    property_type = "studio"
		else:
		    property_type = "NA"

		print (external_link)

		if latitude and longitude:
			location = getAddress(latitude,longitude)
			zipcode = location.raw["address"]["postcode"]

		count = 0
		while count < 5:
			try:
				response = requests.get(external_link)
				count = 5
			except Exception as e:
				print (e)
			count +=1

		soup = BeautifulSoup(response.content,"html.parser")
		dic_details=getSubInfo(soup)

		dic_details.update({"address":address,"city":city,"external_link":external_link,
			"external_source":external_source,"property_type":property_type,"latitude":latitude,
			"longitude":longitude})

		if zipcode:
			dic_details.update({"zipcode":zipcode})
		if rent:
			dic_details.update({"rent":rent})

		if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
			list_data.append(dic_details)
	return list_data


#============================================================================================================

def getProprtyDetail(url):

	count = 0
	while count < 5:
		try:
			response = requests.get(url,timeout = 30)
			count = 5
		except Exception as e:
			print (e)
		count +=1


	m = re.search('var infoPubs(.+?);', response.content.decode("utf-8"))
	text = m.group(1)
	jsnVal = text.strip().strip("=").strip()

	proplst = json.loads(jsnVal)

	return getProptyInfo(proplst)


#============================================================================================================
url = "https://www.vastgoedsinnaeve.be/te-huur?pageindex=1"
data = json.dumps(getProprtyDetail(url),indent=4, sort_keys=True, default=str)


# print (data)
with open('vastgoedsinnaeve.json','w') as f:
    f.write(data)