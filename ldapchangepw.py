#:coding=utf-8:

import ldap
import time
import logging
import decimal
import simplejson
import datetime
import wtforms
import yaml
from wtforms import validators
from flask import (
    Flask, request, render_template,
    flash, g
)
with open('app.yml','r') as ymlfile:
    cfg = yaml.load(ymlfile)

#========= Default Settings ================
DEBUG=cfg['logging']['debug']

SECRET_KEY=cfg['secret_key']

ADMIN_MAIL=()
SMTP_HOST=cfg['mail']['smtp_host']
SMTP_PORT=cfg['mail']['port']
SERVER_EMAIL=cfg['mail']['server_email']

LDAP_HOST=cfg['ldap']['host']
LDAP_PORT=cfg['ldap']['port']
LDAP_BASEDN=cfg['ldap']['base_dn']
LDAP_SEARCH_FILTER=cfg['ldap']['search_filter']
LDAP_LOGIN_FIELD=cfg['ldap']['login_field']
LDAP_USE_LDAPS=cfg['ldap']['use_ldaps']
LDAP_PW_METHOD=cfg['ldap']['pw_method'] # One of md5, sha, crypt

LOG_FILE=None
LOG_BACKUP_SIZE=1024*1024 # 1MB
LOG_BACKUP_COUNT=5

#========= Setup ================

app = Flask(__name__)
app.config.from_object(__name__)
# Import config from settings file with FLASK_SETTINGS environment variable
# or --settings on the devserver
app.config.from_envvar('FLASK_SETTINGS', silent=True)

#========= Logging ================

class SafeJSONEncoder(simplejson.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types
    and performs some extra javascript escaping.
    """
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return o.isoformat()
        elif isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(str(o))
        else:
            return super(SafeJSONEncoder, self).default(o)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return "%s %s %s" % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)), # 19 chars
            ("[%s]" % record.levelname).rjust(9), # 9 chars
            simplejson.dumps({
                "msg": record.msg if isinstance(record.msg, basestring) else repr(record.msg),
                "levelname": record.levelname,
                "args": record.args,
                "created": record.created,
            }), #msg starts at pos #30
        )

if not app.debug:
    app.logger.setLevel(logging.INFO)

    # Production logging
    if app.config['LOG_FILE']:
        # Max 5MB of logs
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=app.config['LOG_BACKUP_SIZE'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        handler.setFormatter(JSONFormatter())
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

        @app.after_request
        def flush_log(response):
            handler.flush()
            return response

    if (app.config['SMTP_HOST'] and app.config['SMTP_PORT'] and
            app.config['SERVER_EMAIL'] and app.config['ADMIN_MAIL']):
        mail_handler = logging.SMTPHandler(
            "%s:%s" % (app.config['SMTP_HOST'], app.config['SMTP_PORT']),
            app.config['SERVER_EMAIL'],
            app.config['ADMIN_MAIL'],
            '[ldapchangepw] Error'
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
else:
    app.logger.handlers[0].setFormatter(JSONFormatter())

#========= LDAP Connection ================

def connect_ldap():
    return ldap.initialize("%s://%s:%s" % (
        'ldaps' if app.config['LDAP_USE_LDAPS'] else 'ldap',
        app.config['LDAP_HOST'],
        app.config['LDAP_PORT'],
    ))

@app.before_request
def before_request():
    g.ldap = connect_ldap()

@app.after_request
def after_request(response):
    g.ldap.unbind()
    return response

#========= Views ================

class PasswordChangeForm(wtforms.Form):
    username = wtforms.TextField(u'usernmae',
        [validators.Required(message=u'Please enter a username')])
    oldpassword = wtforms.PasswordField(u'Current Password',
        [validators.Required(message=u'Please enter the current password')])
    password = wtforms.PasswordField(u'Password',
        [validators.Required(message=u'Please enter a password')])
    password2 = wtforms.PasswordField(u'Password confirmation',
        [validators.EqualTo('password',
             message=u'Password and confirmation does not match')])

@app.route('/', methods=['GET', 'POST'])
def index():
    form = PasswordChangeForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # Find user
            try:
                search_results = g.ldap.search_s(
                    app.config['LDAP_BASEDN'],
                    ldap.SCOPE_SUBTREE,
                    app.config['LDAP_SEARCH_FILTER'],
                    [app.config['LDAP_LOGIN_FIELD']],
                )
            except ldap.LDAPError,e:
                search_results=[]
                if not isinstance(e, ldap.NO_SUCH_OBJECT):
                    raise
            user_dn = None
            for dn, data in search_results:
                field = data.get(app.config['LDAP_LOGIN_FIELD'])
                if not isinstance(field, list):
                    field = [field]
                for item in field:
                    if item == request.form['username']:
                        user_dn = dn
                        break
            if user_dn:
                changed=False
                try:
                    # login (Bind) user
                    g.ldap.simple_bind_s(user_dn, request.form['oldpassword'])
                    # Change PW
                    try:
                        g.ldap.passwd_s(user_dn, request.form['oldpassword'], request.form['password'])
                        changed=True
                    except g.ldap.UNWILLING_TO_PREFORM:
                        changed=False

                except ldap.LDAPError,e:
                    if isinstance(e, ldap.INVALID_CREDENTIALS):
                        app.logger.warning(e, {
                            'type': 'password_mismatch',
                            'username': request.form.get('username'),
                            'user_agent': str(request.user_agent),
                            'route': list(request.access_route),
                        })
                    if isinstance(e, ldap.UNWILLING_TO_PERFORM):
                        app.logger.error(e, {
                            'type': 'permission_denied',
                            'username': request.form.get('username'),
                            'user_agent': str(request.user_agent),
                            'route': list(request.access_route),
                        })

                if changed:
                    flash(u"Password was changed! It takes a little time to reflect, please consent.", "info")
                    # TODO: Mail user
                    app.logger.info("success", {
                        'type': 'success',
                        'username': request.form.get('username'),
                        'user_agent': str(request.user_agent),
                        'route': list(request.access_route),
                    })
                else:
                    flash(u"Username or password is incorrect", "error")

            else:
                flash(u"Username or passwor is incorrect", "error")
                app.logger.warning("warning", {
                    'type': 'user_not_found',
                    'username': request.form.get('username'),
                    'user_agent': str(request.user_agent),
                    'route': list(request.access_route),
                })
    return render_template('index.html', form=form)
