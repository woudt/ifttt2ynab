# pylint: disable=bare-except,global-statement

"""
Main module serving the pages for the bunq2IFTTT appengine app
"""

import base64
import hashlib
import json
import secrets
import traceback
import uuid

import arrow
import requests

from flask import Flask, redirect, render_template, request, make_response
from google.cloud import datastore

# pylint: disable=invalid-name
app = Flask(__name__)
# pylint: enable=invalid-name

DSCLIENT = datastore.Client()

IFTTT_SERVICE_KEY = None
YNAB_ACCOUNT_KEY = None
WEB_SESSION_KEY = None

YNAB_BASE = "https://api.youneedabudget.com/v1"


###############################################################################
# IFTTT interfacing methods                                                   #
###############################################################################

@app.route("/ifttt/v1/status")
def ifttt_status():
    """ Status endpoint for IFTTT platform endpoint tests """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    return ""

@app.route("/ifttt/v1/test/setup", methods=["POST"])
def ifttt_test_setup():
    """ Testdata endpoint for IFTTT platform endpoint tests """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    return json.dumps({
        "data": {
            "samples": {
                "actions": {
                    "ynab_create": {
                        "budget": "TEST#TEST#1",
                        "account": "x",
                        "date": "x",
                        "amount": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                        "import_id" : "x",
                    }
                },
                "actionRecordSkipping": {
                    "ynab_create": {
                        "budget": "TEST#TEST#2",
                        "account": "x",
                        "date": "x",
                        "amount": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                        "import_id" : "x",
                    }
                }
            }
        }
    })

@app.route("/ifttt/v1/actions/ynab_create/fields/budget/options",
           methods=["POST"])
def ifttt_budget_options():
    """ Option values for the budget field """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    try:
        r = requests.get(YNAB_BASE + "/budgets", \
            headers={"Authorization": "Bearer {}".format(get_ynab_key())})
        budgets = r.json()["data"]["budgets"]
        budgets = sorted(budgets, key=lambda x: x["last_modified_on"],
                         reverse=True)
        data = []
        for b in budgets:
            data.append({"label": b["name"], "value": b["id"]})
        return json.dumps({"data": data})
    except:
        traceback.print_exc()
        return json.dumps({"data": [{"name": "ERROR retrieving YNAB data",
                                     "value": ""}]})

