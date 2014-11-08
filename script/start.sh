#!/bin/bash
HOMEDIR="/var/www/"
VENVDIR="$HOMEDIR/venvs/ldapchangepw"

# Load venv
. $VENVDIR/bin/activate


HOST="127.0.0.1"
PORT=10023
BASEDIR="$HOMEDIR/vhosts/ldapchangepw"
PIDFILE="$BASEDIR/tmp/gunicorn.pid"
LOGFILE="$BASEDIR/logs/gunicorn.log"
APPMODULE="application:application"
DAEMONSCRIPT="gunicorn"
DAEMONOPTIONS="--pid=$PIDFILE --log-file=$LOGFILE --bind=$HOST:$PORT --workers=1 --daemon $APPMODULE"

case "$1" in
  start)
    mkdir -p $BASEDIR/logs
    mkdir -p $BASEDIR/tmp
    $DAEMONSCRIPT $DAEMONOPTIONS
    ;;
  stop)
    kill `cat -- $PIDFILE`
    ;;
  reload)
    kill -s HUP `cat -- $PIDFILE`
    ;;
  restart)
    kill `cat -- $PIDFILE`
    sleep 3
    $DAEMONSCRIPT $DAEMONOPTIONS
    ;;
  *)
    echo "Usage: start.sh {start|stop|restart}"
    exit 1
esac

exit 0
