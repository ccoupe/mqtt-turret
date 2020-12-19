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
import math
import random

settings = None
hmqtt = None
debug_level = 1
applog = None
turrets = []    # list of Turret Objects
tur_locks =  []
running = False

# MQTT callback, Mult-Threaded re-entrant
def turretCB(idx, jsonstr):
  global applog, running, turrets, tur_locks, hmqtt
  t = turrets[idx]
  #applog.info(f'locking turret {idx} {t}')
  #tur_locks[idx].aquire()
  applog.info(f'command {jsonstr}')
  if jsonstr == 'stop':
    if t.state == State.running:
      # async kill
      t.cancel()
    return
  elif jsonstr == 'manual':
    t1 = {'min_x': turrets[0].minx, 'max_x': turrets[0].maxx,
      'min_y': turrets[0].miny, 'max_y' : turrets[0].maxy}
    dt = [t1]
    if len(turrets) > 1: 
      t2 = {'min_x': turrets[1].minx, 'max_x': turrets[1].maxx,
        'min_y': turrets[1].miny, 'max_y': turrets[1].maxy}
      dt.append(t2)
    jstr = {'bounds': dt}
    hmqtt.update_status(idx, json.dumps(jstr))
    return
  args = json.loads(jsonstr)
  trk = args.get('cmd', None)
  if trk:
    tracker(t, args)
    return
  applog.info(f'json {args}')
  pwr = args.get('power', None)
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
  viewbx = args.get('begx', None)
  viewby = args.get('begy', None)
  viewex = args.get('endx', None)
  viewey = args.get('endy', None)
  # set viewport if given and it fits
  if viewbx is not None and viewbx >= t.dflt_minx and viewbx <= t.dflt_maxx:
    t.minx = viewbx
  if viewex is not None and viewex >= t.dflt_minx and viewex <= t.dflt_maxx:
    t.maxx = viewex
  if viewby is not None and viewby >= t.dflt_miny and viewby <= t.dlft_maxy:
    t.miny = viewby
  if viewey is not None and viewey >= t.dflt_miny and viewby <= t.dlft_maxy:
    t.maxy = viewey
  # make sure viewport gets restored
  try:
    t.begin()
    if pwr is not None:
      p = int(pwr)
      if p == 0:
        t.laser(False)
        hmqtt.update_power(idx, p)
      elif p == 100:
        t.laser(True)
        hmqtt.update_power(idx, p)
      else:
        applog.warn(f'bad power: {pwr}')
    if pan is not None:
      t.pan_to(pan, margs)
      applog.info(f'pan_to: {pan}')
    if tilt is not None:
      t.tilt_to(tilt, margs)
      applog.info(f'tilt_to: {tilt}')
    if exe:  
      cnt = args.get('count', 1)
      if exe == 1 or exe == 'square':
        square_zig(t, cnt, margs)
      elif exe == 2 or exe == 'circle':
        margs['radius'] = args.get('radius', 40)
        circle_zig(t, cnt, margs)
      elif exe == 3 or exe == 'diamond':
        margs['length'] = args.get('length', 20)
        diamond_zig(t, cnt, margs)
      elif exe == 4 or exe == 'crosshairs':
        margs['length'] = args.get('length', 20)
        cross_zig(t, cnt, margs)
      elif exe == 5 or exe == 'hzig':
        margs['lines'] = args.get('lines', 4)
        horizontal_zig(t, cnt, margs)
      elif exe == 6 or exe == 'vzig':
        margs['lines'] = args.get('lines', 4)
        vertical_zig(t, cnt, margs)
      elif exe == 7 or exe == 'random':
        margs['length'] = args.get('length', 30)
        random_zig(t, cnt, margs)
      else:
        applog.warn(f'unknown exec pattern: {exec}')
  except:
    traceback.print_exc()
  # always restore viewport
  t.minx = t.dflt_minx
  t.maxx = t.dflt_maxx
  t.miny = t.dflt_miny
  t.maxy = t.dflt_maxy
  hmqtt.update_angles(idx, t.pan_angle, t.tilt_angle)
  hmqtt.update_status(idx, 'OK')
  if exe:
    t.stop()
  #applog.debug(f'unlocking {idx}')
  #tur_locks[idx].release()

  
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
  '''
  Draw a circle given a radius. It will be centered in the turret's
  'useful' viewport. To reduced physical movement, precompute the moves. 
  Only save them if they move by one. This also allows us to spread the time evenly.
  
  opts are 'radius', 'method', 'increment', 'pause'
  
  '''
  cparts = []
  cntr = 0

  ctrx = int((t.maxx - t.minx)/2)+t.minx
  ctry = int((t.maxy - t.miny)/2)+t.miny
  r = opts.get('radius', 20)
  if (ctry - r) < t.miny:
    #print('reducing radius to fit')
    r = ctry - t.miny
  #print(f'circle, center = {ctrx},{ctry} r={r}')
  old_x = 0
  old_y = 0
  for a in range(0, 360):
  #for a in [0,90,180,270,360]:
    ar = math.radians(a)
    x = int(ctrx + (math.cos(ar) * r))
    y = int(ctry + (math.sin(ar) * r))
    if x != old_x or y != old_y:
      old_y = y
      old_x = x
      cntr += 1
      cparts.append((x,y))
      #print(f'{cntr}: ang:{a} => {x},{y}')
      
  # deal with the options
  margs = {}
  steps = 1
  if opts['method'] == Move.time:
    margs['pause'] = opts.get('increment', 1) / cntr
  if opts['method'] == Move.steps:
    steps = opts.get('increment', 1)
  t.laser(True)
  for c in range(0, cnt):
    for i in range(0, len(cparts), steps):
      tpl = cparts[i]
      t.point_to(tpl[0], tpl[1], margs)
  t.laser(False)
  t.point_to(90, 90)

  
