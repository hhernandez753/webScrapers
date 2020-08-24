from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
import json
from bs4 import BeautifulSoup
import os
import threading
from datetime import datetime
import time

baseDir = os.path.dirname(os.path.abspath(__file__)) + os.sep
appCfg = json.loads(open(baseDir + 'cfg/app_config.json').read())
URL = appCfg["url"]
DBFILE = "{}/db/{}".format(baseDir, appCfg["dbFile"])
SCRAPERS = {}
StopEvent = threading.Event()

if not os.path.isfile(DBFILE):
    dbConn = sqlite3.connect(DBFILE)
    dbCursor = dbConn.cursor()
    sql = (
        "CREATE TABLE scrapers (" +
        "id INTEGER PRIMARY KEY," +
        "created_at TEXT NOT NULL," +
        "currency TEXT NOT NULL," +
        "frequency INTEGER NOT NULL" +
        ")"
    )
    dbCursor.execute(sql)
    dbConn.commit()

class WebScraper(threading.Thread):
    _scraperId = None
    _coinName = None
    _scraperStart = None
    _scraperLastUpdate = None
    _scraperFrequency = None
    _scraperPrice = None
    _scraperURL = None
    _dbConn = None
    _dbCursor = None
    _RELEASE = None
    _stopEvent = None

    def __init__(self, cfg=None, stopEvent=None):
        if isinstance(cfg, dict) and isinstance(stopEvent, threading.Event):
            if ("coin" in cfg.keys()) and ("frequency" in cfg.keys()) and ("url" in cfg.keys()) and ("db" in cfg.keys()):
                self._coinName = cfg["coin"]
                self._scraperStart = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._scraperLastUpdate = self._scraperStart
                self._scraperFrequency = cfg["frequency"]
                self._scraperURL = cfg["url"]
                self._scraperPrice = self._getCoinPrice()

                self._dbConn = sqlite3.connect(cfg["db"])
                self._dbConn.row_factory = sqlite3.Row
                self._dbCursor = self._dbConn.cursor()

                self._stopEvent = stopEvent

                self._scraperId = self._getScraperId()
                if self._scraperId is None:
                    self._createScraper()
                    self._scraperId = self._getScraperId()

                threading.Thread.__init__(
                    self,
                    name="Web Scraper {}".format(self._coinName),
                    daemon=True
                )
            else:
                self._RELEASE = True
        else:
            self._RELEASE = True

    def run(self):
        if isinstance(self._stopEvent, threading.Event) and not self._RELEASE:
            print("{}: {} started (PID = {})".format(
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.name,
                self.ident
            ))
            print("    Currency: {}".format(self._coinName))
            print("    Current price: {}".format(self._scraperPrice))

            lastTime = time.time()
            while True:
                currentTime = time.time()
                if self._stopEvent.is_set() or self._RELEASE:
                    print("{}: {} stopped".format(
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        self.name
                    ))
                    break

                if int(currentTime - lastTime) >= self._scraperFrequency:
                    lastTime = currentTime
                    lastPrice = self._scraperPrice
                    self._scraperPrice = self._getCoinPrice()
                    self._scraperLastUpdate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    print("{}: {} updated".format(
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        self.name
                    ))
                    print("    Last price: {}".format(lastPrice))
                    print("    Current price: {}".format(self._scraperPrice))

    def terminate(self):
        self._RELEASE = True

    def setScraperFrequency(self, frequency=None):
        if isinstance(frequency, int) and frequency > 0 and frequency <= 30:
            self._scraperFrequency = frequency
            self._updateScraperFrequency()
            print("{}: {} frequency updated to {} seconds".format(
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.name, frequency
            ))

    def getScrapertData(self):
        return {
            "id": self._scraperId,
            "coin": self._coinName,
            "price": self._scraperPrice,
            "start": self._scraperStart,
            "lastUpdate": self._scraperLastUpdate,
            "frequency": self._scraperFrequency
        }

    def _createScraper(self):
        if (not self._coinName is None) and (not self._scraperStart is None) and (not self._scraperFrequency is None):
            sql = (
                "INSERT INTO scrapers(created_at,currency,frequency) " +
                "VALUES('{}', '{}', '{}')".format(
                    self._scraperStart,
                    self._coinName,
                    self._scraperFrequency
                )
            )

            self._dbCursor.execute(sql)
            self._dbConn.commit()

    def _updateScraperFrequency(self):
        if (not self._scraperId is None):
            sql = (
                "UPDATE scrapers " +
                "SET frequency={} ".format(self._scraperFrequency) +
                "WHERE id = {}".format(self._scraperId)
            )
            self._dbCursor.execute(sql)
            self._dbConn.commit()

    def _getScraperId(self):
        scraperId = None
        if not self._coinName is None:
            sql = (
                "SELECT * " +
                "FROM scrapers " +
                "WHERE currency LIKE '{}'".format(self._coinName)
            )

            self._dbCursor.execute(sql)
            result = self._dbCursor.fetchall()
            if len(result) > 0:
                scraperId = result[0]["id"]

        return scraperId

    def _getCoinPrice(self):
        price = 0.0
        page = requests.get(self._scraperURL, timeout=30)
        if page.status_code == 200:
            soup = BeautifulSoup(page.text, "html.parser")
            for row in soup.find_all(class_='cmc-table-row'):
                col = row.find_all('td')
                if col[1].text == self._coinName:
                    price = float(col[3].text.replace("$", "").replace(",", ""))
                    break

        return price

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scraper-add', methods=['GET'])
def scraperAdd():
    requestData = json.loads(request.args.get("q"))

    response = {
        "cod": 400,
        "mssg": "Invalid request",
        "data": None
    }
    try:
        if isinstance(requestData, dict):
            if "coin" in requestData.keys() and "frequency" in requestData.keys():
                if not requestData["coin"] in SCRAPERS.keys():
                    if requestData["frequency"] > 0 and requestData["frequency"] <= 30:
                        scraper = WebScraper(
                            cfg={
                                "coin": requestData["coin"],
                                "frequency": requestData["frequency"],
                                "url": URL,
                                "db": DBFILE
                            },
                            stopEvent=StopEvent
                        )
                        scraper.start()
                        SCRAPERS[requestData["coin"]] = scraper
                        data = scraper.getScrapertData()

                        response = {
                            "cod": 200,
                            "mssg": "Scraper {} created successfully".format(requestData["coin"]),
                            "data": data
                        }
                    else:
                        response = {
                            "cod": 403,
                            "mssg": "Frequency for Scraper invalid ({})".format(requestData["frequency"]),
                            "data": None
                        }
                else:
                    response = {
                        "cod": 402,
                        "mssg": "Scraper {} already exists".format(requestData["coin"]),
                        "data": None
                    }
    except Exception as e:
        response = {
            "cod": 401,
            "mssg": "An error occurred with the request ({})".format(e.args[0]),
            "data": None
        }

    response = jsonify(response)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/scraper-remove', methods=['GET'])
