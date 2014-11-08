import os
import sys
import site

site.addsitedir('/var/www/venvs/ldapchangepw/lib/python2.5/site-packages')

# Needed for trac repository
os.environ['FLASK_SETTINGS'] = '/var/www/vhosts/ldapchangepw/settings_production.py'
os.environ['SCRIPT_NAME'] = '/admin/password_change/'
sys.path = ['/var/www/vhosts/ldapchangepw/'] + sys.path

import ldapchangepw
application = ldapchangepw.app