def diamond_zig(t, cnt, opts):
  '''
  Draw a diamond given a length of one side. It will be centered in the turret's
  'useful' viewport. 
  
  opts are 'length', 'method', 'increment', 'pause'. 
  
  '''
  margs = {}
  length = opts.get('length', 20)
  margs['method'] = opts['method']
  if opts['method'] == Move.steps:
    margs['increment'] = opts.get('increment',1)
  if opts['method'] == Move.time:
    margs['increment'] = opts.get('increment', 0.2) / 4
  margs['pause'] = opts.get('pause',0.2) / 4
  ctrx = int((t.maxx - t.minx)/2)+t.minx
  ctry = int((t.maxy - t.miny)/2)+t.miny
  half = round(length/2)
  print(f'cross: {ctrx}, {ctry} for {half} by {margs}')
  t.point_to(ctrx, ctry + half)
  t.laser(True)
  for i in range(cnt):
    t.line_to(ctrx + half, ctry, margs)
    t.line_to(ctrx, ctry - half, margs)
    t.line_to(ctrx - half, ctry, margs)
    t.line_to(ctrx, ctry + half, margs)
  t.laser(False)
  t.point_to(90,90)
  
def cross_zig(t, cnt, opts):
  '''
  Draw a set of crosshairs given a length. It will be centered in the turret's
  'useful' viewport. 
  
  opts are 'length', 'method', 'increment', 'pause'. 
  
  '''
  margs = {}
  margs['method'] = opts['method']
  if opts['method'] == Move.steps:
    margs['increment'] = opts.get('increment',1)
  if opts['method'] == Move.time:
    margs['increment'] = opts.get('increment', 0.2)
  margs['pause'] = opts.get('pause',0.2) / 2
  length = opts.get('length', 20)
  ctrx = int((t.maxx - t.minx)/2)+t.minx
  ctry = int((t.maxy - t.miny)/2)+t.miny
  half = round(length/2)
  #print(f'cross: {ctrx}, {ctry} for {half}')
  for i in range(cnt):
    # horizontal line
    t.laser(False)
    t.point_to(ctrx - half, ctry)
    t.laser(True)
    t.line_to(ctrx + half, ctry, margs)
    # vertical line
    t.laser(False)
    t.point_to(ctrx, ctry + half)
    t.laser(True)
    t.line_to(ctrx, ctry - half, margs)
    t.laser(False)
    
  t.point_to(90,90)
  

  
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
  '''
  Draw a randwom point cloud in a box given a length of one side. It will be centered in the turret's
  'useful' viewport. 
  
  opts are 'length', 'method', 'increment', 'pause'. 
  For Move.steps 'increment' is the number of points (largish number rcmd)
  For Move.time - the time(sec) is divided by .05 to give the number of points
  pause is per point so a little number like 0.02 is good. For timed loops
  pause > 0.02 will reduce the steps to fit the time.
  
  '''
  margs = {}
  steps = 100
  pause = 0.0
  length = opts.get('length', 20)
  #margs['method'] = opts['method']
  if opts['method'] == Move.steps:
    steps = int(opts.get('increment',100))
    pause = opts.get('pause',0.02)
  elif opts['method'] == Move.time:
     pause = pause = opts.get('pause',0.02)
     steps = int(opts.get('increment', 2) / pause)

  else:
    pause = opts.get('pause',0.02)
    steps = 100
  margs = {'pause': pause}
  ctrx = int((t.maxx - t.minx)/2)+t.minx
  ctry = int((t.maxy - t.miny)/2)+t.miny
  half = round(length/2)
  # origin (draw viewport)
  draw_begx = int(((t.maxx - t.minx) - length) / 2) + t.minx
  draw_begy = int(((t.maxy - t.miny) - length) / 2) + t.miny
  draw_endx = draw_begx + length
  draw_endy = draw_begy + length
  #print(f'inargs {opts}, {margs}')
  #print(f'random: {draw_begx}, {draw_begy} by {length} for {steps}, {pause}')
  t.point_to(ctrx, ctry)
  t.laser(True)
  for i in range(cnt):
    for s in range(steps):
      x = random.randint(draw_begx, draw_endx)
      y = random.randint(draw_begy, draw_endy)
      #print(x,y)
      t.point_to(x, y, margs)
  t.laser(False)
  t.line_to(90, 90, margs)
  
