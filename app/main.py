"""
Main module serving the pages for the IFTTT2YNAB appengine app
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

app = Flask(__name__)

DSCLIENT = datastore.Client()

IFTTT_SERVICE_KEY = None
YNAB_ACCOUNT_KEY = None
YNAB_DEFAULT_BUDGET = None
WEB_SESSION_KEY = None

YNAB_BASE = "https://api.youneedabudget.com/v1"


###############################################################################
# IFTTT test methods                                                          #
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
                "triggers": {
                    "ynab_account_updated": {
                        "budget": "TEST#TEST",
                    },
                    "ynab_category_updated": {
                        "budget": "TEST#TEST",
                    },
                    "ynab_category_month_updated": {
                        "budget": "TEST#TEST",
                        "category": "TEST#TEST",
                    },
                    "ynab_category_month_updated_default": {
                        "category": "TEST#TEST",
                    },
                    "ynab_month_updated": {
                        "budget": "TEST#TEST",
                    },
                    "ynab_payee_updated": {
                        "budget": "TEST#TEST",
                    },
                    "ynab_transaction_updated": {
                        "budget": "TEST#TEST",
                    },
                },
                "actions": {
                    "ynab_create": {
                        "budget": "x",
                        "account": "TEST#TEST#1",
                        "date": "x",
                        "amount": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                        "import_id" : "x",
                    },
                    "ynab_create_default": {
                        "account": "TEST#TEST#1",
                        "date": "x",
                        "amount": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                        "import_id" : "x",
                    },
                    "ynab_adjust_balance": {
                        "budget": "x",
                        "account": "TEST#TEST#1",
                        "date": "x",
                        "new_balance": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                    },
                    "ynab_adjust_balance_default": {
                        "account": "TEST#TEST#1",
                        "date": "x",
                        "new_balance": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                    },
                },
                "actionRecordSkipping": {
                    "ynab_create": {
                        "budget": "x",
                        "account": "TEST#TEST#2",
                        "date": "x",
                        "amount": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                        "import_id" : "x",
                    },
                    "ynab_create_default": {
                        "account": "TEST#TEST#2",
                        "date": "x",
                        "amount": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                        "import_id" : "x",
                    },
                    "ynab_adjust_balance": {
                        "budget": "x",
                        "account": "TEST#TEST#2",
                        "date": "x",
                        "new_balance": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                    },
                    "ynab_adjust_balance_default": {
                        "account": "TEST#TEST#2",
                        "date": "x",
                        "new_balance": "x",
                        "payee": "x",
                        "category": "x",
                        "memo": "x",
                        "cleared": "x",
                        "approved": "x",
                        "flag_color": "x",
                    },
                }
            }
        }
    })


###############################################################################
# IFTTT field dropdown methods                                                #
###############################################################################

@app.route("/ifttt/v1/actions/ynab_create/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/actions/ynab_adjust_balance/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_account_updated/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_category_updated/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_category_month_updated/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_month_updated/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_payee_updated/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_transaction_updated/fields/"\
           "budget/options", methods=["POST"])
def ifttt_budget_options():
    """ Option values for the budget field """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    try:
        data = get_ynab_budgets()
        return json.dumps({"data": data})
    except:
        traceback.print_exc()
        return json.dumps({"data": [{"label": "ERROR retrieving YNAB data",
                                     "value": ""}]})

@app.route("/ifttt/v1/actions/ynab_create_default/fields/"\
           "account/options", methods=["POST"])
@app.route("/ifttt/v1/actions/ynab_adjust_balance_default/fields/"\
           "account/options", methods=["POST"])
def ifttt_account_options():
    """ Option values for the account field """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    try:
        if get_default_budget() is None:
            return json.dumps({"data": [{"label": "ERROR no default budget",
                                         "value": ""}]})
        data = get_ynab_accounts()
        return json.dumps({"data": data})
    except:
        traceback.print_exc()
        return json.dumps({"data": [{"label": "ERROR retrieving YNAB data",
                                     "value": ""}]})

@app.route("/ifttt/v1/actions/ynab_create_default/fields/"\
           "category/options", methods=["POST"])
@app.route("/ifttt/v1/actions/ynab_adjust_balance_default/fields/"\
           "category/options", methods=["POST"])
def ifttt_category_options_false():
    return ifttt_category_options(False)

@app.route("/ifttt/v1/triggers/ynab_category_month_updated_default/fields/"\
           "category/options", methods=["POST"])
def ifttt_category_options_true():
    return ifttt_category_options(True)

def ifttt_category_options(trigger):
    """ Option values for the category field """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    try:
        if get_default_budget() is None:
            return json.dumps({"data": [{"label": "ERROR no default budget",
                                         "value": ""}]})
        data = get_ynab_categories(None, trigger)
        return json.dumps({"data": data})
    except:
        traceback.print_exc()
        return json.dumps({"data": [{"label": "ERROR retrieving YNAB data",
                                     "value": ""}]})


###############################################################################
# IFTTT create transaction action                                             #
###############################################################################

@app.route("/ifttt/v1/actions/ynab_create", methods=["POST"])
def ifttt_create_action_1():
    return ifttt_create_action(False)

@app.route("/ifttt/v1/actions/ynab_create_default", methods=["POST"])
def ifttt_create_action_2():
    return ifttt_create_action(True)

def ifttt_create_action(default):
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
    for x in ["account", "date", "amount", "payee", "category",
              "memo", "cleared", "approved", "flag_color", "import_id"]:
        if x not in fields:
            print("[create_action] ERROR: missing field: "+x)
            return json.dumps({"errors": [{"status": "SKIP", \
                "message": "Invalid data: missing field: "+x}]}), 400
    if not default and "budget" not in fields:
        print("[adjust_balance_action] ERROR: missing field: budget")
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: missing field: "+x}]}), 400

    if default:
        budget = get_default_budget()
    else:
        budget = fields["budget"]

    account = fields["account"]

    if account == "TEST#TEST#1":
        return json.dumps({"data": [{"id": uuid.uuid4().hex}]})
    if account == "TEST#TEST#2":
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Test"}]}), 400
    if len(str(budget)) != 36:
        print("[create_action] ERROR: incorrect budget (no uuid): "+budget)
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: incorrect budget: "+budget}]}), 400

    r = requests.get(YNAB_BASE + "/budgets/{}/accounts".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())})
    results = r.json()["data"]["accounts"]
    account_id = None
    for a in results:
        if a["id"] == account:
            account_id = a["id"]
        elif a["name"] == account:
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
                if c["id"] == category:
                    category_id = c["id"]
                elif c["name"] == category:
                    category_id = c["id"]
        if category_id is None:
            print("[create_action] WARNING: unknown category, ignored")

    try:
        if fields["date"] == "":
            date = arrow.now(data["user"]["timezone"]).format("YYYY-MM-DD")
        else:
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
# IFTTT adjust balance action                                                 #
###############################################################################

@app.route("/ifttt/v1/actions/ynab_adjust_balance", methods=["POST"])
def ifttt_adjust_balance_action_1():
    return ifttt_adjust_balance_action(False)

@app.route("/ifttt/v1/actions/ynab_adjust_balance_default", methods=["POST"])
def ifttt_adjust_balance_action_2():
    return ifttt_adjust_balance_action(True)

def ifttt_adjust_balance_action(default):
    """ Main endpoint to adjust a balance of an account in YNAB """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[adjust_balance_action] ERROR: invalid service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    data = request.get_json()
    if "actionFields" not in data:
        print("[adjust_balance_action] ERROR: missing actionFields")
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: actionFields missing"}]}), 400
    fields = data["actionFields"]
    for x in ["account", "date", "new_balance", "payee", "category",
              "memo", "cleared", "approved", "flag_color"]:
        if x not in fields:
            print("[adjust_balance_action] ERROR: missing field: "+x)
            return json.dumps({"errors": [{"status": "SKIP", \
                "message": "Invalid data: missing field: "+x}]}), 400
    if not default and "budget" not in fields:
        print("[adjust_balance_action] ERROR: missing field: budget")
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: missing field: "+x}]}), 400

    if default:
        budget = get_default_budget()
    else:
        budget = fields["budget"]

    account = fields["account"]

    if account == "TEST#TEST#1":
        return json.dumps({"data": [{"id": uuid.uuid4().hex}]})
    if account == "TEST#TEST#2":
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Test"}]}), 400
    if len(str(budget)) != 36:
        print("[adjust_balance_action] ERROR: incorrect budget (no uuid): "\
              +budget)
        return json.dumps({"errors": [{"status": "SKIP", \
            "message": "Invalid data: incorrect budget: "+budget}]}), 400

    r = requests.get(YNAB_BASE + "/budgets/{}/accounts".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())})
    results = r.json()["data"]["accounts"]
    account_id = None
    for a in results:
        if a["id"] == account:
            account_id = a["id"]
            old_balance = a["balance"]
        elif a["name"] == account:
            account_id = a["id"]
            old_balance = a["balance"]
    if account_id is None:
        print("[adjust_balance_action] ERROR: account not found")
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
                if c["id"] == category:
                    category_id = c["id"]
                elif c["name"] == category:
                    category_id = c["id"]
        if category_id is None:
            print("[adjust_balance_action] WARNING: unknown category, ignored")

    try:
        if fields["date"] == "":
            date = arrow.now(data["user"]["timezone"]).format("YYYY-MM-DD")
        else:
            date = arrow.get(fields["date"]).format("YYYY-MM-DD")
    except:
        print("[adjust_balance_action] ERROR: invalid date: "+fields["date"])
        return json.dumps({"errors": [{"status": "SKIP",
                                       "message": "Invalid date"}]}), 400

    try:
        new_balance = int(float(fields["new_balance"])*1000)
        amount = new_balance - old_balance
    except:
        print("[adjust_balance_action] ERROR: invalid amount: "+\
              fields["new_balance"])
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
# IFTTT account is updated trigger                                            #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_account_updated", methods=["POST"])
def ifttt_account_updated():
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[account_updated] ERROR: invalid IFTTT service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401

    try:
        data = request.get_json()
        print("[account_updated] input: {}".format(json.dumps(data)))

        if "triggerFields" not in data or\
                "budget" not in data["triggerFields"]:
            print("[account_updated] ERROR: budget field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        budget = data["triggerFields"]["budget"]

        if "trigger_identity" not in data:
            print("[account_updated] ERROR: trigger_identity field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        triggerid = data["trigger_identity"]

        limit = 50
        if "limit" in data:
            limit = data["limit"]

        timezone = "UTC"
        if "user" in data and "timezone" in data["user"]:
            timezone = data["user"]["timezone"]

        if budget == "TEST#TEST":
            results = ifttt_account_updated_test()
        else:
            entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
            if entity is None:
                print("[account_updated] WARNING: unknown budget "+budget)
                results = []
            else:
                data = json.loads(entity["accounts"])
                if "triggers" not in data:
                    triggers = []
                else:
                    triggers = data["triggers"]
                if triggerid not in triggers:
                    print("Adding new trigger: "+triggerid)
                    triggers.append(triggerid)
                    data["triggers"] = triggers
                    entity["accounts"] = json.dumps(data)
                    DSCLIENT.put(entity)

                results = data["changed"]

        for result in results:
            result["created_at"] = arrow.get(result["created_at"])\
                                   .to(timezone).isoformat()

        print("[account_updated] Found {} updates".format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[account_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400


def ifttt_account_updated_test():
    created = arrow.utcnow().isoformat()
    stamp = arrow.utcnow().timestamp
    item1 = {"created_at": created, "meta": {"id": "1", "timestamp": stamp}}
    item2 = {"created_at": created, "meta": {"id": "2", "timestamp": stamp}}
    item3 = {"created_at": created, "meta": {"id": "3", "timestamp": stamp}}
    for item in [item1, item2, item3]:
        item["change"] = "update"
        item["name"] = "TEST_account"
        item["type"] = "checking"
        item["on_budget"] = True
        item["closed"] = False
        item["note"] = "TEST_note"
        item["balance"] = "3.33"
        item["cleared_balance"] = "2.22"
        item["uncleared_balance"] = "1.11"
    return [item1, item2, item3]


###############################################################################
# IFTTT category is updated trigger                                           #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_category_updated", methods=["POST"])
def ifttt_category_updated():
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[category_updated] ERROR: invalid IFTTT service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401

    try:
        data = request.get_json()
        print("[category_updated] input: {}".format(json.dumps(data)))

        if "triggerFields" not in data or\
                "budget" not in data["triggerFields"]:
            print("[category_updated] ERROR: budget field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        budget = data["triggerFields"]["budget"]

        if "trigger_identity" not in data:
            print("[category_updated] ERROR: trigger_identity field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        triggerid = data["trigger_identity"]

        limit = 50
        if "limit" in data:
            limit = data["limit"]

        timezone = "UTC"
        if "user" in data and "timezone" in data["user"]:
            timezone = data["user"]["timezone"]

        if budget == "TEST#TEST":
            results = ifttt_category_updated_test()
        else:
            entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
            if entity is None:
                print("[category_updated] WARNING: unknown budget "+budget)
                results = []
            else:
                data = json.loads(entity["categories"])
                if "triggers" not in data:
                    triggers = []
                else:
                    triggers = data["triggers"]
                if triggerid not in triggers:
                    print("Adding new trigger: "+triggerid)
                    triggers.append(triggerid)
                    data["triggers"] = triggers
                    entity["categories"] = json.dumps(data)
                    DSCLIENT.put(entity)

                results = data["changed"]

        for result in results:
            result["created_at"] = arrow.get(result["created_at"])\
                                   .to(timezone).isoformat()

        print("[category_updated] Found {} updates".format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[category_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400


def ifttt_category_updated_test():
    created = arrow.utcnow().isoformat()
    stamp = arrow.utcnow().timestamp
    item1 = {"created_at": created, "meta": {"id": "1", "timestamp": stamp}}
    item2 = {"created_at": created, "meta": {"id": "2", "timestamp": stamp}}
    item3 = {"created_at": created, "meta": {"id": "3", "timestamp": stamp}}
    for item in [item1, item2, item3]:
        item["change"] = "update"
        item["group"] = "TEST_group"
        item["name"] = "TEST_category"
        item["hidden"] = False
        item["note"] = "TEST_note"
        item["budgeted"] = "33.33"
        item["activity"] = "22.22"
        item["balance"] = "11.11"
        item["goal_type"] = "TB"
        item["goal_creation_month"] = "2099-01"
        item["goal_target"] = "44.44"
        item["goal_target_month"] = "2099-12"
        item["goal_percentage_complete"] = "50"
    return [item1, item2, item3]


###############################################################################
# IFTTT category month is updated trigger                                     #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_category_month_updated",
           methods=["POST"])
def ifttt_category_month_updated():
    return ifttt_category_month_updated_implementation(False)

@app.route("/ifttt/v1/triggers/ynab_category_month_updated_default",
           methods=["POST"])
def ifttt_category_month_updated_default():
    return ifttt_category_month_updated_implementation(True)


def ifttt_category_month_updated_implementation(default):
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[cat_month_updated] ERROR: invalid IFTTT service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401

    try:
        data = request.get_json()
        print("[cat_month_updated] input: {}".format(json.dumps(data)))

        if default:
            budget = get_default_budget()
        else:
            if "triggerFields" not in data or\
                    "budget" not in data["triggerFields"]:
                print("[cat_month_updated] ERROR: budget field missing!")
                return json.dumps({"errors": [{"message": "Invalid data"}]}),\
                       400
            budget = data["triggerFields"]["budget"]

        if "triggerFields" not in data or\
                "category" not in data["triggerFields"]:
            print("[cat_month_updated] ERROR: category field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}),\
                   400
        category = data["triggerFields"]["category"]

        if "trigger_identity" not in data:
            print("[cat_month_updated] ERROR: trigger_identity field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        triggerid = data["trigger_identity"]

        limit = 50
        if "limit" in data:
            limit = data["limit"]

        timezone = "UTC"
        if "user" in data and "timezone" in data["user"]:
            timezone = data["user"]["timezone"]

        if category == "TEST#TEST":
            results = ifttt_category_month_updated_test()
        else:
            entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
            if entity is None:
                print("[cat_month_updated] WARNING: unknown budget "+budget)
                results = []
            else:
                cats = json.loads(entity["categories"])
                if category != "":
                    if category not in cats["data"]:
                        for cat in cats["data"]:
                            catdata = cats["data"][cat]
                            if category == catdata[1] + " - " + catdata[0]:
                                category = cat
                    if category not in cats["data"]:
                        for cat in cats["data"]:
                            if category == cats["data"][cat][0]:
                                category = cat
                    if category not in cats["data"]:
                        print("[cat_month_updated] ERROR: category not found!")
                        return json.dumps({"errors": [{"message":\
                                        "Invalid data"}]}), 400

                data = json.loads(entity["month_categories"])
                if "triggers" not in data:
                    triggers = []
                else:
                    triggers = data["triggers"]
                if triggerid not in triggers:
                    print("Adding new trigger: "+triggerid)
                    triggers.append(triggerid)
                    data["triggers"] = triggers
                    entity["month_categories"] = json.dumps(data)
                    DSCLIENT.put(entity)

                if category == "":
                    results = data["changed"]
                else:
                    results = []
                    for change in data["changed"]:
                        if change["category_id"] == category:
                            results.append(change)

        for result in results:
            result["created_at"] = arrow.get(result["created_at"])\
                                   .to(timezone).isoformat()

        print("[cat_month_updated] Found {} updates".format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[cat_month_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400


def ifttt_category_month_updated_test():
    created = arrow.utcnow().isoformat()
    stamp = arrow.utcnow().timestamp
    item1 = {"created_at": created, "meta": {"id": "1", "timestamp": stamp}}
    item2 = {"created_at": created, "meta": {"id": "2", "timestamp": stamp}}
    item3 = {"created_at": created, "meta": {"id": "3", "timestamp": stamp}}
    for item in [item1, item2, item3]:
        item["month"] = "2020-01"
        item["relative_index"] = 2
        item["group"] = "TEST_group"
        item["name"] = "TEST_category"
        item["hidden"] = False
        item["note"] = "TEST_note"
        item["budgeted"] = "33.33"
        item["activity"] = "22.22"
        item["balance"] = "11.11"
        item["goal_type"] = "TB"
        item["goal_creation_month"] = "2099-01"
        item["goal_target"] = "44.44"
        item["goal_target_month"] = "2099-12"
        item["goal_percentage_complete"] = "50"
    return [item1, item2, item3]


###############################################################################
# IFTTT month is updated trigger                                              #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_month_updated", methods=["POST"])
def ifttt_month_updated():
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[month_updated] ERROR: invalid IFTTT service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401

    try:
        data = request.get_json()
        print("[month_updated] input: {}".format(json.dumps(data)))

        if "triggerFields" not in data or\
                "budget" not in data["triggerFields"]:
            print("[month_updated] ERROR: budget field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        budget = data["triggerFields"]["budget"]

        if "trigger_identity" not in data:
            print("[month_updated] ERROR: trigger_identity field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        triggerid = data["trigger_identity"]

        limit = 50
        if "limit" in data:
            limit = data["limit"]

        timezone = "UTC"
        if "user" in data and "timezone" in data["user"]:
            timezone = data["user"]["timezone"]

        if budget == "TEST#TEST":
            results = ifttt_month_updated_test()
        else:
            entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
            if entity is None:
                print("[month_updated] WARNING: unknown budget "+budget)
                results = []
            else:
                months = json.loads(entity["months"])
                if "triggers" not in months:
                    triggers = []
                else:
                    triggers = months["triggers"]
                if triggerid not in triggers:
                    print("Adding new trigger: "+triggerid)
                    triggers.append(triggerid)
                    months["triggers"] = triggers
                    entity["months"] = json.dumps(months)
                    DSCLIENT.put(entity)
            results = months["changed"]

        for result in results:
            result["created_at"] = arrow.get(result["created_at"])\
                                    .to(timezone).isoformat()

        print("[month_updated] Found {} updates"
              .format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[month_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400


def ifttt_month_updated_test():
    created = arrow.utcnow().isoformat()
    stamp = arrow.utcnow().timestamp
    item1 = {"created_at": created, "meta": {"id": "1", "timestamp": stamp}}
    item2 = {"created_at": created, "meta": {"id": "2", "timestamp": stamp}}
    item3 = {"created_at": created, "meta": {"id": "3", "timestamp": stamp}}
    for item in [item1, item2, item3]:
        item["month"] = "2099-12"
        item["relative_index"] = 42
        item["income"] = "1234.56"
        item["budgeted"] = "1234.56"
        item["activity"] = "1234.56"
        item["to_be_budgeted"] = "1234.56"
        item["age_of_money"] = "60"
    return [item1, item2, item3]


###############################################################################
# IFTTT payee is updated trigger                                              #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_payee_updated", methods=["POST"])
def ifttt_payee_updated():
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[payee_updated] ERROR: invalid IFTTT service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401

    try:
        data = request.get_json()
        print("[payee_updated] input: {}".format(json.dumps(data)))

        if "triggerFields" not in data or\
                "budget" not in data["triggerFields"]:
            print("[payee_updated] ERROR: budget field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        budget = data["triggerFields"]["budget"]

        if "trigger_identity" not in data:
            print("[payee_updated] ERROR: trigger_identity field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        triggerid = data["trigger_identity"]

        limit = 50
        if "limit" in data:
            limit = data["limit"]

        timezone = "UTC"
        if "user" in data and "timezone" in data["user"]:
            timezone = data["user"]["timezone"]

        if budget == "TEST#TEST":
            results = ifttt_payee_updated_test()
        else:
            entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
            if entity is None:
                print("[payee_updated] WARNING: unknown budget "+budget)
                results = []
            else:
                data = json.loads(entity["payees"])
                if "triggers" not in data:
                    triggers = []
                else:
                    triggers = data["triggers"]
                if triggerid not in triggers:
                    print("Adding new trigger: "+triggerid)
                    triggers.append(triggerid)
                    data["triggers"] = triggers
                    entity["payees"] = json.dumps(data)
                    DSCLIENT.put(entity)

                results = data["changed"]

        for result in results:
            result["created_at"] = arrow.get(result["created_at"])\
                                   .to(timezone).isoformat()

        print("[payee_updated] Found {} updates".format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[payee_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400


def ifttt_payee_updated_test():
    created = arrow.utcnow().isoformat()
    stamp = arrow.utcnow().timestamp
    item1 = {"created_at": created, "meta": {"id": "1", "timestamp": stamp}}
    item2 = {"created_at": created, "meta": {"id": "2", "timestamp": stamp}}
    item3 = {"created_at": created, "meta": {"id": "3", "timestamp": stamp}}
    for item in [item1, item2, item3]:
        item["change"] = "update"
        item["name"] = "TEST_payee"
    return [item1, item2, item3]


###############################################################################
# IFTTT transaction is updated trigger                                        #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_transaction_updated", methods=["POST"])
def ifttt_transaction_updated():
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        print("[transaction_updated] ERROR: invalid IFTTT service key!")
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401

    try:
        data = request.get_json()
        print("[transaction_updated] input: {}".format(json.dumps(data)))

        if "triggerFields" not in data or\
                "budget" not in data["triggerFields"]:
            print("[transaction_updated] ERROR: budget field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        budget = data["triggerFields"]["budget"]

        if "trigger_identity" not in data:
            print("[transaction_updated] ERROR: trigger_identity field missing!")
            return json.dumps({"errors": [{"message": "Invalid data"}]}), 400
        triggerid = data["trigger_identity"]

        limit = 50
        if "limit" in data:
            limit = data["limit"]

        timezone = "UTC"
        if "user" in data and "timezone" in data["user"]:
            timezone = data["user"]["timezone"]

        if budget == "TEST#TEST":
            results = ifttt_transaction_updated_test()
        else:
            entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
            if entity is None:
                print("[transaction_updated] WARNING: unknown budget "+budget)
                results = []
            else:
                data = json.loads(entity["transactions"])
                if "triggers" not in data:
                    triggers = []
                else:
                    triggers = data["triggers"]
                if triggerid not in triggers:
                    print("Adding new trigger: "+triggerid)
                    triggers.append(triggerid)
                    data["triggers"] = triggers
                    entity["transactions"] = json.dumps(data)
                    DSCLIENT.put(entity)

                results = data["changed"]

        for result in results:
            result["created_at"] = arrow.get(result["created_at"])\
                                   .to(timezone).isoformat()

        print("[transaction_updated] Found {} updates".format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[transaction_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400


def ifttt_transaction_updated_test():
    created = arrow.utcnow().isoformat()
    stamp = arrow.utcnow().timestamp
    item1 = {"created_at": created, "meta": {"id": "1", "timestamp": stamp}}
    item2 = {"created_at": created, "meta": {"id": "2", "timestamp": stamp}}
    item3 = {"created_at": created, "meta": {"id": "3", "timestamp": stamp}}
    for item in [item1, item2, item3]:
        item["change"] = "update"
        item["date"] = "2020-12-31"
        item["amount"] = 12.34
        item["memo"] = "Foo bar"
        item["cleared"] = "cleared"
        item["approved"] = True
        item["flag_color"] = "red"
        item["account"] = "Piggy bank"
        item["payee"] = "Acme Market"
        item["category"] = "Supermarket"
        item["category_group"] = "Personal expenses"
        item["transfer_account"] = ""
    return [item1, item2, item3]


###############################################################################
# IFTTT delete trigger method                                                 #
###############################################################################

@app.route("/ifttt/v1/triggers/ynab_account_updated/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
@app.route("/ifttt/v1/triggers/ynab_category_updated/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
@app.route("/ifttt/v1/triggers/ynab_category_month_updated/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
@app.route("/ifttt/v1/triggers/ynab_category_month_updated_default/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
@app.route("/ifttt/v1/triggers/ynab_month_updated/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
@app.route("/ifttt/v1/triggers/ynab_payee_updated/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
@app.route("/ifttt/v1/triggers/ynab_transaction_updated/" +
           "trigger_identity/<triggerid>", methods=["DELETE"])
def ifttt_delete_trigger(triggerid):
    budgets = get_ynab_budgets()
    for budget in [b["value"] for b in budgets]:
        entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
        if entity is not None:
            for typ in ['accounts', 'categories', 'months', 'month_categories',
                        'payees', 'transactions']:
                data = entity[typ]
                if data is not None:
                    data = json.loads(data)
                    if "triggers" in data:
                        if triggerid in data["triggers"]:
                            newtriggers = []
                            for trig in data["triggers"]:
                                if trig != triggerid:
                                    newtriggers.append(trig)
                            data["triggers"] = newtriggers
                            entity[typ] = json.dumps(data)
                            DSCLIENT.put(entity)


###############################################################################
# YNAB interface methods                                                      #
###############################################################################

YNAB_BUDGETS = []

@app.route("/cron/ynab", methods=["GET"])
def cron():
    global YNAB_BUDGETS
    if not YNAB_BUDGETS:
        entity = DSCLIENT.get(DSCLIENT.key("budget", "budgets"))
        if entity is not None:
            YNAB_BUDGETS = json.loads(entity["data"])
        else:
            entity = datastore.Entity(DSCLIENT.key("budget", "budgets"))

    budgets = get_ynab_budgets_raw()
    to_process = []
    for a in budgets:
        changed = False
        found = False
        for b in YNAB_BUDGETS:
            if a['id'] == b['id']:
                found = True
                if a['last_modified_on'] != b['last_modified_on']:
                    changed = True
        if changed or not found:
            to_process.append(a['id'])

    YNAB_BUDGETS = budgets
    print(to_process)
    if to_process:
        entity = datastore.Entity(DSCLIENT.key("budget", "budgets"),
                                  exclude_from_indexes=["data"])
        entity["data"] = json.dumps(YNAB_BUDGETS)
        DSCLIENT.put(entity)

    triggers = []
    for budget in to_process:

        entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
        if entity is None:
            entity = datastore.Entity(DSCLIENT.key("budget", budget),\
                     exclude_from_indexes=['config', 'accounts', 'categories',
                                           'months', 'month_categories',
                                           'payees', 'transactions'])
            entity['accounts'] = json.dumps({})
            entity['categories'] = json.dumps({})
            entity['months'] = json.dumps({})
            entity['month_categories'] = json.dumps({})
            entity['payees'] = json.dumps({})
            entity['transactions'] = json.dumps({})
            first = True
        else:
            first = False
            knowledge = json.loads(entity['config'])['knowledge']

        url = YNAB_BASE + "/budgets/{}".format(budget)
        if not first:
            url += "?last_knowledge_of_server={}".format(knowledge)

        r = requests.get(url,\
            headers={"Authorization": "Bearer {}".format(get_ynab_key())})
        result = r.json()["data"]
        data = result["budget"]

        config = {
            'id': data['id'],
            'name': data['name'],
            'knowledge': result['server_knowledge']
        }
        entity['config'] = json.dumps(config)

        accounts = json.loads(entity["accounts"])
        accounts = process_accounts(accounts,
                                    data["accounts"],
                                    data["currency_format"],
                                    result['server_knowledge'],
                                    first,
                                    triggers)
        entity["accounts"] = json.dumps(accounts)

        categories = json.loads(entity["categories"])
        categories = process_categories(categories,
                                        data["categories"],
                                        data["category_groups"],
                                        data["currency_format"],
                                        result['server_knowledge'],
                                        first,
                                        triggers)
        entity["categories"] = json.dumps(categories)

        months = json.loads(entity["months"])
        months = process_months(months,
                                data["months"],
                                data["first_month"],
                                data["currency_format"],
                                result['server_knowledge'],
                                first,
                                triggers)
        entity["months"] = json.dumps(months)

        month_categories = json.loads(entity["month_categories"])
        month_categories = process_month_categories(month_categories,
                                                    categories,
                                                    data["months"],
                                                    data["first_month"],
                                                    data["currency_format"],
                                                    result['server_knowledge'],
                                                    first,
                                                    triggers)
        entity["month_categories"] = json.dumps(month_categories)

        payees = json.loads(entity["payees"])
        payees = process_payees(payees,
                                data["payees"],
                                result['server_knowledge'],
                                first,
                                triggers)
        entity["payees"] = json.dumps(payees)

        transactions = json.loads(entity["transactions"])
        transactions = process_transactions(transactions,
                                            accounts,
                                            categories,
                                            payees,
                                            data["transactions"],
                                            data["currency_format"],
                                            result['server_knowledge'],
                                            first,
                                            triggers)
        entity["transactions"] = json.dumps(transactions)

        print(data["name"] + " size = " + str(len(entity["config"]) +
                                              len(entity["accounts"]) +
                                              len(entity["categories"]) +
                                              len(entity["months"]) +
                                              len(entity["month_categories"]) +
                                              len(entity["payees"]) +
                                              len(entity["transactions"])))
        DSCLIENT.put(entity)

    if triggers:
        print("Updating triggers: " + json.dumps(triggers))
        data = {"data": []}
        for triggerid in triggers:
            data["data"].append({"trigger_identity": triggerid})
        headers = {
            "IFTTT-Channel-Key": get_ifttt_key(),
            "IFTTT-Service-Key": get_ifttt_key(),
            "X-Request-ID": uuid.uuid4().hex,
            "Content-Type": "application/json"
        }
        res = requests.post("https://realtime.ifttt.com/v1/notifications",
                            headers=headers, data=json.dumps(data))
        print(res.text)

    return ""

def process_accounts(old, data, curfmt, knowledge, first, triggers):
    if first:
        result = {"changed": [], "data": {}}
    else:
        result = old

    now = arrow.utcnow()

    for item in data:

        fieldhash = hashlib.md5("{}|{}|{}|{}|{}|{}|{}|{}".format(
            item["name"],
            item["type"],
            item["on_budget"],
            item["closed"],
            item["note"],
            item["balance"],
            item["cleared_balance"],
            item["uncleared_balance"],
        ).encode("utf-8")).hexdigest()[:8]

        if item["deleted"]:
            change_type = "delete"
            if item["id"] in result["data"]:
                del result["data"][item["id"]]
        else:
            if item["id"] in result["data"]:
                if result["data"][item["id"]][1] != fieldhash:
                    change_type = "update"
                else:
                    change_type = None
            else:
                change_type = "new"
            result["data"][item["id"]] = [item["name"], fieldhash]

        if not first and change_type is not None:
            change = {
                "created_at": now.isoformat(),
                "change": change_type,
                "name": item["name"],
                "type": item["type"],
                "on_budget": item["on_budget"],
                "closed": item["closed"],
                "note": item["note"],
                "balance": convert_amount(item["balance"], curfmt),
                "cleared_balance": convert_amount(item["cleared_balance"],
                                                  curfmt),
                "uncleared_balance": convert_amount(item["uncleared_balance"],
                                                    curfmt),
                "meta": {
                    "id": item["id"] + "_" + str(knowledge),
                    "timestamp": now.timestamp
                }
            }
            result["changed"].insert(0, change)

    if data and "triggers" in result:
        for trig in result["triggers"]:
            triggers.append(trig)

    return cleanup_old(result, now)

def process_categories(old, data, groupdata, curfmt, knowledge, first,
                       triggers):
    if first:
        result = {"changed": [], "data": {}, "groups": {}}
    else:
        result = old

    now = arrow.utcnow()

    for item in groupdata:
        if item["deleted"]:
            if item["id"] in result["groups"]:
                del result["groups"][item["id"]]
        else:
            result["groups"][item["id"]] = item["name"]

    for item in data:
        group = ""
        if item["category_group_id"] in result["groups"]:
            group = result["groups"][item["category_group_id"]]
        elif not item["deleted"]:
            print("Error: group not found: "+item["category_group_id"])

        fieldhash = hashlib.md5("{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(
            item["category_group_id"],
            item["name"],
            item["hidden"],
            item["note"],
            item["budgeted"],
            item["activity"],
            item["balance"],
            item["goal_type"],
            item["goal_creation_month"],
            item["goal_target"],
            item["goal_target_month"],
            item["goal_percentage_complete"],
        ).encode("utf-8")).hexdigest()[:8]

        if item["deleted"]:
            change_type = "delete"
            if item["id"] in result["data"]:
                del result["data"][item["id"]]
        else:
            if item["id"] in result["data"]:
                if result["data"][item["id"]][2] != fieldhash:
                    change_type = "update"
                else:
                    change_type = None
            else:
                change_type = "new"
            result["data"][item["id"]] = [item["name"], group, fieldhash]

        if not first and change_type is not None:
            change = {
                "category_id": item["id"],
                "created_at": now.isoformat(),
                "change": change_type,
                "group": group,
                "name": item["name"],
                "hidden": item["hidden"],
                "note": item["note"],
                "budgeted": convert_amount(item["budgeted"], curfmt),
                "activity": convert_amount(item["activity"], curfmt),
                "balance": convert_amount(item["balance"], curfmt),
                "goal_type": item["goal_type"],
                "goal_creation_month": item["goal_creation_month"],
                "goal_target": convert_amount(item["goal_target"], curfmt),
                "goal_target_month": item["goal_target_month"],
                "goal_percentage_complete": item["goal_percentage_complete"],
                "meta": {
                    "id": item["id"] + "_" + str(knowledge),
                    "timestamp": now.timestamp
                }
            }
            result["changed"].insert(0, change)

    if data and "triggers" in result:
        for trig in result["triggers"]:
            triggers.append(trig)

    return cleanup_old(result, now)

def process_months(old, data, first_month, curfmt, knowledge, first, triggers):
    if first:
        # for months we only keep changes, so no need to process further
        return {"changed": []}
    result = old

    now = arrow.utcnow()

    for month in data:
        date = arrow.get(first_month)
        target = arrow.get(month["month"])
        index = 1
        while date < target:
            index += 1
            date = date.shift(months=1)
        item = {
            "created_at": now.isoformat(),
            "month": month["month"][:7],
            "relative_index": index,
            "income": convert_amount(month["income"], curfmt),
            "budgeted": convert_amount(month["budgeted"], curfmt),
            "activity": convert_amount(month["activity"], curfmt),
            "to_be_budgeted": convert_amount(month["to_be_budgeted"], curfmt),
            "age_of_money": month["age_of_money"],
            "meta": {
                "id": month["month"] + "_" + str(knowledge),
                "timestamp": now.timestamp
            }
        }
        result["changed"].insert(0, item)

    if data and "triggers" in result:
        for trig in result["triggers"]:
            triggers.append(trig)

    return cleanup_old(result, now)

def process_month_categories(old, categories, data, first_month, curfmt,
                             knowledge, first, triggers):
    if first:
        # for months we only keep changes, so no need to process further
        return {"changed": []}
    result = old

    now = arrow.utcnow()

    for month in data:
        date = arrow.get(first_month)
        target = arrow.get(month["month"])
        index = 1
        while date < target:
            index += 1
            date = date.shift(months=1)

        for item in month["categories"]:
            group = ""
            if item["category_group_id"] in categories["groups"]:
                group = categories["groups"][item["category_group_id"]]
            elif not item["deleted"]:
                print("Error: group not found: "+item["category_group_id"])

            if not item["deleted"]:
                change = {
                    "category_id": item["id"],
                    "created_at": now.isoformat(),
                    "month": month["month"][:7],
                    "relative_index": index,
                    "group": group,
                    "name": item["name"],
                    "hidden": item["hidden"],
                    "note": item["note"],
                    "budgeted": convert_amount(item["budgeted"], curfmt),
                    "activity": convert_amount(item["activity"], curfmt),
                    "balance": convert_amount(item["balance"], curfmt),
                    "goal_type": item["goal_type"],
                    "goal_creation_month": item["goal_creation_month"],
                    "goal_target": convert_amount(item["goal_target"], curfmt),
                    "goal_target_month": item["goal_target_month"],
                    "goal_percentage_complete": \
                        item["goal_percentage_complete"],
                    "meta": {
                        "id": item["id"] + "_" + str(knowledge),
                        "timestamp": now.timestamp
                    }
                }
                result["changed"].insert(0, change)

    if data and "triggers" in result:
        for trig in result["triggers"]:
            triggers.append(trig)

    return cleanup_old(result, now)

def process_payees(old, data, knowledge, first, triggers):
    if first:
        result = {"changed": [], "data": {}}
    else:
        result = old

    now = arrow.utcnow()

    for item in data:

        if item["deleted"]:
            change_type = "delete"
            if item["id"] in result["data"]:
                del result["data"][item["id"]]
        else:
            if item["id"] in result["data"]:
                if result["data"][item["id"]] != item["name"]:
                    change_type = "update"
                else:
                    change_type = None
            else:
                change_type = "new"
            result["data"][item["id"]] = item["name"]

        if not first and change_type is not None:
            change = {
                "created_at": now.isoformat(),
                "change": change_type,
                "name": item["name"],
                "meta": {
                    "id": item["id"] + "_" + str(knowledge),
                    "timestamp": now.timestamp
                }
            }
            result["changed"].insert(0, change)

    if data and "triggers" in result:
        for trig in result["triggers"]:
            triggers.append(trig)

    return cleanup_old(result, now)

def process_transactions(old, accounts, categories, payees, data, curfmt,
                         knowledge, first, triggers):
    if first:
        result = {"changed": [], "data": []}
        return result

    result = old
    now = arrow.utcnow()

    for item in data:

        if item["deleted"]:
            change_type = "delete"
            if item["id"] in result["data"]:
                result["data"].remove(item["id"])
        else:
            if item["id"] in result["data"]:
                change_type = "update"
            else:
                change_type = "new"
                result["data"].append(item["id"])

        payee = None
        if item["payee_id"] in payees["data"]:
            payee = payees["data"][item["payee_id"]]
        account = None
        if item["account_id"] in accounts["data"]:
            account = accounts["data"][item["account_id"]][0]
        transfer_account = None
        if item["transfer_account_id"] in accounts["data"]:
            transfer_account = accounts["data"][item["transfer_account_id"]][0]
        category = None
        category_group = None
        if item["category_id"] in categories["data"]:
            category = categories["data"][item["category_id"]][0]
            category_group = categories["data"][item["category_id"]][1]

        if not first and change_type is not None:
            change = {
                "created_at": now.isoformat(),
                "change": change_type,
                "date": item["date"],
                "amount": convert_amount(item["amount"], curfmt),
                "memo": item["memo"],
                "cleared": item["cleared"],
                "approved": item["approved"],
                "flag_color": item["flag_color"],
                "account": account,
                "payee": payee,
                "category": category,
                "category_group": category_group,
                "transfer_account": transfer_account,
                "meta": {
                    "id": item["id"] + "_" + str(knowledge),
                    "timestamp": now.timestamp
                }
            }
            result["changed"].insert(0, change)

    if data and "triggers" in result:
        for trig in result["triggers"]:
            triggers.append(trig)

    return cleanup_old(result, now)

def convert_amount(amount, curfmt):
    digits = curfmt["decimal_digits"]
    if digits == 0:
        return "{}".format(amount // 1000)
    if digits == 1:
        return "{:.1f}".format((amount // 100) / 10)
    if digits == 2:
        return "{:.2f}".format((amount // 10) / 100)
    return "{:.3f}".format(amount / 1000)

def cleanup_old(result, now):
    result2 = {"changed": [], "triggers": []}
    if "triggers" in result:
        result2["triggers"] = result["triggers"]
    if "data" in result:
        result2["data"] = result["data"]
    if "groups" in result:
        result2["groups"] = result["groups"]
    # only keep records younger than 1 day
    for change in result["changed"]:
        if change["meta"]["timestamp"] > now.timestamp - 86400:
            result2["changed"].append(change)
    # but always keep the last record
    if not result2["changed"] and result["changed"]:
        result2["changed"].append(result["changed"][0])

    return result2

def get_ynab_budgets_raw():
    budgets = []
    if get_ynab_key() is not None:
        r = requests.get(YNAB_BASE + "/budgets", \
            headers={"Authorization": "Bearer {}".format(get_ynab_key())})
        budgets = r.json()["data"]["budgets"]
        budgets = sorted(budgets, key=lambda x: x["last_modified_on"],
                         reverse=True)
    return budgets

def get_ynab_budgets():
    data = []
    budgets = get_ynab_budgets_raw()
    for b in budgets:
        data.append({"label": b["name"], "value": b["id"]})
    return data

def get_ynab_accounts(budget=None):
    if budget is None:
        budget = get_default_budget()
    r = requests.get(YNAB_BASE + "/budgets/{}/accounts".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())})
    results = r.json()["data"]["accounts"]
    data1 = []
    data2 = []
    data3 = []
    for a in results:
        if a["closed"]:
            data3.append({"label": "- " + a["name"], "value": a["id"],
                          "alias": a["name"]})
        elif a["on_budget"]:
            data1.append({"label": "- " + a["name"], "value": a["id"],
                          "alias": a["name"]})
        else:
            data2.append({"label": "- " + a["name"], "value": a["id"],
                          "alias": a["name"]})
    data1 = sorted(data1, key=lambda x: x["label"])
    data2 = sorted(data2, key=lambda x: x["label"])
    data3 = sorted(data3, key=lambda x: x["label"])
    return [
        {"label": "Budget", "values": data1},
        {"label": "Tracking", "values": data2},
        {"label": "Closed", "values": data3},
    ]

def get_ynab_categories(budget=None, trigger=False):
    if budget is None:
        budget = get_default_budget()
    r = requests.get(YNAB_BASE + "/budgets/{}/categories".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())})
    results = r.json()["data"]["category_groups"]
    if trigger:
        data = [{"label": "(all categories)", "value": ""}]
    else:
        data = [{"label": "(automatic)", "value": ""}]
    for g in results:
        groupvalues = []
        for c in g["categories"]:
            groupvalues.append({"label": "- " + c["name"], "value": c["id"],
                                "alias1": g["name"] + "|" + c["name"],
                                "alias2": c["name"]})
        if g["name"] == "Internal Master Category":
            data.insert(1, {"label": g["name"], "values": groupvalues})
        else:
            data.append({"label": g["name"], "values": groupvalues})
    return data


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

def get_default_budget():
    """ Returns the default YNAB budget uuid """
    global YNAB_DEFAULT_BUDGET
    try:
        if YNAB_DEFAULT_BUDGET is None:
            key = DSCLIENT.key("config", "ynab_default_budget")
            entity = DSCLIENT.get(key)
            if entity is not None:
                YNAB_DEFAULT_BUDGET = entity["value"]
    except:
        traceback.print_exc()
    return YNAB_DEFAULT_BUDGET

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
    budgets = get_ynab_budgets()
    defaultbudget = get_default_budget()
    return render_template("main.html",\
        iftttkeyset=iftttkeyset, ynabkeyset=ynabkeyset,\
        budgets=budgets, defaultbudget=defaultbudget)

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

@app.route("/make_default", methods=["GET"])
def make_default():
    global YNAB_DEFAULT_BUDGET
    try:
        cookie = request.cookies.get('session')
        if cookie is None or cookie != get_session_key():
            return render_template("message.html", msgtype="danger", msg=\
                "Invalid request: session cookie not set or not valid")

        budgetid = request.args["budget"]
        uuid.UUID(budgetid) # check if valid uuid

        entity = datastore.Entity(key=DSCLIENT.key("config",
                                                   "ynab_default_budget"))
        entity["value"] = budgetid
        DSCLIENT.put(entity)
        YNAB_DEFAULT_BUDGET = budgetid

        return redirect("/")
    except:
        traceback.print_exc()
        return render_template("message.html", msgtype="danger", msg=\
            'Error while processing default budget. See the logs. <br><br>'\
            '<a href="/">Click here to return home</a>')


if __name__ == "__main__":
    app.run(host="localhost", port=18000, debug=True)
