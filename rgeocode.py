import os
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

if sys.version_info[0] == 3:
	import urllib.request
elif sys.version_info[0] < 3:
	import urllib

def connectdatabase():
	global conn
	try:
		conn = sqlite3.connect(os.path.join(os.getcwd(), os.path.dirname(__file__), 'geo.db'))
	except sqlite3.Error as e:
		status='Error in reverse geocode: '+str(e)
	finally:
		if conn:
			print('Connected to geo database')

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
		status = 'geotable created'
	except sqlite3.Error as e:
		if not 'table already exists' in str(e):
			status='Error occured in creating table geotable: '+ str(e)
	return(status)

def cleanup():
	if conn is not None:
		conn.close()

	if os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'allCountries.txt')):
		os.remove('allCountries.txt')

	if os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'geonamesdata.csv')):
		os.remove('geonamesdata.csv')

	if os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'allCountries.zip')):
		os.remove('allCountries.zip')
	print('Database connection closed ...')
	print('Program finished execution.')

def downloadfile(filename, savetofile):
	global BASE_URL
	print('Downloading ' + filename + ' from geonames.org')
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
	if sys.version_info[0] < 3 and sys.version_info[1] < 5:
		status = 'Python version should be greater than 2.5'
		return(status)

	if platform == "win32":
		if not os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'sqlite3.exe')):
			status='sqlite3 not found.'
			return(status)
		else:
			connectdatabase()
	else:
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
		else:
			status = 'Start reverse geocode - geotable already exists ...'
			return(status)
	except sqlite3.Error as e:
	  	status = 'Error in reverse geocode: ' + str(e)
	  	return(status)

	if not os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'allCountries.zip')):
		status = downloadfile(FILE_ONE, 'allCountries.zip')
		if 'Error downloading file: ' in status:
			return(status)
		with zipfile.ZipFile('allCountries.zip', 'r') as z:
			z.extractall(os.path.join(os.getcwd(), os.path.dirname(__file__)))

		f=open('geonamesdata.csv', 'w', encoding='UTF-8')
		print('Preparing data ...')

		with open('allCountries.txt', 'r', encoding="utf8") as source:
			reader = csv.reader(source, delimiter='\t')
			for r in reader:
				f.write((r[2]+ '|' + r[4] + '|' + r[5] + '|' + r[8] + '|' + r[10] + '|' + r[11]+'\n'))
			f.close()

		subprocess.call(["sqlite3", "geo.db","-separator", "|" ,".import geonamesdata.csv geotable"])

		print('Populating geotable done...')
		
	if not os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'countries.tsv')):
		status = downloadfile(FILE_TWO, 'countries.tsv')
		if 'Error downloading file: ' in status:
			return(status)
	if not os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'admin1.tsv')):
		status = downloadfile(FILE_THREE, 'admin1.tsv')
		if 'Error downloading file: ' in status:
			return(status)
	if not os.path.exists(os.path.join(os.getcwd(), os.path.dirname(__file__), 'admin2.tsv')):
		status = downloadfile(FILE_FOUR, 'admin2.tsv')
		if 'Error downloading file: ' in status:
			return(status)
	status = 'Start reverse geocode'
	return(status)
        
def geo_dictionary():
	with open(os.path.join(os.getcwd(), os.path.dirname(__file__), 'countries.tsv'), 'r', encoding="utf8") as source:
		reader = csv.reader(source, delimiter='\t')
		for row in reader:
			code = row[0]
			name = row[4]
			countries[code] = name
	with open(os.path.join(os.getcwd(), os.path.dirname(__file__), 'admin1.tsv'), 'r', encoding="utf8") as source:
		reader = csv.reader(source, delimiter='\t')
		for row in reader:
			code = row[0]
			name = row[1]
			admin1[code] = name
	with open(os.path.join(os.getcwd(), os.path.dirname(__file__), 'admin2.tsv'), 'r', encoding="utf8") as source:
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
			locationlist.append(admin2[geolocation[placeindex]['city_code']])
		except Exception as e:
			locationlist.append('')
		try:
			locationlist.append(admin1[geolocation[placeindex]['state_code']])
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

def start_rgeocode(latitude, longitude):
	if isinstance(latitude, float) and isinstance(longitude, float):
		status=do_check()
	else:
		status='Function parameters should be of type<float> only'
		
	if 'Start reverse geocode' in status:
		if 'Error in reverse geocode: ' in status:
			print(status)
		else:
			geo_dictionary()

			status='Reverse geocoding (' + str(latitude) + ', ' + str(longitude) +'): '
			locationlist=get_location(latitude, longitude)
			
			print(status)
			print(locationlist)
	else:
		print(status)
	cleanup()

if __name__ == '__main__':
	latitude = 12.9751
	longitude = 77.5964
	start_rgeocode(latitude, longitude)

	latitude = -33.852222
	longitude = 151.210556
	start_rgeocode(latitude, longitude)

	latitude = 40.689247
	longitude = -74.044502
	start_rgeocode(latitude, longitude)

	latitude = -25.695230
	longitude = -54.436718
	start_rgeocode(latitude, longitude)