@app.route("/ifttt/v1/actions/ynab_create", methods=["POST"])
def ifttt_create_action():
    """ Main endpoint to create a transaction in YNAB """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[create_action] ERROR: invalid service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    data = request.get_json()
    if "actionFields" not in data:
        print("[create_action] ERROR: missing actionFields")
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: actionFields missing"}]}), 400
    fields = data["actionFields"]
    for x in ["budget", "account", "date", "amount", "payee", "category",
              "memo", "cleared", "approved", "flag_color", "import_id"]:
        if x not in fields:
            print("[create_action] ERROR: missing field: "+x)
            return json.dumps({"errors": [{"status": "SKIP", \
                "message": "Invalid data: missing field: "+x}]}), 400

    budget = fields["budget"]
    if budget == "TEST#TEST#1":
        return json.dumps({"data": [{"id": uuid.uuid4().hex}]})
    if budget == "TEST#TEST#2":
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Test"}]}), 400
    if len(str(budget)) != 36:
        print("[create_action] ERROR: incorrect budget (no uuid): "+budget)
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: incorrect budget: "+budget}]}), 400

    account = fields["account"]
    r = requests.get(YNAB_BASE + "/budgets/{}/accounts".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())})
    results = r.json()["data"]["accounts"]
    account_id = None
    for a in results:
        if a["name"] == account:
            account_id = a["id"]
    if account_id is None:
        print("[create_action] ERROR: account not found")
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Account not found"}]}), 400

    category = fields["category"]
    category_id = None
    if category != "":
        r = requests.get(YNAB_BASE + "/budgets/{}/categories".format(budget), \
            headers={"Authorization": "Bearer {}".format(get_ynab_key())})
        results = r.json()["data"]["category_groups"]
        for g in results:
            for c in g["categories"]:
                if c["name"] == category:
                    category_id = c["id"]
        if category_id is None:
            print("[create_action] WARNING: category not found, ignoring")

    try:
        date = arrow.get(fields["date"]).format("YYYY-MM-DD")
    except:
        print("[create_action] ERROR: invalid date: "+fields["date"])
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Invalid date"}]}), 400

    try:
        amount = int(float(fields["amount"])*1000)
    except:
        print("[create_action] ERROR: invalid amount: "+fields["amount"])
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Invalid amount"}]}), 400

    body = {"transaction": {
        "account_id": account_id,
        "date": date,
        "amount": amount,
    }}
    if fields["payee"] != "":
        body["transaction"]["payee_name"] = fields["payee"][:50]
    if category_id is not None:
        body["transaction"]["category_id"] = category_id
    if fields["memo"] != "":
        body["transaction"]["memo"] = fields["memo"][:200]
    if fields["cleared"] != "":
        body["transaction"]["cleared"] = fields["cleared"]
    if fields["approved"] == "true":
        body["transaction"]["approved"] = True
    else:
        body["transaction"]["approved"] = False
    if fields["flag_color"] not in ["", "none"]:
        body["transaction"]["flag_color"] = fields["flag_color"]
    if fields["import_id"] != "":
        body["transaction"]["import_id"] = fields["import_id"]

    print(json.dumps(body))
    r = requests.post(YNAB_BASE + "/budgets/{}/transactions".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())}, \
        json=body)
    print(r.status_code, r.text)
    if r.status_code > 299:
        try:
            msg = "{} Bad request".format(r.status_code)
            msg = r.json()["error"]["detail"]
        except:
            pass
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": msg}]}), 400

    return json.dumps({"data": [{"id": uuid.uuid4().hex}]})


###############################################################################
# Config storage/caching                                                      #
###############################################################################

def get_ifttt_key():
    """ Returns the IFTTT service key """
    global IFTTT_SERVICE_KEY
    try:
        if IFTTT_SERVICE_KEY is None:
            key = DSCLIENT.key("config", "ifttt_key")
            entity = DSCLIENT.get(key)
            if entity is not None:
                IFTTT_SERVICE_KEY = entity["value"]
    except:
        traceback.print_exc()
    return IFTTT_SERVICE_KEY

def get_ynab_key():
    """ Returns the YNAB personal access token """
    global YNAB_ACCOUNT_KEY
    try:
        if YNAB_ACCOUNT_KEY is None:
            key = DSCLIENT.key("config", "ynab_key")
            entity = DSCLIENT.get(key)
            if entity is not None:
                YNAB_ACCOUNT_KEY = entity["value"]
    except:
        traceback.print_exc()
    return YNAB_ACCOUNT_KEY

def get_session_key():
    """ Returns the web interface session key """
    global WEB_SESSION_KEY
    try:
        if WEB_SESSION_KEY is None:
            key = DSCLIENT.key("config", "session_key")
            entity = DSCLIENT.get(key)
            if entity is not None:
                WEB_SESSION_KEY = entity["value"]
    except:
        traceback.print_exc()
    return WEB_SESSION_KEY

def new_session_key():
    """ Generate a new web interface session key """
    global WEB_SESSION_KEY
    try:
        WEB_SESSION_KEY = secrets.token_urlsafe(32)

        entity = datastore.Entity(DSCLIENT.key("config", "session_key"))
        entity["value"] = WEB_SESSION_KEY
        DSCLIENT.put(entity)
    except:
        traceback.print_exc()

    return WEB_SESSION_KEY

###############################################################################
# Web interface methods                                                       #
###############################################################################

@app.route("/")
def home_get():
    """ Endpoint for the homepage """
    cookie = request.cookies.get('session')
    if cookie is None or cookie != get_session_key():
        return render_template("start.html")
    iftttkeyset = (get_ifttt_key() is not None)
    ynabkeyset = (get_ynab_key() is not None)
    return render_template("main.html",\
        iftttkeyset=iftttkeyset, ynabkeyset=ynabkeyset)

