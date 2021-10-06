import os
from os.path import expanduser
import csv
import sys
from sys import platform
import sqlite3
import zipfile
import subprocess

from haversine import haversine

countries = {}
admin2 = {}
admin1 = {}
conn = None
BASE_URL = "http://download.geonames.org/export/dump/"
FILE_ONE = "allCountries.zip"
FILE_TWO = "countryInfo.txt"
FILE_THREE = "admin1CodesASCII.txt"
FILE_FOUR = "admin2Codes.txt"
LOCATION = ''

if sys.version_info[0] == 3:
	import urllib.request
elif sys.version_info[0] < 3:
	import urllib
	
def connectdatabase():
	global conn
	global LOCATION
	try:
		conn = sqlite3.connect(os.path.join(LOCATION, 'geo.db'))
		status = 'Database connected'
	except sqlite3.Error as e:
		status='Error in reverse geocode: '+str(e)

	return(status)

def creategeotable():
	try:
		sql ="""CREATE TABLE geotable(
        geo_name TEXT NOT NULL,
        geo_lat REAL NOT NULL,
        geo_lng REAL NOT NULL,
        geo_countrycode TEXT,
        geo_statecode TEXT,
        geo_citycode TEXT
        )"""
		cursor = conn.cursor()
		cursor.execute(sql)
		conn.commit()
		status = 'geotable created'
	except sqlite3.Error as e:
		if not 'table already exists' in str(e):
			status='Error occured in creating table geotable: '+ str(e)

	return(status)

def cleanup():
	global LOCATION
	if conn is not None:
		conn.close()

	if os.path.exists(os.path.join(LOCATION, 'allCountries.txt')):
		os.remove(os.path.join(LOCATION, 'allCountries.txt'))

	if os.path.exists(os.path.join(LOCATION, 'geonamesdata.csv')):
		os.remove(os.path.join(LOCATION, 'geonamesdata.csv'))

	if os.path.exists(os.path.join(LOCATION, 'allCountries.zip')):
		os.remove(os.path.join(LOCATION, 'allCountries.zip'))
	
def downloadfile(filename, savetofile):
	global BASE_URL
	global LOCATION
	savetofile = os.path.join(LOCATION, savetofile)
	if sys.version_info[0] == 3:
		try:
			urllib.request.urlretrieve(BASE_URL + filename, savetofile)
			status = filename + ' download complete ...'
		except Exception as e:
			status='Error downloading file: ' + filename + ' ' + str(e)
	elif sys.version_info[0] < 3:
		try:
			urllib.urlretrieve(BASE_URL + filename, savetofile)
			status = filename + ' download complete ...'
		except Exception as e:
			status='Error downloading file: ' + filename + ' ' + str(e)
	return(status)

