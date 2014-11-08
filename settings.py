#:coding=utf-8:

DEBUG=False

SECRET_KEY='SecretKey'
ADMIN_MAIL=('admin@example.com',)

LDAP_BASEDN='ou=User,dc=example,dc=com'

LDAP_PW_METHOD='crypt' # One of md5, sha, crypt

LOG_FILE='./ldapchangepw.log'
