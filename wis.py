#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
VUT FIT WIS Checker
https://github.com/romanblanco/vut-fit-wis-checker

@author:   Roman Blanco
@contact:  roman.blanco92@gmail.com
@license:  GNU GPL v3
'''

import os
import sys
import platform
import signal
import re
import urllib.request
import configparser
import xml.etree.ElementTree as ElementTree
from time import localtime, strftime, sleep
from getpass import getpass

class Application:

	def __init__(self):
		""" Postupne spousti metody """

		self.config()

		while True:

			if self.connection():
				if self._courseNames: self.courses()
				if self._termURLs: self.terms()
				if self._checkUpdate: self.checkNewValuation()
				if (os.path.isfile("NOVE.log")): self.printNewValuation()

			if self._loop:
				print("\nAktualizovano: " + strftime("%H:%M:%S", localtime()))

				try: self._loopTime
				except: self._loopTime = 300
				for i in range (self._loopTime, 0, -1):
					sys.stdout.write('\rNasledujici aktualizace: %d ' %i)
					sys.stdout.flush()
					sleep(1)

				if (platform.system() == 'Windows'):
					os.system('cls')
				else:
					os.system('clear')

			else:
				os._exit(0)


	def config(self):
		""" Nacte konfiguraci ze souboru wis.ini, podle konfugurace se 
		nasledne spousti funkce skriptu """

		config = configparser.ConfigParser()
		config.read('wis.ini')

		#============== UZIVATELSKE JMENO ===============
		try: self._username = config['WIS']['user']
		except:	self._username = input("Login: ")
		#============== UZIVATELSKE HESLO ===============
		try: self._password = config['WIS']['pass']
		except: self._password = getpass(prompt="Password: ", stream=None)

		#============== KONTROLA AKTUALIACI =============
		try: 
			if config['WIS']['check'] == 'True':
				self._checkUpdate = True
			else:
				self._checkUpdate = False
		except:	self._checkUpdate = True

		#============== OPAKOVANI =======================
		try: 
			if config['WIS']['loop'] == 'True':
				self._loop = True
			else:
				self._loop = False
		except: self._loop = True

		#============== OPAKOVANI =======================
		try: self._loopTime = int(config['WIS']['time'])
		except:	self._loopTime = 300

		#============== NOTIFIKACE PRI ZMENE ============
		try: self._notifyCMD = config['WIS']['cmd']
		except:	self._notifyCMD = ""

		#============== ZOBRAZOVANE KURZY ===============
		self._courseNames = []
		try:
			for course in config['courses']:
				self._courseNames.append(config['courses'][course])
		except:
			self._courseNames = input("Checked courses: ").split(' ')
		self._courseNames = [c for c in self._courseNames if c != '']

		#============== ZOBRAZOVANE TERMINY =============
		self._termURLs = []
		try:
			for term in config['terms']:
					self._termURLs.append(config['terms'][term])
		except:
			pass
		self._termURLs = [url for url in self._termURLs if url != '']

	def connection(self):
		""" Overeni pripojeni k serveru

		return False: nelze se pripojit
		return True: lze ze pripojit """

		try:
			urllib.request.urlopen('http://www.fit.vutbr.cz/')
			return True
		except:
			print("! Nelze se pripojit na skolni server")
			return False


	def websiteSource(self, url):
		""" Ziskani zdrojoveho HTML / XML kodu pro ziskani udaju o
		hodnoceni

		parametr url: odkaz na stranku jejiz zdrojovy kod se ma vratit
		return content: Vraci zdrojovy kod stranky (nedekodovany) """

		try:
			connection = urllib.request.HTTPPasswordMgrWithDefaultRealm()
			connection.add_password(None, url, self._username, self._password)

			handler = urllib.request.HTTPBasicAuthHandler(connection)
			opener = urllib.request.build_opener(handler)
			urllib.request.install_opener(opener)

			content = urllib.request.urlopen(url).read()
		except:
			print("! Nelze nacist zdroj stranky")
			print("! Pravdepodobne byly spatne zadany prihlasovaci udaje")
			content = None

		return content


	def courses(self):
		""" Ziska hodnoceni kurzu z WISu (XML), vytiskne a ulozi do promenne
		pro zapsani do souboru """

		url = 'https://wis.fit.vutbr.cz/FIT/st/get-courses.php'
		source = self.websiteSource(url)
		if source is None:
			self.loopOrExit(1)
		source = source.decode('utf-8')

		try:
			root = ElementTree.fromstring(source)
			result = list()

			# Vyhledani prvku 'abbrv' a 'points' v XML kodu
			for entry in root.iter('course'):
				result.append([entry.get('abbrv'), int(entry.get('points'))])
				# result = pole s nactenym hodnocenim
		except:
			print("! Problem nacteni XML")
			self.loopOrExit(1)

		# item[0] = zkratka predmetu podle niz se tridi vypisovane data
		courses = [ item for item in result if item[0] in self._courseNames]

		print("Predmety:\n")

		courseValuations = ""
		for course in courses:
			courseValuations += course[0] + "\t" + str(course[1]) + "\n"
			# course[0] = zkratka predmetu
			# course[1] = hodnoceni predmetu
		print(courseValuations)

		# zapsani zaznamu do souboru kvuli porovnani
		try:
			if self._checkUpdate:
				self.newLogFile(courseValuations)
		except:
			# V pripade ze neni nastavena promenna checkUpdate
			pass


	def terms(self):
		""" Nacte a vytiskne hodnoceni konkretnich terminu """

		print("Terminy:\n")
		for url in self._termURLs:
			source = self.websiteSource(url)
			if source is None:
				self.loopOrExit(1)
			source = source.decode('ISO-8859-2')

			courseName = re.search(r'<title>(.{3,4})', source)
			points = re.search(
			 r'<td align=right><b>([0-9]+( \(?[0-9]+\)?)?)', source)
			termName = re.search(r'.*<h[2-3]>(.+)(?= - .+<)', source)

			print(
			 courseName.group(1) + '\t' +
			 points.group(1) + '\t' +
			 termName.group(1)
			)


	def logFile(self):
		""" Overeni existence souboru s predeslym zaznamem hodnoceni

		return False: soubor neexistuje, nelze porovnavat aktualizace
		return True: soubor existuje, lze porovnavat aktualizace """

		if (os.path.isfile('wis.log')):
			return True
		else:
			print(
			 "* Nenalezen soubor s predeslym zaznamem hodnoceni\n"
			 "* Kontrola aktualizace probehne az pri dalsim spusteni"
			)
			return False


	def newLogFile(self, courseValuations):
		""" Zapise do souboru nactene hodnoceni pro pozdejsi
		porovnavani novych zmen v hodnoceni

		parametr courseValuations: retezec obsahujici hodnoceni ktere
		ma byt zapsano do noveho souboru """

		if not self.logFile():
			# neexistuje soubor s predeslym zaznamem hodnoceni
			with open('wis.log', 'w') as newLogFile:
				newLogFile.write(courseValuations)
			newLogFile.close
			# neni s cim porovnavat zmeny hodnoceni
			self.loopOrExit(0)
		else:
			# zapsani zaznamu ktery bude porovnavan s predeslym
			with open('wis.new.log', 'w') as newLogFile:
				newLogFile.write(courseValuations)
			newLogFile.close


	def checkNewValuation(self):
		""" Porovna soubor s puvodnim a nove nactenym hodnocenim a v
		pripade rozdilu vytvori novy soubor """

		try:
			with open('wis.log') as old, open('wis.new.log') as new:
				oldValues = old.readlines()
				newValues = new.readlines()
		except:
			print("\n! Soubor se zaznamem je prazdny")
			print("\n! Chyba je zpusobena nevyplnenim kurzu")
			self.loopOrExit(1)

		changes = ""
		if len(newValues) == len(oldValues):
			for line in range(len(newValues)):
				if newValues[line] != oldValues[line]:
					changes += newValues[line]
		else:
			print(
			 "\n* Probehla zmena konfigurace\n"
			 "* Kontrola aktualizace probehne pri pristim spusteni"
			)

		old.close
		new.close

		if changes != "":
			with open('NOVE.log', 'a') as newValFile:
				newValFile.write(changes)
			newValFile.close
			self.notification()

		os.remove('wis.log')
		os.rename('wis.new.log', 'wis.log')


	def printNewValuation(self):
		""" Pokud existuje soubor s novym hodnocenim, vypise jej """

		with open('NOVE.log', 'r') as newValuation:
			content = newValuation.read()
			print("\nNove hodnoceni:\n\n" + content)
		newValuation.close


	def notification(self):
		try: os.system(self._notifyCMD)
		except: pass


	def loopOrExit(self, exitValue):
		""" Vhledem ke konfiguraci rozhodne, jestli se skript znovu
		spusti, nebo ukonci. Pokud je nastavene spousteni ve smycce,
		zavola metodu __init__(), jinak se ukonci s hodnotou poslanou v
		parametru

		parametr exitValue: navratova hodnota pri ukonceni """

		try:
			if self._loop:
				print("\nAktualizovano: " + strftime("%H:%M:%S", localtime()))

				try:
					for i in range (self._loopTime, 0, -1):
						sys.stdout.write('\rNasledujici aktualizace: %d ' %i)
						sys.stdout.flush()
						sleep(1)
				except:
					for i in range (300, 0, -1):
						sys.stdout.write('\rNasledujici aktualizace: %d ' %i)
						sys.stdout.flush()
						sleep(1)

				if (platform.system() == 'Windows'):
					os.system('cls')
				else:
					os.system('clear')
				self.__init__()
			else:
				os._exit(exitValue)
		except:
			os._exit(exitValue)


	def signal_handler(signal, frame):
		""" Pri zachyceni signalu ukonci skript """
		os._exit(0)

	signal.signal(signal.SIGINT, signal_handler)


if __name__ == '__main__':
	# ========================================================
	# uzitecne pri spousteni skriptu ze slozky pridane v $PATH
	# -> pro ukladani docasnych souboru do slozky ~/tmp
	# home = os.path.expanduser("~")
	# os.chdir(home + "/tmp")
	# ========================================================

	app = Application()