def do_check():
	global conn
	global LOCATION
	downloadflag = 0
	if sys.version_info[0] < 3 and sys.version_info[1] < 5:
		status = 'Python version should be greater than 2.5'
		return(status)

	if platform == "win32":
		if not os.path.exists(os.path.join(LOCATION, 'sqlite3.exe')):
			status='sqlite3.exe not found.'
			return(status)
		connectdatabase()
	else:
		if not os.path.exists(os.path.join(LOCATION, 'sqlite3')):
			status='sqlite3 not found.'
			return(status)
		connectdatabase()
	
	sql="""SELECT
	NAME
	FROM
	SQLITE_MASTER
	WHERE
	TYPE = 'table'
	AND
	NAME = 'geotable';
	"""
	try:    
		cursor = conn.execute(sql)
		row = cursor.fetchone()
		if row is None:
			creategeotable()
			downloadflag = 1
		else:
			status = 'Start reverse geocode - geotable already exists ...'
	except sqlite3.Error as e:
	  	status = 'Error in reverse geocode: ' + str(e)
	  	return(status)

	if not os.path.exists(os.path.join(LOCATION, 'allCountries.zip')) and downloadflag == 1:
		status = downloadfile(FILE_ONE, 'allCountries.zip')
		if 'Error downloading file: ' in status:
			return(status)
		with zipfile.ZipFile(os.path.join(LOCATION, 'allCountries.zip'), 'r') as z:
			z.extractall(LOCATION)

		f=open(os.path.join(LOCATION, 'geonamesdata.csv'), 'w', encoding='UTF-8')

		with open(os.path.join(LOCATION, 'allCountries.txt'), 'r', encoding="utf8") as source:
			reader = csv.reader(source, delimiter='\t')
			for r in reader:
				f.write((r[2]+ '|' + r[4] + '|' + r[5] + '|' + r[8] + '|' + r[10] + '|' + r[11]+'\n'))
			f.close()

		#Enclosing LOCATION quotes allows for spaces in file path
		NL = '"' + LOCATION  + '/' + "geonamesdata.csv" + '"' 
		
		subprocess.call([
		os.path.join(LOCATION, "sqlite3"), 
		os.path.join(LOCATION, "geo.db"), 
		"-separator", "|" ,
		".import "+ NL + " geotable"
		])

	if not os.path.exists(os.path.join(LOCATION, 'countries.tsv')):
		status = downloadfile(FILE_TWO, 'countries.tsv')
		if 'Error downloading file: ' in status:
			return(status)

	if not os.path.exists(os.path.join(LOCATION, 'admin1.tsv')):
		status = downloadfile(FILE_THREE, 'admin1.tsv')
		if 'Error downloading file: ' in status:
			return(status)

	if not os.path.exists(os.path.join(LOCATION, 'admin2.tsv')):
		status = downloadfile(FILE_FOUR, 'admin2.tsv')
		if 'Error downloading file: ' in status:
			return(status)
	status = 'Start reverse geocode'
	return(status)
        
def geo_dictionary():
	with open(os.path.join(LOCATION, 'countries.tsv'), 'r', encoding="utf8") as source:
		reader = csv.reader(source, delimiter='\t')
		for row in reader:
			code = row[0]
			if not '#' in code:
				name = row[4]
				countries[code] = name
	with open(os.path.join(LOCATION, 'admin1.tsv'), 'r', encoding="utf8") as source:
		reader = csv.reader(source, delimiter='\t')
		for row in reader:
			code = row[0]
			name = row[1]
			admin1[code] = name
	with open(os.path.join(LOCATION, 'admin2.tsv'), 'r', encoding="utf8") as source:
		reader = csv.reader(source, delimiter='\t')
		for row in reader:
			code = row[0]
			name = row[1]
			admin2[code] = name

def get_location(latitude, longitude):
	global conn
	locationlist=[]
	geolocation = []
	haversinedistancelist=[]

	coordinates = latitude, longitude
	allcoordinates=[]

	latitude = str(latitude)
	dotindex = latitude.index('.')
	latitiude = latitude[0:dotindex]

	longitude = str(longitude)
	dotindex = longitude.index('.')
	longitude = longitude[0:dotindex]

	sql = """SELECT
	rowid,
	geo_name,
	geo_lat,
	geo_lng,
	geo_countrycode,
	geo_statecode,
	geo_citycode
	FROM geotable 
	WHERE geo_lat LIKE '""" + latitiude + """%'
	AND geo_lng LIKE '""" + longitude +  "%';"

	try: 
		cursor = conn.execute(sql)
		rows = cursor.fetchall()
	except sqlite3.Error as e:
	  	status = 'Error in reverse geocode: ' + str(e)
	  	return(status)
	
	for row in rows:
		geolocation.append(dict(locality=row[1], 
								country_code=row[4], 
	            				state_code=str(row[4])+'.'+str(row[5]), 
	            				city_code=str(row[4])+'.'+str(row[5])+'.'+str(row[6])
	            				)
							)
		allcoordinates.append((row[2], row[3]))

	try:
		for i in range(len(allcoordinates)):
			haversinedistancelist.append(haversine(coordinates, allcoordinates[i]))

		likelyplace = min(haversinedistancelist)
		placeindex = haversinedistancelist.index(likelyplace)

		try:
			locationlist.append(geolocation[placeindex]['locality'])
		except Exception as e:
			locationlist.append('')
		try:
			locationlist.append(admin1[geolocation[placeindex]['state_code']])
		except Exception as e:
			locationlist.append('')
		try:	
			locationlist.append(admin2[geolocation[placeindex]['city_code']])
		except Exception as e:
			locationlist.append('')
		try:
			locationlist.append(countries[geolocation[placeindex]['country_code']])
		except Exception as e:
			locationlist.append('')
	except Exception as e:
	  status = 'Error in reverse geocode: ' + str(e)
	  return(status + str(locationlist))

	return(locationlist)