def cleanup():
  global turrets
  for t in turrets:
    t.stop()
  GPIO.cleanup()
    
def main():
  global settings, hmqtt, applog, turrets, tur_locks
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
     tur_locks.append(Lock())
                       
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
    
def tracker(tur, args):
  global applog
  # tur is Turret Object.
  # image 0,0 is Top,Left. Incrment y to move down
  applog.info(f'tracker {args}')
  x = args['x']
  y = args['y']
  ex = args['ex']
  ey = args['ey']
  wid = ex - x
  hgt = ey - y
  area = wid * hgt
  fw = 640
  fh = 480
  tgt_ctr_x = (wid / 2) + x
  tgt_ctr_y = (hgt / 2) + y
  # target is % of camera range
  cam_px = tgt_ctr_x / fw
  cam_py = tgt_ctr_y / fh
  msg = f'area: {area} ctr_x: {tgt_ctr_x} {cam_px}% ctr_y: {tgt_ctr_y} {cam_py}%'
  # That's the view from the camera - now compute angles from the turrets
  # point of view.
  if tur.tpos == 'fc':
    # mirror view, left is right
    nx = tur.max_tx - (cam_px * (tur.max_tx - tur.min_tx))
    tur.pan_to(nx)
    # vertical (tilt) goal:  aim for 4 ft height 
    # Guess: if distance > 3 meter, drop a degree or 5?
    ny = tur.max_ty - (cam_py * (tur.max_ty - tur.min_ty))
    if hgt < 240:
      ny -= 3
    tur.tilt_to(ny)
    applog.info(f'shoot_at {nx},{ny} using {msg}')
  elif tur.tpos == 'br':
    nx = tur.min_tx + (cam_px * (tur.max_tx - tur.min_tx))
    tur.pan_to(nx)
    # my 'bc' turret is two feet high. Needs some +angle to get to 4ft
    # Big image is far way from turret
    ny = ny = tur.max_ty - (cam_py * (tur.max_ty - tur.min_ty))
    if hgt > 240:
      ny -= 3
    tur.tilt_to(ny)
    
  tur.laser(True)


         
if __name__ == '__main__':
  sys.exit(main())
