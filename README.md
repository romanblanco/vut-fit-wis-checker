VUT FIT WIS Checker
===================

Funkce a možnosti
-----------------
- skript stahuje aktualní hodnocení z WISu a porovnává, zda se hodnocení oproti původnímu načtení změnilo
- lze nastavit libovolný příkaz na upozornění změny hodnocení
- možnost nastavit zobrazení hodnocení konkrétních termínů
- možnost nastavení frekvence aktualizace


Konfigurace
-----------

Pro nastavení skriptu se používá soubor [wis.json](/wis.json "wis.json")

##### Sekce `"wis"`: #####

 * Přihlašovací údaje:
    + `user` — uživatelské jméno
    + `pass` — heslo k informačnímu systému

 * Funkčnost a způsob spouštění skriptu:
    + `time` — pauza mezi opětovným spuštěním při spouštění ve smyčce (v sekundách)
    + `cmd` — přikaz operačního systému, který se má použít jako notifikace

##### Sekce `"courses"` a `"terms"`: #####

 * Nastavení vypisovaných dat:
    + `course` — zkratky vypisovaných předmětů
    + `terms` — URL adresy sledovaných termínů
    
#### Ukázka konfigurace: ####
    {
      "wis": {
        "user": "xlogin00",
        "pass": "he5lonawis",
        "time": 90,
        "cmd": "aplay band.wav"
      },
      "courses": [
        "INP",
        "INM",
        "IFJ",
        "ISS"
      ],
      "terms": [
        "https://wis.fit.vutbr.cz/FIT/st/course-sl.php?id=543210&item=01234",
        "https://wis.fit.vutbr.cz/FIT/st/course-sl.php?id=012345&item=43210"
      ]
    }

Pokud některé prvky v konfiguraci chybí, nebo konfigurační soubor chybí úplně, skript se chová následovně:

- pro přihlašovací údaje bude skript vyžadovat ruční zadání (viz Ukázka spouštění)
- pro ostatní skript použije defaultní nastavení:

        time = 300
        cmd = None
        courses = [všechny předměty v aktualním ak. roce]
        term = None


Spouštění
---------

Při spuštění skriptu bez parametru, začne skript ve smyčce kontrolovat nové hodnocení, v případě změny hodnocení jej vypíše a dál pokračuje v kontrole

Při spuštění skriptu s parametrem `show` skript vypíše názvy a hodnocení (u termínů ještě jejich popis) sledovaných kurzů a termínů


Ukázka
------

Spuštění bez parametru: (ukázka zjištění nového hodnocení)

    $ ./wis.py
    IAL 0   ➜     IAL 15     Půlsemestrální zkouška
    IAL 30  ➜     IAL 45 
Spuštění s parametrem `show`

    $ ./wis.py show
    Predmety:

    IAL     0
    IFJ     10
    INM     0
    INP     10
    ISS     20

    Terminy:

    IAL     0      Půlsemestrální zkouška
    INP     10     Půlsemestrální zkouška
Spuštění bez existujícího konfiguračního souboru

    $ ./wis.py show
    Login: xlogin00
    Password:
    Predmety:
    IAL     0
    IFJ     10
    INM     0
    INP     10
    ISS     20
    IDS     0
    IPK     0
    IPP     0
    IZG     0
    IZU     0
    ICP     0
