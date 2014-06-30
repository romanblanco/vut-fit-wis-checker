#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import re
import configparser
import urllib.request
import xml.etree.ElementTree as ElementTree
from getpass import getpass
from time import sleep, ctime


def main():
    app = Application()
    connection = Connection(app.username, app.password)
    courses = Courses(connection, app.courses)
    terms = Terms(connection, app.terms)
    while True:
        connection.checkConnection()
        courses.loadCourses()
        terms.loadTerms()
        showCond = (len(sys.argv) == 2 and sys.argv[1] == "show")
        if not showCond:
            app.checkNewScore(terms, courses)
            sleep(app.time)
        else:
            app.showScore(terms, courses)
            break


class Application:
    """Zakladni funkce aplikace - nacteni konfiguracnich souboru, kontrola
    noveho hodnoceni, vypsani hodnoceni
    """

    def __init__(self):
        self.username = None
        self.password = None
        self.time = 300
        self.notifyCmd = None
        self.courses = None
        self.terms = None
        self.loadConfig()

    def loadConfig(self):
        """Ze souboru 'wis.ini' nacte konfiguraci aplikace. Pokud nektere z
        potrebnych polozek (login, heslo) v souboru nenalezne, bude pozadovat
        jejich rucni zadani
        """
        config = configparser.ConfigParser()
        try:
            config.read('wis.ini')
        except:
            sys.stderr.write("! Chyba v konfiguracnim souboru\n")
            os._exit(1)
        # nacteni nastaveni z konfiguracniho souboru
        if 'WIS' in config:
            self.username = config.get('WIS', 'user', fallback=None)
            self.password = config.get('WIS', 'pass', fallback=None)
            self.time = int(config.get('WIS', 'time', fallback=300))
            self.notifyCmd = config.get('WIS', 'cmd', fallback=None)
        if 'courses' in config:
            self.courses = config.get('courses', 'course', fallback=None)
        if self.courses is not None:
            self.courses = self.courses.split('\n')
        if 'terms' in config:
            self.terms = config.get('terms', 'term', fallback=None)
        if self.terms is not None:
            self.terms = self.terms.split('\n')
        # rucni zadani prihl. udaju pokud nebyly v konfiguracnim souboru
        if self.username is None:
            self.username = input("Login: ")
        if self.password is None:
            self.password = getpass(prompt="Password: ", stream=None)

    def checkNewScore(self, terms, courses):
        """Porovna stary zaznam hodnoceni s novym a v pripade zmen vypise
        informaci o novem hodnoceni
        """
        # zjisteni zmen v hodnoceni
        if terms.oldrecord:
            terms.changes = [(old, new) for old, new in
                             zip(terms.oldrecord, terms.newrecord)
                             if new != old]
        if courses.oldrecord:
            courses.changes = [(old, new) for old, new in
                               zip(courses.oldrecord, courses.newrecord)
                               if new != old]
        # vypsani zmen + notifikace
        if terms.changes or courses.changes:
            if terms.changes:
                # pole: [predmet] [hodnoceni] [popis]
                for old, new in terms.changes:
                    print(old[0] + ' ' + old[1] + '\t->\t' +
                          new[0] + ' ' + new[1] + '\t' + new[2])
            if courses.changes:
                # pole: [predmet] [hodnoceni]
                for old, new in courses.changes:
                    print(old[0] + ' ' + old[1] + '\t->\t' +
                          new[0] + ' ' + new[1])
            if self.notifyCmd:
                os.system(self.notifyCmd)

    def showScore(self, terms, courses):
        """Vypise nactene hodnoceni"""
        if courses.newrecord:
            print("Predmety:\n")
            for course in courses.newrecord:
                print(course[0] + '\t' + course[1])
        if courses.newrecord and terms.newrecord:
            print('')
        if terms.newrecord:
            print("Terminy:\n")
            for term in terms.newrecord:
                print(term[0] + '\t' + term[1] + '\t' + term[2])


class Connection:
    """Obstarava prace vyzadujici pripojeni k internetu"""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.checkLogin()

    def checkConnection(self):
        """Kontrola pripojeni. Vraci rizeni az ve chvili, kdy je overene
        pripojeni
        """
        while True:
            try:
                testUrl = 'http://www.fit.vutbr.cz/'
                urllib.request.urlopen(testUrl, timeout=10)
                return
            except:
                sleep(2)
                pass

    def websiteSource(self, url, coding):
        """Ziskani zdrojoveho HTML/XML kodu pro ziskani udaju o
        hodnoceni
        """
        try:
            connection = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            connection.add_password(None, url, self.username, self.password)
            handler = urllib.request.HTTPBasicAuthHandler(connection)
            opener = urllib.request.build_opener(handler)
            urllib.request.install_opener(opener)
            content = urllib.request.urlopen(url).read()
        except:
            content = None
            pass
        if content is not None:
            content = content.decode(coding)
        return content

    def checkLogin(self):
        """Overeni spravnosti prihlasovacich udaju"""
        self.checkConnection()
        testUrl = 'https://wis.fit.vutbr.cz/FIT/st/get-courses.php'
        source = self.websiteSource(testUrl, 'utf-8')
        if source is None:
            sys.stderr.write("! Nepodarilo se prihlasit k WISu\n")
            os._exit(2)


class Courses:
    """Nacteni informaci o kurzech"""

    def __init__(self, connection, courses):
        self.oldrecord = None
        self.newrecord = None
        self.changes = None
        self.connection = connection
        self.courses = courses

    def loadCourses(self):
        """Uchovani predchoziho hodnoceni kurzu (pokud existuje) a nacteni
        noveho
        """
        url = 'https://wis.fit.vutbr.cz/FIT/st/get-courses.php'
        source = self.connection.websiteSource(url, 'utf-8')
        try:
            root = ElementTree.fromstring(source)
            result = list()
            for entry in root.iter('course'):
                # result = pole s nactenym hodnocenim
                result.append([entry.get('abbrv'), entry.get('points')])
        except:
            sys.stderr.write("! Chyba pri nacitani XML zdroje\n")
            os._exit(3)
        # poznamenani stareho hodnoceni a nacteni noveho
        self.oldrecord = self.newrecord
        if self.courses is None:
            self.newrecord = [item for item in result]
        else:
            self.newrecord = [item for item in result if item[0]
                              in self.courses]


class Terms:
    """Nacteni informaci o terminech"""

    def __init__(self, connection, terms):
        self.oldrecord = None
        self.newrecord = list()
        self.changes = None
        self.connection = connection
        self.terms = terms

    def loadTerms(self):
        """Uchovani predchoziho hodnoceni terminu (pokud existuje) a nacteni
        noveho
        """
        if not self.terms:
            return
        # poznamenani stareho hodnoceni a nacteni noveho
        self.oldrecord = self.newrecord
        self.newrecord = list()
        for url in self.terms[:]:
            source = self.connection.websiteSource(url, 'ISO-8859-2')
            # nacteni informaci z html stranky regexem
            try:
                courseName = re.search(r'<title>([A-Z0-9]{3,4})', source)
                termName = re.search(r'.*<h[2-3]>(.+)(?= - .+<)', source)
                points = re.search(r'<td align=right><b>'
                                   '([0-9]+( \(?[0-9]+\)?)?)', source)
                self.newrecord.append([courseName.group(1), points.group(1),
                                      termName.group(1), url])
            except:
                sys.stderr.write("! Nelze nacist informace o terminu: " +
                                 url + "\n")
                self.terms.remove(url)
                continue

if __name__ == '__main__':

    def signal_handler(signal, frame):
        """Pri zachyceni signalu ukonci skript"""
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    main()
