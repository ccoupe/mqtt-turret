#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys
import json
import argparse
import warnings
from datetime import datetime
import time
from threading import Lock, Thread
import socket
import os
import platform
from subprocess import Popen
from lib.Settings import Settings
from lib.Turret import Turret, State, Move
from lib.Homie_MQTT import Homie_MQTT
import logging
import logging.handlers
import atexit

import RPi.GPIO as GPIO

settings = None
hmqtt = None
debug_level = 1
applog = None
turrets = []    # list of Turret Objects
#tur_lock =  Lock()
running = False

# MQTT callback, Mult-Threaded re-entrant
def turretCB(turreti, jsonstr):
  global hmqtt, applog, tur_lock, running
  #tur_lock.acquire()    
  t = turrets[turreti - 1]
  print(t)
  if jsonstr == 'stop' and t.stopped == False:
    # async kill
    t.stop()
    return
  t.begin()
  args = json.loads(jsonstr)
  pwr = args.get('power', None)
  if pwr:
    p = int(pwr)
    if p == 0:
      t.laser(False)
      hmqtt.update_power(p)
    elif p == 100:
      t.laser(True)
      hmqtt.update_power(p)
    else:
      applog.warn(f'bad power: {pwr}')
  pause = args.get('pause', 0.50)
  pan = args.get('pan', None)
  if pan:
    t.pan_to(pan)
    if pause:
      time.sleep(pause)
  tilt = args.get('tilt', None)
  if tilt:
    t.tilt_to(tilt)
    if pause:
      time.sleep(pause)

  exec = args.get('exec', None)
  if exec:
    cnt = args.get('count', 1)
    if exec == 1:
      square_zig(t, cnt, pause)
    elif exec == 2:
      circle_zig(t, cnt, pause)
    elif exec == 3:
      diamond_zig(t, cnt, pause)
    elif exec == 4:
      cross_zig(t, cnt, pause)
    elif exec == 5
      horizontal_zig(t, cnt, pause)
    elif exec == 6:
      vertical_zig(t, cnt, pause)
    elif exec == 7:
      random_zig(t, cnt, pause)
    else:
      app.warn(f'unknown exec pattern: {exec}')
      
  hmqtt.update_angles(t.pan_angle, t.tilt_angle)
  hmqtt.update_status('OK')
  t.stop()
  #tur_lock.release()
  
def square_zig(t, cnt, pause):
  # pan range
  xmin = t.minx + 10
  xmax = t.maxx - 10
  pan_range = xmax - xmin
  # tilt range
  ymin = t.miny + 20
  ymax = t.maxy - 20

  # start at lower,left
  t.laser(False)
  t.pan_to(90)
  t.tilt_to(90)
  t.laser(True)
  time.sleep(0.2)
  for i in range(0, cnt):
    if t.state == State.stopping:
      applog.info('exec square canceled')
      break
    # to upper, left
    t.tilt_to(ymax, {'pause': pause})
    # to upper, right
    t.pan_to(xmax, {'pause': pause})
    # to lower, right
    t.tilt_to(ymin, {'pause': pause})
    # to lower, left
    t.pan_to(xmin, {'pause': pause})
  t.pan_to(90)
  t.tilt_to(90)
  time.sleep(0.5)
  t.laser(False)
    
def circle_zig(t, cnt, pause):
  pass
  
def diamond_zig(t, cnt, pause):
  pass
  
def cross_zig(t, cnt, pause):
  pass
  
def horizontal_zig(t, cnt, pause):
  pass
  
def vertical_zig(t, cnt, pause):
  pass
  
def random_zig(t, cnt, pause):
  pass
  
def cleanup():
  global turrets
  for t in turrets:
    t.stop()
  GPIO.cleanup()
    
def main():
  global settings, hmqtt, applog, turrets
  # process cmdline arguments
  loglevels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
  ap = argparse.ArgumentParser()
  ap.add_argument("-c", "--conf", required=True, type=str,
    help="path and name of the json configuration file")
  ap.add_argument("-s", "--syslog", action = 'store_true',
    default=False, help="use syslog")
  ap.add_argument("-d", "--debug", action='store', type=int, default='3',
    nargs='?', help="debug level, default is 3")
  args = vars(ap.parse_args())
  
  # logging setup
  applog = logging.getLogger('mqttlaser')
  #applog.setLevel(args['log'])
  if args['syslog']:
    applog.setLevel(logging.DEBUG)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    # formatter for syslog (no date/time or appname. Just  msg.
    formatter = logging.Formatter('%(name)s-%(levelname)-5s: %(message)-40s')
    handler.setFormatter(formatter)
    applog.addHandler(handler)
  else:
    logging.basicConfig(level=logging.DEBUG,datefmt="%H:%M:%S",format='%(asctime)s %(levelname)-5s %(message)-40s')

  #GPIO.setmode(GPIO.BOARD)

  settings = Settings(args["conf"], 
                      applog)
  # init turrets from settings
  for t in settings.turrets:
     turrets.append(Turret(t, applog))

  hmqtt = Homie_MQTT(settings, 
                    turretCB)
                    
  settings.print()
  
  # fix debug levels
  if args['debug'] == None:
    debug_level = 3
  else:
    debug_level = args['debug']
    
  atexit.register(cleanup)
  # All we do now is loop over a 5 minute delay
  # and let the threads work.
  while True:
    time.sleep(5 * 60)
         
if __name__ == '__main__':
  sys.exit(main())
