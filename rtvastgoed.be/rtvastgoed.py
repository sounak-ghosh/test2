#!/usr/bin/env python
# coding: utf-8

import requests 
from bs4 import BeautifulSoup
import re,json
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
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
	coordinates = lat+","+lng
	location = locator.reverse(coordinates)
	return location

def extractPrice(text):
	textlst = re.findall(r'\d+', text)
	if len(textlst)==3:
		return int(textlst[0]+textlst[1])
	elif len(textlst)==2:
		return int(textlst[0])
	elif len(textlst)==1:
		return int(textlst[0])
	else:
		return 0


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
	elif isinstance(data,(list,tuple)):
		lis = []
		for i in data:
			lis.append(cleanKey(i))
		return lis
	else:
		return data

def getSqureMtr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text) == 2:
		output = int(list_text[0])
	elif len(list_text) == 1:
		output = int(list_text[0])
	else:
		output=0

	return output



def scrapDetail(soup):

	dic = {}
	imgLst = []

	title = soup.find("div",class_="property__header-block").find("h1").text.strip()

	add = soup.find("div",class_="property__header-block__adress__street")
	if add:
		pydash.set_(dic,"address",add.text.strip())
	#==================================================================================================

	img_urls = soup.find("div",class_="prop-pictures").findAll("a")
	for img in img_urls:
		imgLst.append("https://www.rtvastgoed.be"+img["href"])

	#==================================================================================================
	description = soup.find("div",class_="property__details__block__description").text.strip()
	#==================================================================================================

	if "garage" in soup.text.lower() or "parking" in soup.text.lower():
		pydash.set_(dic,"parking",True)
	if "zwembad" in description.lower() or "swimming" in description.lower():
		pydash.set_(dic,"swimming_pool",True)
	if "gemeubileerd" in description.lower() or "furnished" in description.lower() or "ingericht" in soup.text.lower():
		pydash.set_(dic,"furnished",True)
	# if "machine à laver" in description.lower():
	# 	pydash.set_(dic,"washing_machine",True)
	# if "lave" in description.lower() and "vaisselle" in description.lower():
	# 	pydash.set_(dic,"dishwasher",True)
	if "terras" in description.lower():
		pydash.set_(dic,"terrace",True)
	if "lift" in description.lower():
		pydash.set_(dic,"elevator",True)
	#==================================================================================================


	if soup.find("div",class_="gmap",id="pand-map"):
		latitude = soup.find("div",class_="gmap",id="pand-map")["data-geolat"]
		longitude = soup.find("div",class_="gmap",id="pand-map")["data-geolong"]

		pydash.set_(dic,"latitude",latitude)
		pydash.set_(dic,"longitude",longitude)

		location = getAddress(latitude,longitude)
		address = location.address

		if "postcode" in location.raw["address"]:
			pydash.set_(dic,"zipcode",location.raw["address"]["postcode"])
		if "city_district" in location.raw["address"]:
			pydash.set_(dic,"city",location.raw["address"]["city_district"])

	#==================================================================================================

	rec_dic = {}
	leftDiv = soup.find("div",class_="col-sm-12 col-md-6 property__details__left-col")
	rightDiv = soup.find("div",class_="col-sm-12 col-md-6 property__details__right-col")

	if leftDiv:
		odd_trs = leftDiv.findAll("tr",class_ = 'odd')
		even_trs = leftDiv.findAll("tr",class_ = 'even')
		if odd_trs:
			for ech_trs in odd_trs:
				keys = ech_trs.find("td",class_="label").text.strip()
				values = ech_trs.find("td",class_="value").text.strip()
				rec_dic.update({keys:values})
		if even_trs:
			for ech_trs in even_trs:
				keys = ech_trs.find("td",class_="label").text.strip()
				values = ech_trs.find("td",class_="value").text.strip()
				rec_dic.update({keys:values})

	if rightDiv:
		odd_trs = rightDiv.findAll("tr",class_ = 'odd')
		even_trs = rightDiv.findAll("tr",class_ = 'even')
		if odd_trs:
			for ech_trs in odd_trs:
				keys = ech_trs.find("td",class_="label").text.strip()
				values = ech_trs.find("td",class_="value").text.strip()
				rec_dic.update({keys:values})
		if even_trs:
			for ech_trs in even_trs:
				keys = ech_trs.find("td",class_="label").text.strip()
				values = ech_trs.find("td",class_="value").text.strip()
				rec_dic.update({keys:values})

	rec_dic = cleanKey(rec_dic)

	#==================================================================================================

	if "huurwaarborg" in rec_dic:
		pydash.set_(dic,"deposit",extractPrice(rec_dic["huurwaarborg"]))
	if "vrijop" in rec_dic:
		pydash.set_(dic,"available_date",strToDate(rec_dic["vrijop"]))	

	if "woonoppervlakte" in rec_dic:
		if getSqureMtr(rec_dic["woonoppervlakte"]):
			square_meters= getSqureMtr(rec_dic["woonoppervlakte"])
			pydash.set_(dic,"square_meters",square_meters)
	elif "grond_oppervlakte" in rec_dic:
		if getSqureMtr(rec_dic["grond_oppervlakte"]):
			square_meters= getSqureMtr(rec_dic["grond_oppervlakte"])
			pydash.set_(dic,"square_meters",square_meters)

	if "prijs" in rec_dic:
		if extractPrice(rec_dic["prijs"]):
			rent = extractPrice(rec_dic["prijs"])
			pydash.set_(dic,"rent",rent)

	if "aantalslaapkamers" in rec_dic:
		if extractPrice(rec_dic["aantalslaapkamers"]):
			bedCount = extractPrice(rec_dic["aantalslaapkamers"])
			pydash.set_(dic,"room_count",bedCount)

	if "autostaanplaats" in rec_dic:
		pydash.set_(dic,"parking",True)
	if "lift" in rec_dic:
		pydash.set_(dic,"elevator",True)

	#==================================================================================================


	dic.update({
		"title":title,
		"description":description,
		"images":imgLst,
		"external_images_count":len(imgLst),
		"landlord_name":"RT VERHUUR",
		"landlord_phone":"+32 11 69 76 40",
		"landlord_email":"verhuur@rtvastgoed.be",
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

	listProperty = []
	for section in soup.findAll("section"):
		proptyList = section.find("div",class_="row").findAll("div",class_="row")

		for index,propty in enumerate(proptyList):
			# print (index)
			extrnlurl="https://www.rtvastgoed.be"+propty.find("a",class_="spotlight__content__moreinfo link")["href"]

			count = 0
			while  count < 5:
				try:
					response = requests.get(extrnlurl,timeout=30)
					count = 5
				except Exception as e:
					print (e)
				count +=1

			print (extrnlurl)

			property_type = section.find("h2").text.strip()
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

			soup = BeautifulSoup(response.content,"html.parser")

			details_dic = scrapDetail(soup)
			
			details_dic.update({"property_type":property_type,
				"external_link":extrnlurl,"external_source":"rtvastgoed.be"})


			if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
				listProperty.append(details_dic)

	return listProperty


url = "https://www.rtvastgoed.be/nl/te-huur/"
data = json.dumps(getPropertyDetails(url),indent=4, sort_keys=True, default=str)

# print (data)

with open('rtvastgoed.json','w') as f:
    f.write(data)