def scraperRemove():
    requestData = json.loads(request.args.get("q"))

    response = {
        "cod": 400,
        "mssg": "Invalid request"
    }
    try:
        if isinstance(requestData, dict):
            if "coin" in requestData.keys():
                if requestData["coin"] in SCRAPERS.keys():
                    scraper = SCRAPERS[requestData["coin"]]
                    scraper.terminate()
                    scraper.join()
                    SCRAPERS.pop(requestData["coin"])

                    response = {
                        "cod": 200,
                        "mssg": "Scraper {} removed".format(requestData["coin"])
                    }
                else:
                    response = {
                        "cod": 402,
                        "mssg": "Scraper {} does not exists".format(requestData["coin"])
                    }
    except Exception as e:
        response = {
            "cod": 401,
            "mssg": "An error occurred with the request {}".format(e.args[0])
        }

    response = jsonify(response)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/scraper-data', methods=['GET'])
def scraperData():
    requestData = json.loads(request.args.get("q"))

    response = {
        "cod": 400,
        "mssg": "Invalid request",
        "data": []
    }
    try:
        if isinstance(requestData, dict):
            if "coin" in requestData.keys():
                scrapersData = []
                if requestData["coin"] in ["ALL"] + list(SCRAPERS.keys()):
                    if requestData["coin"] == "ALL":
                        for coin in SCRAPERS.keys():
                            scraper = SCRAPERS[coin]
                            scrapersData.append(scraper.getScrapertData())
                    else:
                        scraper = SCRAPERS[requestData["coin"]]
                        scrapersData.append(scraper.getScrapertData())

                    response = {
                        "cod": 200,
                        "mssg": "Successful request (Scraper: {})".format(requestData["coin"]),
                        "data": scrapersData
                    }
                else:
                    response = {
                        "cod": 402,
                        "mssg": "Scraper {} does not exists".format(requestData["coin"]),
                        "data": []
                    }
    except Exception as e:
        response = {
            "cod": 401,
            "mssg": "An error occurred with the request {}".format(e.args[0]),
            "data": []
        }

    response = jsonify(response)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/scraper-update', methods=['GET'])
def scraperUpdate():
    requestData = json.loads(request.args.get("q"))

    response = {
        "cod": 400,
        "mssg": "Invalid request"
    }
    try:
        if isinstance(requestData, dict):
            if "coin" in requestData.keys() and "frequency" in requestData.keys():
                if requestData["coin"] in SCRAPERS.keys():
                    if requestData["frequency"] > 0 and requestData["frequency"] <= 30:
                        scraper = SCRAPERS[requestData["coin"]]
                        scraper.setScraperFrequency(requestData["frequency"])

                        response = {
                            "cod": 200,
                            "mssg": "Scraper {} frequency updated to {} seconds".format(
                                requestData["coin"],
                                requestData["frequency"]
                            )
                        }
                    else:
                        response = {
                            "cod": 403,
                            "mssg": "Frequency for Scraper invalid ({})".format(requestData["frequency"])
                        }
                else:
                    response = {
                        "cod": 402,
                        "mssg": "Scraper {} does not exists".format(requestData["coin"])
                    }
    except Exception as e:
        response = {
            "cod": 401,
            "mssg": "An error occurred with the request {}".format(e.args[0])
        }

    response = jsonify(response)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=False)

    StopEvent.set()
    for coin in SCRAPERS.keys():
        scraper = SCRAPERS[coin]
        scraper.join()
