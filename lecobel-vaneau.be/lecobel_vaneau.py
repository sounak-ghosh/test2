#!/usr/bin/env python
# coding: utf-8

import requests 
from bs4 import BeautifulSoup
import re,json,time
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


def numfromStr(text,flag = False):
	list_text = re.findall(r'\d+',text)

	if len(list_text)==2:
		output = int(list_text[0]+list_text[1])
	elif len(list_text)==1:
		output = int(list_text[0])
	else:
		output=0

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




def proptyDetail(soup):

	dic = {"currency":"EUR"}

	if soup.find("section",id="description"):
		prortySoup = soup.find("section",id="description")
		description = prortySoup.find("div",class_="description").text.strip()
		dic.update({"description":description})

		soupstr = prortySoup.find("div",class_="specifications")

		rec_dic = {}
		if soupstr:
			for ech_div in soupstr.findAll("div"):
				if ":" in ech_div.text.strip():
					text_ = ech_div.text.strip().split(":")
					rec_dic.update({text_[0].strip():text_[1].strip()})
			rec_dic = cleanKey(rec_dic)


			if "balcony" in description.lower():
				pydash.set_(dic,"balcony",True)

			if "terrace" in rec_dic:
				if rec_dic["terrace"] == "Yes":
					pydash.set_(dic,"terrace",True)
				else:
					pydash.set_(dic,"properties.terrace",False)
			if "elevator" in description.lower() or "lift" in description.lower():
				pydash.set_(dic,"elevator",True)

			if "swimmingpool" in rec_dic:
				if rec_dic["swimmingpool"] == "Yes":
					pydash.set_(dic,"swimming_pool",True)
				else:
					pydash.set_(dic,"swimming_pool",False)

			if "furnished" in description.lower():
				pydash.set_(dic,"furnished",True)

			if "reference" in rec_dic:
				pydash.set_(dic,"external_id",rec_dic["reference"])			

			if "floor" in rec_dic:
				pydash.set_(dic,"floor",rec_dic["floor"])

			if "surface" in rec_dic:
				pydash.set_(dic,"square_meters",numfromStr(rec_dic["surface"]))

			if "parking_s" in rec_dic or "parking" in rec_dic:
				pydash.set_(dic,"parking",True)


		if soup.find("div",class_="informations__agent"):
			landlord_name = soup.find("div",class_="informations__agent").find('div',class_="name").text.strip()
			pydash.set_(dic,"landlord_name",landlord_name)

		landlord_phone = "+32 467 85 71 82"
		landlord_email = "rent@lecobel.be"

		dic.update({"landlord_phone":landlord_phone,"landlord_email":landlord_email})


	return dic




def getPropertyDetails(all_proprty):
	list_propty =[]
	for index,soup in enumerate(all_proprty):



		print (">>>>>",index)
		latitude = soup["data-latitude"]
		longitude = soup["data-longitude"]


		location = getAddress(latitude,longitude)

		zipcode = location.raw["address"]["postcode"]
		address = location.address

		city = None
		if "city_district" in location.raw["address"]:
			city=location.raw["address"]["city_district"]
		elif "city" in location.raw["address"]:
			city=location.raw["address"]["city"]
		elif "town" in location.raw["address"]:
			city=location.raw["address"]["town"]
		


		external_link = "https://www.lecobel-vaneau.be"+soup["data-url"]
		external_source = "lecobel-vaneau.be"
		title = soup.find("a",class_="link__property full-link")["title"]

		print (external_link)

		imgLst = []
		for picture in soup.findAll("source",type="image/webp"):
			imgLst.append("https://www.lecobel-vaneau.be"+(picture["srcset"]))


		price = soup.find("div",class_="property-price property-data--center").text.strip()
		rent = numfromStr(price)

		property_type = soup.find("div",class_="property-name property-data--bold property-data--center property-data--upper").text.split("-")[-1].strip()


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


		bedCount = 0
		if soup.find("div",class_="property-bedrooms property-data--center property-data--bold"):
			bedCount = numfromStr(soup.find("div",class_="property-bedrooms property-data--center property-data--bold").text.strip(),flag=True)
		
			


		count = 0
		while  count < 5:
			try:
				response = requests.get(external_link,timeout=30)
				count = 5
			except Exception as e:
				print (e)
			count +=1


		soup2 = BeautifulSoup(response.content,"html.parser")

		dic_detail =proptyDetail(soup2)

		dic_detail.update({"address":address,"zipcode":zipcode,"external_link":external_link,"title":title,
			"images":imgLst,"property_type":property_type,"latitude":latitude,"longitude":longitude,
			"external_images_count":len(imgLst),"external_source":"lecobel-vaneau.be"})

		if rent:
			pydash.set_(dic_detail,"rent",rent)
		if bedCount:
			pydash.set_(dic_detail,"room_count",bedCount)
		if city:
			pydash.set_(dic_detail,"city",city)

		if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
			list_propty.append(dic_detail)

	return list_propty



def scrapDetail(url):
	count = 0
	while  count < 5:
		try:
			response = requests.get(url,timeout=30)
			count = 5
		except Exception as e:
			print (e)
		count +=1

	soup = BeautifulSoup(response.content,"html.parser")

	all_proprty = soup.findAll("div",class_="property property__search-item")

	k = 30
	while True:
		url = "https://www.lecobel-vaneau.be/en/vaneau-search/search?field_ad_type[eq][]=renting&limit=28&mode=list&offset={}&offset_additional=0&search_page_id=580".format(k)
		print (url)

		count = 0
		while  count < 5:
			try:
				response = requests.get(url,timeout=30)
				count = 5
			except Exception as e:
				print (e)
			count +=1

		jsonLoad = json.loads(response.content.decode("utf-8"))

		if len(jsonLoad["html"]) < 200:
			break
		
		soup = BeautifulSoup(jsonLoad["html"],"html.parser")
		proprtys = soup.findAll("div",class_="property property__search-item")


		all_proprty.extend(proprtys)
		k+=28



	return getPropertyDetails(all_proprty)



url = "https://www.lecobel-vaneau.be/en/list-properties-tenant"
data = json.dumps(scrapDetail(url),indent=4, sort_keys=True, default=str)

with open('lecobel_vaneau.json','w') as f:
    f.write(data)