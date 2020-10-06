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


def getAddress(lat,lng):
	coordinates = str(lat)+","+str(lng)
	location = locator.reverse(coordinates)
	return location


def getLatLng(city,country):
	loc = locator.geocode(city+','+ country)
	return loc.latitude,loc.longitude

def num_there(s):
    return any(i.isdigit() for i in s)

#============================================================================================================

def basicInfo(soup):
	parking,bedroom,rent = False,0,0
	a,b = False,False

	list_det = re.findall(r'\d+', soup.find("span").text)

	if soup.find("i",class_="flaticon-bed"):
		a=True
	if soup.find("i",class_="ti-car"):
		b=True


	if len(list_det) == 4:
		bedroom = list_det[0].strip()
		parking = True
		rent = list_det[-2].strip()+list_det[-1].strip()

	elif len(list_det) == 3:
		if a:
			bedroom = list_det[0].strip()					
		if b:
			parking = True

		if a and b:
			rent = list_det[-1].strip()
		else:
			rent = list_det[-2].strip()+list_det[-1].strip()

	elif len(list_det) == 2:
		if a:
			bedroom = list_det[0].strip()
		if b:
			parking = True

		if not a and not b:
			rent = list_det[-2].strip()+list_det[-1].strip()
		else:
			rent = list_det[-1].strip()

	else:
		rent = list_det[-1].strip()


	return bedroom,parking,rent



def numfromStr(text):
	list_text = re.findall(r'\d+',text)

	if len(list_text)>0:
		output = int(list_text[0])
	else:
		output=0

	return output


def getSqureMtr(text):
	list_text = re.findall(r'\d+',text)
	output = list_text[0]

	return output
#============================================================================================================
def scrapDetail2(soup):

	dic = {}

	title = soup.find("h1",class_="font-weight-light").text.strip()
	descrp2 = soup.find("p",align="justify").text.strip()

	tot_descrp = title+".\n"+descrp2



	if "Charges :" in tot_descrp:
		temp_ults = numfromStr(tot_descrp.split("Charges :")[-1])
		if temp_ults:
			pydash.set_(dic,"utilities",temp_ults)



	if soup.find("div",class_="bg-white padding-40 box-shadow-with-hover border-radius"):
		consumption_data = soup.find("div",class_="bg-white padding-40 box-shadow-with-hover border-radius").text

		if "Conso Spécifique" in consumption_data:
			egry = consumption_data.split(":")[1].strip().split("  ")[0].strip()
			if egry:
				pydash.set_(dic,"energy_label",egry)


	if "lift" in tot_descrp.lower():
		pydash.set_(dic,"elevator",True)
	elif "geen lift" not in tot_descrp.lower():
		pydash.set_(dic,"elevator",False)
	if "garage" in tot_descrp.lower() or "parking" in tot_descrp.lower():
		pydash.set_(dic,"parking",True)
	if "terras" in tot_descrp.lower():
		pydash.set_(dic,"terrace",True)
	if "balcon" in tot_descrp.lower() or "balcony" in tot_descrp.lower():
		pydash.set_(dic,"balcony",True)
	if "zwembad" in tot_descrp.lower() or "swimming" in tot_descrp.lower():
		pydash.set_(dic,"swimming_pool",True)
	if "gemeubileerd" in tot_descrp.lower() or "furnished" in tot_descrp.lower():
		pydash.set_(dic,"furnished",True)
	# if "machine à laver" in tot_descrp.lower():
	# 	pydash.set_(dic,"washing_machine",True)
	# if "lave" in tot_descrp.lower() and "vaisselle" in tot_descrp.lower():
	# 	pydash.set_(dic,"dishwasher",True)


	img_div = soup.find("div",class_="owl-carousel owl-nav-overlay owl-dots-overlay margin-bottom-30").findAll("img")
	list_img=[]
	for img in img_div:
		list_img.append(img["src"])

	lanlord_no=soup.find("a",href="envoyer-un-message--contact")["title"]
	landlord_name = "Aller vers le site du DL Groupe"


	for p in soup.findAll("p"):
		if p.find("i",class_="fa fa-location-arrow"):
			address = p.text.strip()
			pydash.set_(dic,"address",address)
			break

	if "étudiant" in title.lower() or  "studenten" in title.lower() and "appartement" in title.lower():
	    property_type = "student_apartment"
	elif "appartement" in title.lower():
	    property_type = "apartment"
	elif "woning" in title.lower() or "maison" in title.lower() or "huis" in title.lower():
	    property_type = "house"
	elif "chambre" in title.lower() or "kamer" in title.lower():
	    property_type = "room"
	# elif "commerciale" in title.lower() or "reclame" in title.lower():
	#     property_type = "property_for_sale"
	elif "studio" in title.lower():
	    property_type = "studio"
	else:
		property_type = "NA"


	if soup.find("i",class_="flaticon-decrease"):
		for echDiv in soup.find("div",class_="row fontIcon").findAll("div",class_="col ficheIcon"):
			if echDiv.find("i",class_="flaticon-decrease"):
				square_meters = int(getSqureMtr(echDiv.text.strip()))
				pydash.set_(dic,"square_meters",square_meters)


	if len(title.split(".")) > 1:
		for ech_txt in title.split(".")[1:]:
			if "libre" in ech_txt.lower():
				if num_there(strToDate(ech_txt.strip())):
					pydash.set_(dic,"available_date",strToDate(ech_txt.strip()))

		# if "available_date" not in dic:
		# 	for ech_txt in title.split(";"):
		# 		if "libre" in ech_txt.lower() and num_there(ech_txt):
		# 			pydash.set_(dic,"available_date",strToDate(ech_txt.strip()))



	dic.update({"property_type":property_type,"images":list_img,"external_images_count":len(list_img),
		"landlord_name":landlord_name,"landlord_phone":lanlord_no,
		"description":tot_descrp,"title":title,"currency":"EUR"})

	return dic