def country_code():
	country_code_dictionary={}
	try:
		with open(os.path.join(LOCATION, 'countries.tsv'), 'r', encoding="utf8") as source:
			reader = csv.reader(source, delimiter='\t')
			for row in reader:
				code = row[0]
				if not '#' in code:
					name = row[4]
					country_code_dictionary[code] = name
	except FileNotFoundError:
		status = 'File not found countries.tsv'
		return(status)
	return(country_code_dictionary)

def user_cwd(LOCATIONDICT):
	global LOCATION
	try:
		LOCATION = os.path.dirname(LOCATIONDICT['__file__'])
	except KeyError:
		#LOCATION is set to home path when start_rgeocode is run from interactive shell
		LOCATION = expanduser("~") 
	
	if platform == "win32":
		LOCATION = LOCATION + '\\'
		LOCATION = LOCATION.replace('\\', '\\\\')

	if len(LOCATION) == 0:			
		LOCATION = os.getcwd()		#LOCATION is set to cwd when rgeocode.py is main
	return(LOCATION)

def filter_rgeocode(codelist):
	LOCATIONDICT = sys._getframe(1).f_globals
	LOCATION = user_cwd(LOCATIONDICT)
	country_code_dictionary = country_code()
	if country_code_dictionary == 'File not found countries.tsv':
		status = 'File not found countries.tsv'
		return(status)

	connectdatabase()
	dictionary_keys = country_code_dictionary.keys()

	for key in range(len(codelist)):
		if codelist[key] not in dictionary_keys:
			status = 'Invalid country code: ' + str(codelist[key])
			return(status)

	code="'"
	delim = "',"
	for i in range(len(codelist)):
		code = code + "'" + str(codelist[i]) + delim
	
	code = code[1:-1]

	sql="""DELETE
	FROM geotable
	WHERE geo_countrycode NOT IN (""" + code +");"
	
	try: 
		cursor = conn.execute(sql)
		conn.commit()
		conn.execute("vacuum")	#This is to reduce file size of geo.db from ~600MB
		status = 'Database filtered: '
	except sqlite3.Error as e:
		status = 'Error in filter_rgeocode delete ' + str(e)
		
	if status == 'Database filtered: ':
		sql="SELECT changes();"
		try: 
			cursor = conn.execute(sql)
			count = cursor.fetchone()
			status = status + 'Deleted ' + str(count[0]) + ' rows.'
		except sqlite3.Error as e:
		  	status = 'Error in filter_rgeocode changes() ' + str(e)
		
	cleanup()
	return(status)

def start_rgeocode(latitude, longitude):
	LOCATIONDICT = sys._getframe(1).f_globals
	LOCATION = user_cwd(LOCATIONDICT)

	if isinstance(latitude, float) and isinstance(longitude, float):
		status=do_check()
	else:
		status='Invalid data type'
		
	if 'Start reverse geocode' in status:
		if 'Error in reverse geocode: ' in status:
			return(status)
		else:
			geo_dictionary()

			locationlist=get_location(latitude, longitude)
			
			cleanup()
			return(locationlist)
	else:
		cleanup()
		return(status)
	
if __name__ == '__main__':
	latitude = 12.9751
	longitude = 77.5964
	location = start_rgeocode(latitude, longitude)
	print(location)
	
	latitude = -33.852222
	longitude = 151.210556
	location = start_rgeocode(latitude, longitude)
	print(location)

	latitude = 40.689247
	longitude = -74.044502
	location = start_rgeocode(latitude, longitude)
	print(location)

	latitude = -25.695230
	longitude = -54.436718
	location = start_rgeocode(latitude, longitude)
	print(location)