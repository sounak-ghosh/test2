import json
import pandas as pd
import sys



json_template={"external_link":"str","external_source":"str","external_images_count":"int","washing_machine":"bool","dishwasher":"bool","bathroom_count":"int","external_id":"str","title":"str","description":"str","city":"str","zipcode":"str","address":"str","latitude":"str","longitude":"str","property_type":"str","square_meters":"int","room_count":"int","available_date":"str","images":"list","floor_plan_images":"list","rent":"int","currency":"str","deposit":"int","prepaid_rent":"int","utilities":"int","water_cost":"int","heating_cost":"int","energy_label":"str","pets_allowed":"bool","furnished":"bool","floor":"str","parking":"bool","elevator":"bool","balcony":"bool","terrace":"bool","swimming_pool":"bool","landlord_name":"str","landlord_email":"str","landlord_phone":"str"}

must_required = {"external_link":[],"property_type":[],"currency":[],"address":[],"external_source":[]}




def getStats(iterator):
	dic_stats = {}
	for data in iterator:
		for key,value in data.items():

			value_type = str(type(value)).replace("<class '","").replace("'>","")

			if key in dic_stats and  value_type in dic_stats[key][0]:
				dic_stats[key] = [dic_stats[key][0],dic_stats[key][1]+1]

			elif key in dic_stats and value_type not in dic_stats[key][0]:
				dic_stats[key] = [dic_stats[key][0]+","+value_type,dic_stats[key][1]+1]
			else:
				dic_stats[key] = [value_type,1]

	if dic_stats:
		df = pd.DataFrame()
		for k,v in dic_stats.items():
			df = df.append({"Attribute": k,"DataType":v[0],"TotalKey":int(v[1])},ignore_index=True)

	print ("______________________JSON Stats___________________")
	print (df)
	print ("\n")




def errorType(iterator):
	dic_data = {}
	for index,data in enumerate(iterator):
		for key,value in data.items():

			value_type = str(type(value)).replace("<class '","").replace("'>","")

			if key in json_template and value_type != json_template[key]:
				dic_data.update({key:"Wrong DataType"})

			elif key not in json_template:
				dic_data.update({key:"Unkown Attribute"})

		for k in must_required:
			if k not in data:
				must_required[k].append(index)
				must_required.update({k:must_required[k]})

	df1 = pd.DataFrame(columns=["Attribute","ErrorType"])
	for k,v in dic_data.items():
		df1 = df1.append({"Attribute": k,"ErrorType":v},ignore_index=True)

	print ("______________________Error Stats___________________")
	print (df1)
	print ("\n")



	df2 = pd.DataFrame(columns=["Attribute","MissingKeys"])
	for k,v in must_required.items():
		df2 = df2.append({"Attribute": k,"MissingKeys":v},ignore_index=True)

	print ("______________________Missing Required Keys Stats___________________")
	print (df2)


if  __name__ == "__main__":
	sys_args = sys.argv
	if len(sys_args)==1:
		raise Exception("Please enter a JSON file name in argument")

	fileName = sys_args[1]
	iterator = json.loads(open(fileName,"r").read())

	getStats(iterator)
	errorType(iterator)