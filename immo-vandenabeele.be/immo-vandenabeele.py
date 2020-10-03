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
		date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
	else:
		date = text
	return date


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

def numfromStr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text)==2:
		output = int(list_text[0])
	elif len(list_text)==1:
		output = int(list_text[0])
	else:
		output=0

	return output


def getAddress(lat,lng):
	coordinates = lat+","+lng
	location = locator.reverse(coordinates)
	return location

def scrapDetail(soup):
	imgLst = []
	dic = {}
	currency = "EUR"


	if soup.find("div",class_="s-small-slider__text"):
		if soup.find("div",class_="s-small-slider__text").find("div",class_="s-text-markup"):
			latlan = soup.find("div",class_="s-small-slider__text").find("div",class_="s-text-markup").find("a")["href"].split("query=")[-1]

			latitude = latlan.split(",")[0]
			longitude = latlan.split(",")[-1]

			pydash.set_(dic,"latitude",latitude)
			pydash.set_(dic,"longitude",longitude)

			location = getAddress(latitude,longitude)
			zipcode = location.raw["address"]["postcode"]
			pydash.set_(dic,"zipcode",zipcode)



	descp_div = soup.find("div",class_="s-container--small")
	if descp_div:
		description = descp_div.find("div",class_="s-text-markup s-text-container-centered").text.strip()
		pydash.set_(dic,"description",description)

	imgUrls = soup.find("div",class_="s-small-slider__items")#.findAll("a")
	if imgUrls:
		imgUrls = soup.find("div",class_="s-small-slider__items").findAll("a")
		for imgs in imgUrls:
			imgLst.append(imgs["href"])




	recDiv = soup.find("div",class_="s-text-container-data s-text-container-data--col-4").findAll("div",class_="s-text-container-col-4-col")

	rec = {}
	for echRec in recDiv:
		head = echRec.findAll("div")[0].text.strip()
		value = echRec.findAll("div")[1].text.strip()
		rec.update({head:value})
	cln_dic = cleanKey(rec)
	

	if "huisdieren" in cln_dic:
		if cln_dic["huisdieren"] == "Niet toegelaten":
			pydash.set_(dic,"pets_allowed",False)
		else:
			pydash.set_(dic,"pets_allowed",True)
	if "beschikbaarheid" in cln_dic:
		pydash.set_(dic,"available_date",strToDate(cln_dic["beschikbaarheid"]))


	dic.update({
			"currency":currency,
			"landlord_name":"Agence Van den Abeele",
			"landlord_email":"info@agencevandenabeele.be",
			"landlord_phone":"050 33 39 76"})

	if imgLst:
		dic.update({"images":imgLst,"external_images_count":len(imgLst)})

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

	json_load = json.loads(response.content.decode("utf-8"))


	list_proprty=[]
	for index,propty in enumerate(json_load["data"]):

		print (">>>>>",index)

		dump_data = json.dumps(propty).lower()


		external_link = propty["url"]
		title = propty["title"]
		bedroom = propty["bedrooms"]
		city = propty["city"]
		external_source = "agencevandenabeele.be"
		rent = propty["price"]
		square_meters = propty["surface"]

		textlist =  propty["slug"].lower().split(city.lower())
		address = textlist[0]+city
		proptyType = propty["typeSlug"]


		####################property types##################
		if "étudiant" in proptyType.lower() or  "studenten" in proptyType.lower() and "appartement" in proptyType.lower():
			proptyType = "student_apartment"
		elif "appartement" in proptyType.lower():
			proptyType = "apartment"
		elif "woning" in proptyType.lower() or "maison" in proptyType.lower() or "huis" in proptyType.lower():
			proptyType = "house"
		elif "chambre" in proptyType.lower() or "kamer" in proptyType.lower():
			proptyType = "room"
		elif "studio" in proptyType.lower():
			proptyType = "studio"
		#####################################################


		if proptyType in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"] and external_link:
			count = 0
			while  count < 5:
				try:
					response = requests.get(external_link,timeout=30)
					count = 5
				except Exception as e:
					print (">>>>>>>>",e)
				count +=1

			soup = BeautifulSoup(response.content,"html.parser")

			dic_details = scrapDetail(soup)

			dic_details.update({"title":title,"external_link":external_link,
				"city":city,"property_type":proptyType,"external_source":external_source,"address":address})

			if "inrichten" in dump_data or "furnished" in dump_data:
				pydash.set_(dic_details,"furnished",True)

			if "garage" in dump_data or "parking" in dump_data:
				pydash.set_(dic_details,"parking",True)

			if rent:
				pydash.set_(dic_details,"rent",rent)

			if bedroom:
				pydash.set_(dic_details,"room_count",bedroom)

			if int(square_meters):
				pydash.set_(dic_details,"square_meters",int(square_meters))			

			list_proprty.append(dic_details)

	return list_proprty



url = "https://www.agencevandenabeele.be/nl/api/properties.json?grid=1240,1599&pg=1"
	  # "https://www.agencevandenabeele.be/nl/api/properties.json?grid=1240,1599&pg=1"
data = json.dumps(getPropertyDetails(url),indent=4, sort_keys=True, default=str)

with open('immo-vandenabeele.json','w') as f:
    f.write(data)