#============================================================================================================

def scrapDetail(soup):

	main_div = soup.find("div",class_="container-fluid").find("div",class_=True,recursive=False)
	if main_div:

		propertyList = main_div.findAll("div",recursive=False)
		list_data = []
		for propty in propertyList:

			extrn_link="http://www.cabinet056.be/"+propty.find("a",class_="portfolio-link")["href"]


			cityDiv = propty.find("div",class_="portfolio-title")
			city = cityDiv.find("h6").text.strip()
			
			latitude,longitude = getLatLng(city,"Belgium")
			location = getAddress(latitude,longitude)
			zipcode = location.raw["address"]["postcode"] 

			rootInfo=basicInfo(cityDiv)

			print (extrn_link)
			count = 0
			while count < 5:
				try:
					response = requests.get(extrn_link,timeout = 30)
					count = 5
				except Exception as e:
					print (e)
				count+=1

			soup2 = BeautifulSoup(response.content,"html.parser")
			dic_detail = scrapDetail2(soup2)

			dic_detail.update({"city":city,"external_link":extrn_link,
				"external_source":"cabinet056.be","zipcode":zipcode,"latitude":str(latitude),
				"longitude":str(longitude)})


			if int(rootInfo[0]) != 0:
				pydash.set_(dic_detail,"room_count",int(rootInfo[0]))
			if rootInfo[1]:
				pydash.set_(dic_detail,"parking",True)
			if int(rootInfo[2]) != 0:
				pydash.set_(dic_detail,"rent",int(rootInfo[2]))

			if dic_detail["property_type"] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
				list_data.append(dic_detail)

		return list_data


#============================================================================================================

def scrapProprties(url):
	count = 0
	while count < 5:
		try:
			response = requests.get(url,timeout = 30)
			count = 5
		except Exception as e:
			print (e)
		count+=1

	soup = BeautifulSoup(response.content,"html.parser")
	pagination = soup.find("ul",class_="pagination justify-content-center margin-top-70").findAll("li")[-2]


	list_data = []
	for i in range(int(pagination.text)):
		print ("PAGE=>>>",i)

		url = "http://www.cabinet056.be/Chercher-bien-accueil--L--resultat?pagin={}&regionS=&communeS=&type=&prixmaxS=&chambreS=&keyword=&viager=&listeLots=".format(str(i))
		count = 0
		while count < 5:
			try:
				response = requests.get(url,timeout = 30)
				count = 5
			except Exception as e:
				print (e)
			count+=1

		soup = BeautifulSoup(response.content,"html.parser")
		data_ = scrapDetail(soup)

		list_data.extend(data_)

	return list_data





#============================================================================================================
url = "http://www.cabinet056.be/maison-a-vendre--L--resultat"
data = json.dumps(scrapProprties(url),indent=4, sort_keys=True, default=str)

with open('cabinet056.json','w') as f:
    f.write(data)
