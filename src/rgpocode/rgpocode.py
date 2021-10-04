import os
from os.path import expanduser
import csv
import sys
from sys import platform
import sqlite3
import zipfile
import subprocess

#countries = {}
conn = None
BASE_URL = 'http://download.geonames.org/export/'
FILE_ONE = 'allCountries'

if sys.version_info[0] == 3:
	import urllib.request
elif sys.version_info[0] < 3:
	import urllib
	
def connectdatabase():
	global conn
	global LOCATION
	try:
		conn = sqlite3.connect(os.path.join(LOCATION, 'gpo.db'))
	except sqlite3.Error as e:
		status='Error in postalcode: '+str(e)

def creategpotable():
	try:
		sql ="""CREATE TABLE gpotable(
        gpo_countrycode TEXT NOT NULL,
        gpo_postalcode TEXT NOT NULL,
        gpo_placename TEXT NOT NULL,
        gpo_admin1 TEXT,
        gpo_admin2 TEXT,
        gpo_admin3 TEXT,
        gpo_latitude REAL NOT NULL,
        gpo_longitude REAL NOT NULL
        )"""
		cursor = conn.cursor()
		cursor.execute(sql)
	except sqlite3.Error as e:
		if not 'table already exists' in str(e):
			status='Error occured in creating table gpotable: '+ str(e)
	
	print(status)
	return(status)


def cleanup():
	global LOCATION
	global FILE_ONE
	if conn is not None:
		conn.close()

	if os.path.exists(os.path.join(LOCATION, FILE_ONE+'.zip')):
		os.remove(os.path.join(LOCATION, FILE_ONE+'.zip'))

	if os.path.exists(os.path.join(LOCATION, FILE_ONE+'.txt')):
		os.remove(os.path.join(LOCATION, FILE_ONE+'.txt'))

	if os.path.exists(os.path.join(LOCATION, 'gponamesdata.csv')):
		os.remove(os.path.join(LOCATION, 'gponamesdata.csv'))

	if os.path.exists(os.path.join(LOCATION, 'readme.txt')):
		os.remove(os.path.join(LOCATION, 'readme.txt'))

	
def downloadfile(filename, savetofile):
	global BASE_URL
	global LOCATION
	savetofile = os.path.join(LOCATION, savetofile)
	fileurl = BASE_URL + filename
	print(BASE_URL + filename)
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
	global FILE_ONE
	downloadflag = 0
	if sys.version_info[0] < 3 and sys.version_info[1] < 5:
		status = 'Python version should be greater than 2.5'
		return(status)

	if platform == "win32":
		if not os.path.exists(os.path.join(LOCATION, 'sqlite3.exe')):
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
	NAME = 'gpotable';
	"""
	try:    
		cursor = conn.execute(sql)
		row = cursor.fetchone()
		if row is None:
			creategpotable()
			downloadflag = 1
		else:
			status = 'Start reverse postalcode - gpotable and file already exist ...'
	except sqlite3.Error as e:
	  	status = 'Error in reverse postalcode: ' + str(e)
	  	return(status)


	if downloadflag == 1:
		status = downloadfile('zip/'+FILE_ONE+'.zip', FILE_ONE+'.zip')
		if 'Error downloading file: ' in status:
			return(status)
		with zipfile.ZipFile(os.path.join(LOCATION, FILE_ONE+'.zip'), 'r') as z:
			z.extractall(LOCATION)

		f=open(os.path.join(LOCATION, 'gponamesdata.csv'), 'w', encoding='UTF-8')

		with open(os.path.join(LOCATION, FILE_ONE + '.txt'), 'r', encoding="utf8") as source:
			reader = csv.reader(source, delimiter='\t')
			for r in reader:
				f.write((r[0]+ '|' + r[1] + '|' + r[2] + '|' + r[3] + '|' + r[5] + '|' + r[7]+ '|' + r[9] + '|' + r[10] + '\n'))
			f.close()

		#Enclosing location of geonamesdata.csv file in quotes allows for spaces in file path
		NL = '"' + LOCATION + "gponamesdata.csv" +'"' 
		
		subprocess.call([
		os.path.join(LOCATION, "sqlite3"), 
		os.path.join(LOCATION, "gpo.db"), 
		"-separator", "|" ,
		".import "+ NL + " gpotable"
		])

	status = 'Start reverse postalcode'
	return(status)


def get_location(userinput):
	global conn
	locationlist=[]
	geolocation = []
		
	sql = """SELECT
	rowid,
	gpo_countrycode,
	gpo_placename,
	gpo_admin1,
	gpo_admin2,
	gpo_admin3
	FROM gpotable 
	WHERE gpo_postalcode = '""" + str(userinput) + "';"

	try: 
		cursor = conn.execute(sql)
		rows = cursor.fetchall()
	except sqlite3.Error as e:
	  	status = 'Error in reverse postalcode: ' + str(e)
	  	return(status)
	
	for row in rows:
		geolocation.append(dict(place_name=row[2],
								admin1=row[3],
								admin2=row[4],
								admin3=row[5],
								country_code=row[1]
	            				)
							)
	return(geolocation)
	

def start_rgpocode(userinput):
	global LOCATION
	LOCATIONDICT = sys._getframe(1).f_globals
	try:
		LOCATION = os.path.dirname(LOCATIONDICT['__file__'])
	except KeyError:
		LOCATION = expanduser("~")
	
	if platform == "win32":
		LOCATION = LOCATION + '\\'
		LOCATION = LOCATION.replace('\\', '\\\\')
	
	status=do_check()
		
	if 'Start reverse postalcode' in status:
		if 'Error in reverse postalcode: ' in status:
			return(status)
		else:
			locationlist=get_location(userinput)
			
			cleanup()
			return(locationlist)
	else:
		cleanup()
		return(status)
	

if __name__ == '__main__':
	location = start_rgpocode('N5V')
	print(location)
