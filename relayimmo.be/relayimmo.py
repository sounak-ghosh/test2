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


def numfromStr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text)==2:
		output = int(list_text[0]+list_text[1])
	elif len(list_text)==1:
		output = int(list_text[0])
	else:
		output=0

	return output

def getAddress(lat,lng):
	coordinates = str(lat)+","+str(lng)
	location = locator.reverse(coordinates)
	return location


def getLatLng(city,country):
	loc = locator.geocode(city+','+ country)
	return loc.latitude,loc.longitude


def getSqureMtr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text) == 2:
		output = int(list_text[0])
	elif len(list_text) == 1:
		output = int(list_text[0])
	else:
		output=0

	return output



def getSubInfo(soup):


	dic = {}

	title = soup.find("div",class_="col-12 col-lg-8").find("h1").text.strip()
	description = soup.find("div",class_="col-12 col-lg-8").find("p").text.strip()


	if soup.find("div",class_="price-features"):

		for ech_text in soup.find("div",class_="price-features").text.split("  "):

			if "habitation" in ech_text.lower() and getSqureMtr(ech_text):
				pydash.set_(dic,"square_meters",getSqureMtr(ech_text))

			if "etage" in ech_text.lower():
				pydash.set_(dic,"floor",ech_text.lower().strip())

			if "espec" in ech_text.lower():
				pydash.set_(dic,"energy_label",ech_text.replace("Espec","").strip())

			if "salle de bain" in ech_text.lower() and getSqureMtr(ech_text):
				pydash.set_(dic,"bathroom_count",getSqureMtr(ech_text))				


	priceBox = soup.find("div",class_ = "prices-box")
	if priceBox.find("h6",class_="heading-uppercase"):
		external_id = priceBox.find("h6",class_="heading-uppercase").text.strip()
		pydash.set_(dic,"external_id",external_id.replace("REF","").strip())



	priceTexts = priceBox.find("div",class_="price-features")

	if priceTexts:
		for ech_i in priceTexts.text.split("  "):
			if "dispo le" in ech_i.lower():
				date = strToDate(ech_i.lower().replace("dispo le","").strip())
				pydash.set_(dic,"available_date",date)



	if "lift" in description.lower() and "geen lift" not in description.lower():
		pydash.set_(dic,"elevator",True)
	if "garage" in description.lower() or "parking" in description.lower():
		pydash.set_(dic,"parking",True)
	if "terras" in description.lower():
		pydash.set_(dic,"terrace",True)
	if "balcon" in description.lower() or "balcony" in description.lower():
		pydash.set_(dic,"balcony",True)
	if "zwembad" in description.lower() or "swimming" in description.lower():
		pydash.set_(dic,"swimming_pool",True)
	if "gemeubileerd" in description.lower()or "aménagées" in description.lower() or "furnished" in description.lower():
		pydash.set_(dic,"furnished",True)
	if "machine à laver" in description.lower():
		pydash.set_(dic,"washing_machine",True)
	if "lave" in description.lower() and "vaisselle" in description.lower():
		pydash.set_(dic,"dishwasher",True)

	pictures = soup.find("div" ,class_="owl-carousel owl-nav-right margin-bottom-30").findAll("img",alt="")
	imgLst = []
	for pics in pictures:
		imgLst.append(pics["src"])

	if ("student" in title.lower() or "étudiant" in title.lower() or  "studenten" in title.lower()) and ("apartment" in title.lower() or "appartement" in title.lower()):
	    property_type = "student_apartment"
	elif "appartement" in title.lower() or "apartment" in title.lower():
	    property_type ="apartment"
	elif "woning" in title.lower() or "maison" in title.lower() or "huis" in title.lower() or "house" in title.lower():
	    property_type = "house"
	elif "chambre" in title.lower() or "kamer" in title.lower() or "room" in title.lower():
	    property_type = "room"
	# elif "commerciale" in title.lower() or "reclame" in title.lower() or "commercial" in title.lower():
	#     property_type = "property_for_sale"
	elif "studio" in title.lower():
	    property_type = "studio"
	else:
	    property_type = "NA"


	dic.update({
		"title":title,
		"description":description,
		"images":imgLst,
		"external_images_count":len(imgLst),
		"landlord_name":"Relay Immo",
		"landlord_phone":"+32 (0) 69 22 90 99",
		"property_type":property_type,
		"currency":"EUR"
	})

	return dic



def getPropInfo(list_prop):

	list_data=[]

	for propSoup in list_prop:

		city = propSoup.find("h2").text.strip()

		rent = None
		if numfromStr(propSoup.find("h4").text.strip()):
			rent = numfromStr(propSoup.find("h4").text.strip())

		latitude,longitude = getLatLng(city,"Belgium")
		location = getAddress(latitude,longitude)
		address = location.address
		zipcode = location.raw["address"]["postcode"] 

		bedCount = None
		if propSoup.find("i",class_="flaticon-bed"):
			bedCount = int(numfromStr(propSoup.find("span").text.strip()))

		external_source = "relayimmo.be"
		external_link = "https://www.relayimmo.be/"+propSoup.find("a",class_ = "portfolio-link")["href"]

		print (external_link)
		count = 0
		while count < 5:
			try:
				response = requests.get(external_link,timeout=30)
				count = 5
			except Exception as e:
				print(e)
			count+=1

		soup = BeautifulSoup(response.content,"html.parser")
		dic_detail = getSubInfo(soup)

		dic_detail.update({"address":address,"city":city,"zipcode":zipcode,"latitude":str(latitude),
			"longitude":str(longitude),"external_link":external_link,"external_source":external_source})

		if rent:
			pydash.set_(dic_detail,"rent",rent)
		if bedCount:
			pydash.set_(dic_detail,"room_count",bedCount)

		if dic_detail["property_type"] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
			list_data.append(dic_detail)

	return list_data






def scrpProptry():
	listPropties = []
	for i in range(100):
		print("page>>>>",i)
		url = "https://www.relayimmo.be/Chercher-bien-accueil--L--resultat?pagin={}&localiteS=&type=&prixmaxS=70-10000000&chambreS=&keyword=&".format(i)

		count = 0
		while count < 5:
			try:
				response = requests.get(url,timeout=30)
				count = 5
			except Exception as e:
				print(e)
			count+=1

		soup =BeautifulSoup(response.content,"html.parser")

		if soup.find("a",class_ = "portfolio-link"):
			allPropDiv = soup.findAll("div",class_="portfolio-box")[2:]
			listPropties.extend(allPropDiv)
		else:
			break

	return getPropInfo(listPropties)
	

data = json.dumps(scrpProptry(),indent=4, sort_keys=True, default=str)

with open('relayimmo.json','w') as f:
    f.write(data)