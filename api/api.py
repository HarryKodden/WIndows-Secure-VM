import os
import sys

from flask import Flask, request, jsonify, abort
from flask_restful import Resource, Api
import requests
import json

from guacapy import Guacamole

from samba.netcmd.main import cache_loader
from samba.netcmd import Command, SuperCommand

Command.show_command_error = lambda self, e: None

class mySambaTool(SuperCommand):
    subcommands = cache_loader()
    subcommands["user"] = None
    subcommands["group"] = None

import subprocess
import random

def unique(email):
    username = email.split('@')[0]
    username = "{}{}".format(username, random.randint(1,1000))
    return username

import string
from random import choice

def createPassword():
    allchar = string.ascii_letters + string.punctuation + string.digits
    return "".join(choice(allchar) for x in range(12))

# LDAP - part

import ldap,ldap.sasl
import ldap.modlist as modlist

ldap_session = None

SAMBA_HOST = os.environ.get('SAMBA_HOST','localhost')
SAMBA_USER = os.environ.get('SAMBA_USER','Administrator')
SAMBA_PASS = os.environ.get('SAMBA_PASS','secret')
SAMBA_REALM = os.environ.get('SAMBA_REALM','example.org')

def lookup_username(email):
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    ldap_session = ldap.initialize('ldap://{}'.format(SAMBA_HOST), trace_level=0)
    ldap_session.start_tls_s()
    ldap_session.protocol_version = 3
    ldap_session.set_option(ldap.OPT_REFERRALS, 0)
    ldap_session.bind_s("{}@{}".format(SAMBA_USER, SAMBA_REALM), SAMBA_PASS)

    base = ''
    for dc in SAMBA_REALM.split('.'):
       if base != '':
          base = base+','
       base = base+"dc={}".format(dc)

    scope = ldap.SCOPE_SUBTREE
    filter = "(&(objectClass=user)(mail=*))"
    attrs = ["*"]

    r = ldap_session.search(base, scope, filter, attrs)
    type, data = ldap_session.result(r, 60)
    ldap_session.unbind_s()

    for u in data:
      (name, attrs) = u
      if attrs and hasattr(attrs, 'has_key') and attrs.has_key('mail') and email in attrs['mail']:
         if hasattr(attrs, 'has_key') and attrs.has_key('sAMAccountName'):
            return attrs['sAMAccountName'][0]

    return None

def lookup_email(username):
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    ldap_session = ldap.initialize('ldap://{}'.format(SAMBA_HOST), trace_level=0)
    ldap_session.start_tls_s()
    ldap_session.protocol_version = 3
    ldap_session.set_option(ldap.OPT_REFERRALS, 0)
    ldap_session.bind_s("{}@{}".format(SAMBA_USER, SAMBA_REALM), SAMBA_PASS)

    base = ''
    for dc in SAMBA_REALM.split('.'):
       if base != '':
          base = base+','
       base = base+"dc={}".format(dc)

    scope = ldap.SCOPE_SUBTREE
    filter = "(&(objectClass=user)(cn=*))"
    attrs = ["*"]

    r = ldap_session.search(base, scope, filter, attrs)
    type, data = ldap_session.result(r, 60)
    ldap_session.unbind_s()

    for u in data:
      (name, attrs) = u
      if attrs and hasattr(attrs, 'has_key') and attrs.has_key('cn') and username in attrs['cn'] and attrs.has_key('mail'):
            return attrs['mail'][0]

    return None

def quacamole_account(email):
    print("Setup Guacamole account")

    c = Guacamole(
        os.environ.get("GUACAMOLE_HOST", "localhost") + ":" + os.environ.get("GUACAMOLE_PORT", "80"),
        os.environ.get("GUACAMOLE_USER", "guadmin"),
        os.environ.get("GUACAMOLE_PASS", "guadmin"),
        method='http',
        url_path='/guacamole', default_datasource=None, verify=True)

    # (delete)/create user in Guacamole registry with actual password...

    connection = os.environ.get("GUACAMOLE_CONNECTION", 1)

    try:
        c.delete_user(email)
    except:
        pass

    c.add_user(payload={
        "username":email,
#       "password":password,
        "attributes":{
                "disabled":"",
                "expired":"",
                "access-window-start":"",
                "access-window-end":"",
                "valid-from":"",
                "valid-until":"",
                "timezone":""
            }
        }
    )

    c.grant_permission(email, payload=[{"op":"add","path":"/connectionPermissions/{}".format(connection),"value":"READ"}])

def samba_user(email, username, password):
    print("update user: {}".format(username))

    result = cmd._run("samba-tool", "user", *[
        'setpassword', username, '--newpassword={}'.format(password),
        '-H', 'ldap://{}'.format(SAMBA_HOST),
        '-U{}%{}'.format(SAMBA_USER, SAMBA_PASS)
    ])

    if result:
        print("User not found, creating")

        result = cmd._run("samba-tool", "user", *[
            'create', username, password,
            '--given-name={}'.format(username),
            '--mail={}'.format(email),
            '-H', 'ldap://{}'.format(SAMBA_HOST),
            '-U{}%{}'.format(SAMBA_USER, SAMBA_PASS)
        ])
        result = cmd._run("samba-tool", "group", *[
            'addmembers', 'Remote Desktop Users', username,
            '-H', 'ldap://{}'.format(SAMBA_HOST),
            '-U{}%{}'.format(SAMBA_USER, SAMBA_PASS)
        ])

cmd = mySambaTool()

app = Flask(__name__)
api = Api(app)

url = os.environ.get("PID_URL", "localhost")

class user(Resource):

    def post(self):
        try:
            if 'user' not in request.json:
               raise Exception("Missing user in request")

            quacamole_account(request.json['user'])

            return jsonify({'status':'ok'})

        except:
            abort(400)


class validate(Resource):

    def post(self):
        try:
            if 'user' not in request.json:
               raise Exception("Missing user in request")

            if 'token' not in request.json:
               raise Exception("Missing token in request")
        except:
            abort(400)

        try:
            email=lookup_email(request.json['user']) or request.json['user']

            params = {'user': email, 'pass': request.json['token']}
            headers = {"content-type": "application/json"}
            r = requests.post(url, params=params, headers=headers)

            if r.status_code == 200:

                data = json.loads(r.text)

                if 'result' not in data:
                    raise Exception("Missing result in response")

                if 'status' not in data['result']:
                    raise Exception("Missing status in response result")

                if not data['result']['status']:
                    raise Exception("Status not ok in result")

                if 'value' not in data['result']:
                    raise Exception("Missing value in response result")

                if not data['result']['value']:
                    raise Exception("value not ok in result")

                # Generate password...
                username = lookup_username(email) or unique(email)
                password = createPassword()

                print('username: ', username)
                print('email: ',email)

                try:
                    samba_user(email, username, password)
                    quacamole_account(email)
                except:
                    raise Exception('Error setting password for user')

                return jsonify({'username':username, 'password': password})

            raise Exception("Error: {}".format(r.status_code))

        except:
            abort(403)

        abort(400)

api.add_resource(validate, '/api/validate')
api.add_resource(user, '/api/user')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 80), debug=True)
