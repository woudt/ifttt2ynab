# pylint: disable=bare-except,global-statement

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

# pylint: disable=invalid-name
app = Flask(__name__)
# pylint: enable=invalid-name

DSCLIENT = datastore.Client()

IFTTT_SERVICE_KEY = None
YNAB_ACCOUNT_KEY = None
YNAB_DEFAULT_BUDGET = None
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
                "triggers": {
                    "ynab_month_updated": {
                        "budget": "TEST",
                    }
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


@app.route("/ifttt/v1/actions/ynab_create/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/actions/ynab_adjust_balance/fields/"\
           "budget/options", methods=["POST"])
@app.route("/ifttt/v1/triggers/ynab_month_updated/fields/"\
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
def ifttt_category_options():
    """ Option values for the category field """
    if "IFTTT-Service-Key" not in request.headers or \
            request.headers["IFTTT-Service-Key"] != get_ifttt_key():
        return json.dumps({"errors": [{"message": "Invalid key"}]}), 401
    try:
        if get_default_budget() is None:
            return json.dumps({"data": [{"label": "ERROR no default budget",
                                         "value": ""}]})
        data = get_ynab_categories()
        return json.dumps({"data": data})
    except:
        traceback.print_exc()
        return json.dumps({"data": [{"label": "ERROR retrieving YNAB data",
                                     "value": ""}]})


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


@app.route("/ifttt/v1/triggers/ynab_month_updated", methods=["POST"])
def ifttt_month_updated():
    """ Option values for the budget field """
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

        if budget == "TEST":
            budget = get_default_budget()
            if budget is None:
                print("[month_updated] ERROR: default budget not set!")
                return json.dumps({"errors": [{"message": "No default"}]}), 400

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

        entity = DSCLIENT.get(DSCLIENT.key("budget", budget))
        if entity is None:
            print("[month_updated] WARNING: budget not found "+budget)
            results = []
        else:
            months = json.loads(entity["months"])
            if "triggers" not in months:
                triggers = []
            else:
                triggers = months["triggers"]
            if triggerid not in triggers:
                print(triggers)
                print("Adding new trigger: "+triggerid)
                triggers.append(triggerid)
                months["triggers"] = triggers
                entity["months"] = json.dumps(months)
                DSCLIENT.put(entity)

            results = months["changed"]
            for result in results:
                result["created_at"] = arrow.get(result["created_at"])\
                                       .to(timezone).isoformat()

        # ensure at least three updates when testing
        if data["triggerFields"]["budget"] == "TEST" and len(results) < 3:
            update1 = results[0].copy()
            update1["meta"] = update1["meta"].copy()
            update1["meta"]["id"] = "1_" + update1["meta"]["id"]
            update2 = results[0].copy()
            update2["meta"] = update2["meta"].copy()
            update2["meta"]["id"] = "2_" + update2["meta"]["id"]
            results.append(update1)
            results.append(update2)

        print("[month_updated] Found {} updates"
              .format(len(results)))
        return json.dumps({"data": results[:limit]})

    except:
        traceback.print_exc()
        print("[month_updated] ERROR: cannot retrieve transactions")
        return json.dumps({"errors": [{"message": \
                           "Cannot retrieve transactions"}]}), 400

@app.route("/ifttt/v1/triggers/ynab_month_updated/trigger_identity/" +
           "<triggerid>", methods=["DELETE"])
def ifttt_month_updated_delete_trigger(triggerid):
    budget = get_default_budget()
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

@app.route("/cron/ynab", methods=["GET"])
def cron():
    budget = get_default_budget()
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

    triggers = []

    accounts = json.loads(entity["accounts"])
    accounts = process_accounts(accounts,
                                data["accounts"],
                                data["currency_format"],
                                result['server_knowledge'],
                                first,
                                triggers)
    entity["accounts"] = json.dumps(accounts)

    categories = json.loads(entity["categories"])
    categories = process_categories(accounts,
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
                            data["currency_format"],
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

    return json.dumps({
        "config": config,
        "accounts": accounts,
        "categories": categories,
        "month_categories": month_categories,
        "months": months,
        "payees": payees,
        "transactions": transactions,
        "data": result
    })

def process_accounts(old, data, curfmt, knowledge, first, triggers):
    return []

def process_categories(old, data, groupdata, curfmt, knowledge, first,
                       triggers):
    return []

def process_months(old, data, first_month, curfmt, knowledge, first, triggers):
    if not old or "changed" not in old:
        result = {"changed": []}
    else:
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

    # only keep records younger than 1 day
    result2 = {"changed": []}
    if not first: # do not keep anything on first run
        for change in result["changed"]:
            if change["meta"]["timestamp"] > now.timestamp - 86400:
                result2["changed"].append(change)
    # but never delete the last record
    if not result2["changed"] and result["changed"]:
        result2["changed"].append(result["changed"][0])

    return result2

def process_month_categories(old, categories, data, first_month, curfmt,
                             knowledge, first, triggers):
    return []

def process_payees(old, data, curfmt, knowledge, first, triggers):
    return []

def process_transactions(old, accounts, categories, payees, data, curfmt,
                         knowledge, first, triggers):
    return []

def convert_amount(amount, curfmt):
    digits = curfmt["decimal_digits"]
    if digits == 0:
        return "{}".format(amount // 1000)
    elif digits == 1:
        return "{:.1f}".format((amount // 100) / 10)
    elif digits == 2:
        return "{:.2f}".format((amount // 10) / 100)
    else:
        return "{:.3f}".format(amount / 1000)


def get_ynab_budgets():
    data = []
    if get_ynab_key() is not None:
        r = requests.get(YNAB_BASE + "/budgets", \
            headers={"Authorization": "Bearer {}".format(get_ynab_key())})
        budgets = r.json()["data"]["budgets"]
        budgets = sorted(budgets, key=lambda x: x["last_modified_on"],
                         reverse=True)
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

def get_ynab_categories(budget=None):
    if budget is None:
        budget = get_default_budget()
    r = requests.get(YNAB_BASE + "/budgets/{}/categories".format(budget), \
        headers={"Authorization": "Bearer {}".format(get_ynab_key())})
    results = r.json()["data"]["category_groups"]
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