@app.route("/login", methods=["POST"])
def user_login():
    """ Endpoint for login password submission """
    try:
        hashfunc = hashlib.sha256()
        hashfunc.update(request.form["password"].encode("utf-8"))

        stored_hash = DSCLIENT.get(DSCLIENT.key("config", "password_hash"))
        if stored_hash is not None:
            salt = DSCLIENT.get(DSCLIENT.key("config", "password_salt"))
            hashfunc.update(salt["value"].encode('ascii'))
            calc_hash = base64.b64encode(hashfunc.digest()).decode('ascii')
            if calc_hash != stored_hash["value"]:
                return render_template("message.html", msgtype="danger", msg=\
                    'Invalid password! - To try again, '\
                    '<a href="/">click here</a>')
        else:
            # first time login, so store the password
            salt = secrets.token_urlsafe(32)
            hashfunc.update(salt.encode('ascii'))
            calc_hash = base64.b64encode(hashfunc.digest()).decode('ascii')

            entity = datastore.Entity(DSCLIENT.key("config", "password_salt"))
            entity["value"] = salt
            DSCLIENT.put(entity)
            entity = datastore.Entity(DSCLIENT.key("config", "password_hash"))
            entity["value"] = calc_hash
            DSCLIENT.put(entity)

        resp = make_response(redirect('/'))
        resp.set_cookie("session", new_session_key())
        return resp

    except:
        traceback.print_exc()
        return render_template("message.html", msgtype="danger", msg=\
            'An unknown exception occurred. See the logs. <br><br>'\
            '<a href="/">Click here to return home</a>')

@app.route("/set_ifttt_key", methods=["POST"])
def ifttt_key():
    """ Handles the submission of the IFTTT key """
    global IFTTT_SERVICE_KEY
    try:
        cookie = request.cookies.get('session')
        if cookie is None or cookie != get_session_key():
            return render_template("message.html", msgtype="danger", msg=\
                "Invalid request: session cookie not set or not valid")

        keyvalue = request.form["iftttkey"].strip()
        if len(keyvalue) == 64:
            entity = datastore.Entity(key=DSCLIENT.key("config", "ifttt_key"))
            entity["value"] = keyvalue
            DSCLIENT.put(entity)
            IFTTT_SERVICE_KEY = None
            return redirect("/")

        return render_template("message.html", msgtype="danger", msg=\
            'Invalid IFTTT key: length is not 64. <br><br>'\
            '<a href="/">Click here to return home</a>')
    except:
        traceback.print_exc()
        return render_template("message.html", msgtype="danger", msg=\
            'Error while processing IFTTT key. See the logs. <br><br>'\
            '<a href="/">Click here to return home</a>')

@app.route("/set_ynab_key", methods=["POST"])
def ynab_key():
    """ Handles the submission of the YNAB key """
    global YNAB_ACCOUNT_KEY
    try:
        cookie = request.cookies.get('session')
        if cookie is None or cookie != get_session_key():
            return render_template("message.html", msgtype="danger", msg=\
                "Invalid request: session cookie not set or not valid")

        keyvalue = request.form["ynabkey"].strip()
        if len(keyvalue) == 64:
            entity = datastore.Entity(key=DSCLIENT.key("config", "ynab_key"))
            entity["value"] = keyvalue
            DSCLIENT.put(entity)
            YNAB_ACCOUNT_KEY = None
            return redirect("/")

        return render_template("message.html", msgtype="danger", msg=\
            'Invalid YNAB token: length is not 64. <br><br>'\
            '<a href="/">Click here to return home</a>')
    except:
        traceback.print_exc()
        return render_template("message.html", msgtype="danger", msg=\
            'Error while processing YNAB token. See the logs. <br><br>'\
            '<a href="/">Click here to return home</a>')


if __name__ == "__main__":
    app.run(host="localhost", port=18000, debug=True)
