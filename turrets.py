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
from adafruit_servokit import ServoKit

settings = None
hmqtt = None
debug_level = 1
applog = None
turrets = []    # list of Turret Objects
#tur_lock =  Lock()
running = False

# MQTT callback, Mult-Threaded re-entrant
def turretCB(idx, jsonstr):
  global applog, running
  #tur_lock.acquire()    
  t = turrets[idx]
  #print(t)
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
  # build internal args dict with defaults
  margs = {}
  margs['method'] = Move.direct
  margs['pause'] = args.get('pause', t.dfltp)
  if args.get('steps', None):
    margs['method'] = Move.steps
    margs['increment'] = args['steps']
  if args.get('time', None):
    margs['method'] = Move.time
    margs['increment'] = args['time']
  tilt = args.get('tilt', None)
  pan = args.get('pan', None)
  exe = args.get('exec', None)
  if pan:
    t.pan_to(pan, margs)
  tilt = args.get('tilt', None)
  if tilt:
    t.tilt_to(tilt)
  if exe:
    cnt = args.get('count', 1)
    if exe == 1:
      square_zig(t, cnt, margs)
    elif exe == 2:
      circle_zig(t, cnt, margs)
    elif exe == 3:
      diamond_zig(t, cnt, margs)
    elif exe == 4:
      cross_zig(t, cnt, margs)
    elif exe == 5:
      margs['lines'] = args.get('lines', 4)
      horizontal_zig(t, cnt, margs)
    elif exe == 6:
      margs['lines'] = args.get('lines', 4)
      vertical_zig(t, cnt, margs)
    elif exe == 7:
      random_zig(t, cnt, margs)
    else:
      app.warn(f'unknown exec pattern: {exec}')
      
  hmqtt.update_angles(idx, t.pan_angle, t.tilt_angle)
  hmqtt.update_status(idx, 'OK')
  t.stop()
  #tur_lock.release()
  
def square_zig(t, cnt, opts):
  print(opts)
  # pan range
  xmin = t.minx # + 10
  xmax = t.maxx # - 10
  # tilt range
  ymin = t.miny # + 20
  ymax = t.maxy # - 20

  # start at lower,left
  t.laser(False)
  t.pan_to(90, opts)
  t.tilt_to(90, opts)
  t.laser(True)
  time.sleep(0.2)
  for i in range(0, cnt):
    if t.state == State.stopping:
      applog.info('exec square canceled')
      break
    # to upper, left
    t.tilt_to(ymax, opts)
    # to upper, right
    t.pan_to(xmax, opts)
    # to lower, right
    t.tilt_to(ymin, opts)
    # to lower, left
    t.pan_to(xmin, opts)
  t.pan_to(90, opts)
  t.tilt_to(90, opts)
  t.laser(False)
    
def circle_zig(t, cnt, opts):
  pass
  
def diamond_zig(t, cnt, opts):
  pass
  
def cross_zig(t, cnt, opts):
  pass
  
def horizontal_zig(t, cnt, opts):
  #print(f' inopts: {opts}')
  # pan range
  xmin = t.minx
  xmax = t.maxx
  xrng = xmax - xmin
  # tilt range
  ymin = t.miny
  ymax = t.maxy
  yrng = ymax - ymin
  lines = int(opts.get('lines', 4))
  # divide total time by lines 
  if opts['method'] == Move.time:
    opts['increment'] /=  lines
  if opts['method'] == Move.steps:
      opts['method'] = Move.direct
  #print(f'outopts: {opts}')
  for i in range(0, cnt):
    #print(f"Horizontal {i}")
    if i % 2 == 0:
      x = xmin
      y = ymin
      t.pan_to(x)
      t.tilt_to(y)
      t.laser(True)
      sdir = 'right'
      ystepd = int(yrng / lines)
      for s in range(0, lines):
        y += ystepd
        if sdir == 'right':
          #print(f'step+ {s} to {xmax} {y} by {ystepd}')
          t.line_to(xmax, y, opts)
          sdir = 'left'
        elif sdir == 'left':
          #print(f'step- {s} to {xmin} {y} by {ystepd}')
          t.line_to(xmin, y, opts)
          sdir = 'right'       
      t.laser(False)
    else:
      #print('reverse horizontal')
      x = xmax
      y = ymax
      t.pan_to(x)
      t.tilt_to(y)
      t.laser(True)
      sdir = 'left'
      ystepd = int(yrng / lines)
      for s in range(0, lines):
        y -= ystepd
        if sdir == 'left':
          #print(f'step- {s} to {xmin} {y} by {ystepd}')
          t.line_to(xmin, y, opts)
          sdir = 'right'
        elif sdir == 'right':
          #print(f'step+ {s} to {xmax} {y} by {ystepd}')
          t.line_to(xmax, y, opts)
          sdir = 'left'       
      t.laser(False)
  opts['pause'] = 0.1
  t.line_to(90, 90, opts)
  #t.pan_to(90, opts)
  #t.tilt_to(90, opts)
  
  
def vertical_zig(t, cnt, opts):
  #print(f' inopts: {opts}')
  # pan range
  xmin = t.minx
  xmax = t.maxx
  xrng = xmax - xmin
  # tilt range
  ymin = t.miny
  ymax = t.maxy
  yrng = ymax - ymin
  lines = int(opts.get('lines', 4))
  # divide total time by lines 
  if opts['method'] == Move.time:
    opts['increment'] /=  lines
  if opts['method'] == Move.steps:
      opts['method'] = Move.direct
  #print(f'outopts: {opts}')
  for i in range(0, cnt):
    if i & 1 == 0:
      x = xmin
      y = ymin
      t.pan_to(x)
      t.tilt_to(y)
      t.laser(True)
      sdir = 'up'
      xstepd = int(xrng / lines)
      for s in range(0, lines):
        x += xstepd
        if sdir == 'up':
          #print(f'step+ {s} to {x} {ymax}')
          t.line_to(x, ymax, opts)
          sdir = 'down'
        elif sdir == 'down':
          #print(f'step- {s} to {x} {ymin}')
          t.line_to(x, ymin, opts)
          sdir = 'up'       
      t.laser(False)
    else:
      #print('starting vert reverse')
      x = xmax
      y = ymax
      t.pan_to(x)
      t.tilt_to(y)
      t.laser(True)
      sdir = 'down'
      xstepd = int(xrng / lines)
      for s in range(0, lines):
        x -= xstepd
        if sdir == 'up':
          #print(f'step+ {s} to {x} {ymax}')
          t.line_to(x, ymax, opts)
          sdir = 'down'
        elif sdir == 'down':
          #print(f'step- {s} to {x} {ymin}')
          t.line_to(x, ymin, opts)
          sdir = 'up'       
      t.laser(False)
  opts['pause'] = 0.1
  t.line_to(90, 90, opts)
  #t.pan_to(90, opts)
  #t.tilt_to(90, opts)
    
  
def random_zig(t, cnt, opts):
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
  # init turrets from settings. Do any of the turret
  # use PCA9685, if so, we init that device here.
  init_pca = False
  kit = None
  for t in settings.turrets:
    if t.get('laser_pin', False):
      init_pca = True
  if init_pca:
    applog.info('initializing PCA9685')
    kit = ServoKit(channels=16)
    
  # init mqtt server connection
  hmqtt = Homie_MQTT(settings, turretCB)
  
  for i in range(0, len(settings.turrets)):
     turrets.append(Turret(settings.turrets[i], kit, applog))
   
  #hmqtt = Homie_MQTT(settings, 
  #                  turretCB)
                    
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
