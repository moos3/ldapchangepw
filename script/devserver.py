#!/usr/bin/env python
#:coding=utf-8:

import sys
import os

import argparse

base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path = [base_path] + sys.path

def devserver():
    parser = argparse.ArgumentParser(description='Run the development server')
    parser.add_argument('--settings', metavar='FILE', default=None,
            required=False, help="The settings file")

    parser.add_argument('--host', default='127.0.0.1', help="The host IP to bind to")
    parser.add_argument('--port', type=int, default=5050, help="The port number to bind to")
    parser.add_argument('--debug', action='store_true', default=False, help="Start in debug mode")

    args = parser.parse_args()
    if args.settings:
        os.environ['FLASK_SETTINGS'] = args.settings

    from ldapchangepw import app
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug or app.debug,
    )

if __name__ == '__main__':
    devserver()
