#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import re
import json
import urllib.request
import xml.etree.ElementTree as ElementTree
from getpass import getpass
from time import sleep, strftime


def main():
    iterate = not (len(sys.argv) == 2 and sys.argv[1] == "show")
    app = Application(iterate)
    connection = Connection(app.username, app.password)
    courses = Courses(connection, app.courses)
    terms = Terms(connection, app.terms)
    while True:
        if not connection.checkConnection():
            app.loop()
            continue
        courses.loadCourses()
        terms.loadTerms()
        if app.newScore(terms, courses):
            app.showScore(terms, courses)
        if not app.iterate:
            break
        app.loop()


class Application:
    """Zakladni funkce aplikace. Nacteni konfiguracnich souboru,
    kontrola noveho hodnoceni, vypsani hodnoceni"""

    def __init__(self, iterate):
        self.iterate = iterate
        self.username = None
        self.password = None
        self.time = None
        self.notifyCmd = None
        self.courses = None
        self.terms = None
        self.change = ""
        self.loadConfig()

    def loadConfig(self):
        """Ze souboru 'wis.json' nacte konfiguraci aplikace. Pokud nektere z
        potrebnych polozek (login, heslo) v souboru nenalezne, bude pozadovat
        jejich rucni zadani
        """
        try:
            with open('wis.json') as configFile:
                config = json.load(configFile)
        except ValueError:
            print("⚑ Chyba v konfiguracnim souboru")
            sys.exit(4)
        except:
            config = None
            pass
        # nacteni nastaveni
        if config and 'wis' in config:
            self.username = config['wis'].get('user')
            self.password = config['wis'].get('pass')
            self.time = config['wis'].get('time', 90)
            self.notifyCmd = config['wis'].get('cmd')
        if config and 'courses' in config:
            self.courses = config.get('courses')
        if config and 'terms' in config:
            self.terms = config.get('terms')
        # rucni zadani prihlasovacich udaju, pokud nebyly nastaveny
        if self.username is None:
            self.username = input("Login: ")
        if self.password is None:
            self.password = getpass(prompt="Heslo: ", stream=None)

    def newScore(self, terms, courses):
        """Porovna stary zaznam hodnoceni s novym a v pripade zmen vypise
        informaci o novem hodnoceni
        """
        # zjisteni zmen v hodnoceni
        if not terms.oldrecord or not courses.oldrecord:
            return True  # prvni iterace, chci zobrazit hodnoceni
        if terms.oldrecord:
            terms.changes = [(old, new) for old, new in
                             zip(terms.oldrecord, terms.newrecord)
                             if new != old]
        if courses.oldrecord:
            courses.changes = [(old, new) for old, new in
                               zip(courses.oldrecord, courses.newrecord)
                               if new != old]
        # nacteni zmen
        if terms.changes or courses.changes:
            status = '✖ ' if terms.changes and not courses.changes else '✔ '
            if courses.changes:
                for old, new in courses.changes:
                    self.change += (status + old[0] + '\t' + old[1]
                                    + ' ➜ ' + new[1] + '\n')
            if terms.changes:
                for old, new in terms.changes:
                    self.change += (status + old[0] + '\t' + old[1]
                                    + ' ➜ ' + new[1] + '\t' + new[2] + '\n')
            if self.notifyCmd:
                os.system(self.notifyCmd)
            return True
        else:
            return False

    def showScore(self, terms, courses):
        """Vypise nactene hodnoceni"""
        if self.iterate:
            clear()
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
        if self.change != "":
            print('')
            print("Nove hodnoceni:\n")
            print(self.change)
        elif self.iterate:
            print('')

    def loop(self):
        """Stara se o opakovani overovani hodnoceni podle nastaveneho
        intervalu"""
        sys.stdout.write('\rPosledni aktualizace ' + strftime('%X'))
        sleep(self.time)
        sys.stdout.flush()


class Connection:
    """Trida obstarava prace vyzadujici pripojeni k internetu"""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.checkLogin()

    def checkConnection(self):
        """Kontrola pripojeni. Vraci True, pokud je dostupne pripojeni"""
        while True:
            try:
                testUrl = 'http://www.fit.vutbr.cz/'
                urllib.request.urlopen(testUrl, timeout=10)
                return True
            except:
                return False

    def websiteSource(self, url, coding):
        """Ziskani zdrojoveho HTML / XML kodu pro ziskani udaju o
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
            print("⚑ Nepodarilo se prihlasit k informacnimu systemu")
            sys.exit(1)


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
        # pokud se nepodari nacist XML
        if not source:
            print("⚑ Chyba pri nacitani XML zdroje")
            return
        root = ElementTree.fromstring(source)
        result = list()
        for entry in root.iter('course'):
            # result = pole s nactenym hodnocenim
            result.append([entry.get('abbrv'), entry.get('points')])
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
        for url in self.terms:
            source = self.connection.websiteSource(url, 'ISO-8859-2')
            # nacteni informaci z html stranky regexem
            try:
                courseName = re.search(r'<title>([A-Z0-9]{3,4})', source)
                termName = re.search(r'.*<h[2-3]>(.+)(?= - .+<)', source)
                points = re.search(r'<td align=right><b>'
                                   '([0-9]+( \(?[0-9,]+\)?)?)', source)
                self.newrecord.append([courseName.group(1), points.group(1),
                                      termName.group(1), url])
            except:
                print("⚑ Nelze nacist informace o terminu: " + url)
                self.terms.remove(url)
                continue

if __name__ == '__main__':

    sys.stdout.write("\x1b]2;VUT FIT WIS Checker\x07")

    def clear():
        """Prikaz pro vycisteni obrazu terminalu"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def signal_handler(signal, frame):
        """Pri zachyceni signalu ukonci skript"""
        print("\nBye bye...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    main()
