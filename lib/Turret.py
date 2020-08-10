#
# Class for Laser Turret
# has two servos (MG90 or SG90) for pan and tilt and a laser diode.
# Derived from Explaining Computers (h/t) 
# Uses GPIO (aka BCM) pin numbers (because AdaFruit)
#
# TODO: use pwm correction values to get full range out of the servo
# mine only go 20..160 or there about.
# 
import RPi.GPIO as GPIO
from adafruit_servokit import ServoKit
import time
import enum 

class State(enum.Enum): 
  stopped = 0
  running = 1
  stopping = 2

class Move(enum.Enum):
  direct = 0
  time = 1
  steps = 2

class Turret:

  def __init__(self, dic, kit, log):
    self.log = log
    self.kit = kit
    self.pca = dic['hw']
    self.laserp = dic['laser_pin']
    self.panp = dic['pan_pin']    # or PCA9685 channel num
    self.tiltp = dic['tilt_pin']  # or PCA9685 channel num
    self.dfltp = dic.get('delay',0.25)
    self.pan_angle = 0
    self.tilt_angle = 0
    self.power = False
    self.state = State.stopped
    # max and min depend on individual servos, mounting scheme and where the
    # thing is deployed.  These defaults work for mine.
    self.minx = dic.get('pan_min', 30)
    self.maxx = dic.get('pan_max', 150)
    self.miny = dic.get('tilt_min', 50)
    self.maxy = dic.get('tilt_max',180)
    GPIO.setup(self.laserp,GPIO.OUT)
    if self.pca is None:
      # Use less precise software pwm
      GPIO.setup(self.tiltp,GPIO.OUT)
      self.servoTilt = GPIO.PWM(self.tiltp,50)  # pulse 50Hz
      GPIO.setup(self.panp,GPIO.OUT)
      self.servoPan = GPIO.PWM(self.panp,50)
      self.servoTilt.start(0)
      self.servoPan.start(0)
      self.pause = 0.25
    else:
      # init Adafruit PCA9685 library - moved to main()
      # self.kit = ServoKit(channels=16)
      # this gets close to mount instablity. Visually, at least.
      self.pause = 0.1
      
  def move_it(self, servo, angle, pause):
    if self.state == State.stopping:
      return
    if self.pca is None:
      servo.ChangeDutyCycle(2+(angle/18))
      time.sleep(pause)
      servo.ChangeDutyCycle(0)
    else:
      servo.angle = angle
      time.sleep(pause)
  
  def _set_pan(self, angle):
    self.pan_angle = angle
    
  def _get_pan(self):
    return(self.pan_angle)
    
  def _set_tilt(self, angle):
    self.tilt_angle = angle
    
  def _get_tilt(self):
    return self.tilt_angle
  
  def move_to(self, servo, get_angle, set_angle, angle, pause, meth, incr):
    if meth == Move.direct:
      self.move_it(servo, angle, pause)
      set_angle(angle)
    elif meth == Move.steps:
      beg_angle = get_angle()
      distance = int(angle - beg_angle)
      if distance > 0:
        i = beg_angle
        while i < (angle - incr):
          i += incr
          set_angle(i)
          #print('mv+ to', i)
          self.move_it(servo, get_angle(), pause)
        #print('mv+ final',angle)
        self.move_it(servo, angle, pause)
      else:
        i = beg_angle
        while i > (angle + incr):
          i -= incr
          set_angle(i)
          #print('mv+ to', i)
          self.move_it(servo, get_angle(), pause)
        #print('mv+ final',angle)
        self.move_it(servo, angle, pause)
      set_angle(angle)
    elif meth == Move.time:
      # The 'incr' arg has the time in seconds to execute the whole move.
      # Smoothness (ns) depends on
      # distance and time allowed. Difficult computation. 8 is a good
      # value for 1 or 2 sec. 2 is a nice value for 5 sec.
      incr -= self.dfltp
      ns = 10
      if incr > 0.5 and incr <= 2:
        ns = 8
      elif incr > 2 and incr <= 4:
        ns = 4
      elif incr > 4:
        ns = 2
      beg_angle = get_angle()
      distance = int(angle - beg_angle)
      steps = abs(int(distance / ns))
      print('distance', distance,'deadline:', incr, 'steps', steps)
      if steps <= 1:
        # just do one step and wait
        self.move_it(servo, angle, incr)
        set_angle(angle)
      else:
        if distance > 0:
          # rotate clockwise
          t_s = incr / steps
          i = 1
          while i < steps:
            d = beg_angle+(i * ns)
            #print(f'tm+ to {d} {t_s}')
            self.move_it(servo, d, t_s)
            set_angle(d)
            i += 1
          #print(f'tm+ final {angle}')
          self.move_it(servo, angle, pause)
          set_angle(angle)
        else:
          # counter clockwise (aka anti-clockwise)
          t_s = incr / steps
          i = 1
          while i < steps:
            d = beg_angle-(i * ns)
            #print(f'tm- to {d} {t_s}')
            self.move_it(servo, d, t_s)
            set_angle(d)
            i += 1
          #print(f'tm- final {angle}')
          self.move_it(servo, angle, pause)
          set_angle(angle)
            
            
        
     
  def pan_to(self, angle, opts={}):
    #print(f'pan_to {angle}, from {self.pan_angle}')
    meth = opts.get('method', Move.direct)
    pause = opts.get('pause',self.dfltp)
    incr = opts.get('increment', 10)
    if meth == Move.time:
      incr = opts.get('deadline',1)
    if self.state == State.stopping:
      return
    self.move_to(self.kit.servo[self.panp], self._get_pan, self._set_pan, angle, pause, meth, incr)
    return         
      
  def tilt_to(self, angle, opts={}):
    #print(f'tilt_to {angle} from {self.tilt_angle}')
    if self.state == State.stopping:
      return
    if angle > self.maxy:
      angle = self.maxy
    if angle < self.miny:
      angle = self.miny
    meth = opts.get('method', Move.direct)
    pause = opts.get('pause',self.dfltp)
    incr = opts.get('increment', 10)
    if meth == Move.time:
      incr = opts.get('deadline',1)
    if self.state == State.stopping:
      return
    self.move_to(self.kit.servo[self.tiltp], self._get_tilt, self._set_tilt, angle, pause, meth, incr)
    return    
  
  def laser(self, tf):
    if tf == True:
      GPIO.output(self.laserp, GPIO.HIGH)
      self.power = 100
    else:
      GPIO.output(self.laserp, GPIO.LOW)
      self.power = 0
      
  def begin(self):
    #print('begining turret', self.state)
    self.state = State.running
    if self.pca is None:
      self.servoTilt.start(0)
      self.servoPan.start(0)
    
  def cancel(self):
    if self.state != State.stopped:
      self.state = State.stopping

  def stop(self):
    #print('stopping turret', self.state)
    self.state = State.stopped
    if self.pca is None:
      self.servoPan.stop()
      self.servoTilt.stop()
    GPIO.output(self.laserp, GPIO.LOW)
    
  # draw like methods
  def line_to(self, x, y, opts):
    meth = opts.get('method', Move.direct)
    pause = opts.get('pause',self.dfltp)
    incr = opts.get('increment', 10)
    if meth == Move.time:
      incr = opts.get('deadline',1)
    if self.state == State.stopping:
      return
    ydist = abs(y - self.tilt_angle)
    xdist = abs(x - self.pan_angle)
    slope = (self.tilt_angle - y) / (self.pan_angle - x)
    print(f'line_to from {self.pan_angle},{self.tilt_angle} to {x},{y} slope {slope} with {xdist}, {ydist}')
    xbegp = self.pan_angle
    ybegp = self.tilt_angle
    xp = xbegp
    yp = ybegp
    servoP = self.kit.servo[self.panp]
    servoT = self.kit.servo[self.tiltp]
    for i in range(0, xdist):
      xp = xbegp + i
      xp = min(xp, self.maxx)
      yp = ybegp + int(i * slope)
      yp = min(yp, self.maxy)
      print(i, xp, yp, i*slope)
      #self.pan_to(xp , args)
      #self.tilt_to(yp, args)
      self.move_to(servoP, self._get_pan, self._set_pan, xp, pause, meth, incr)
      self.move_to(servoT, self._get_tilt, self._set_tilt, yp, pause, meth, incr)
    # issue final move
    print('f ', x, y)
    #self.pan_to(x, opts)
    #self.tilt_to(y, opts)
    self.move_to(servoP, self._get_pan, self._set_pan, x, pause, meth, incr)
    self.move_to(servoT, self._get_tilt, self._set_tilt, y, pause, meth, incr)


if __name__ == '__main__':
  # Pins are GPIO, aka BCM. Not board.
  kit = ServoKit(channels=16)
  tdict = {"hw": True, 'laser_pin': 17, 'pan_pin': 0, 'tilt_pin': 1, 'pan_min': 0,
      'pan_max': 180, 'tilt_min': 77, 'tilt_max': 180}
  #tdict = {"hw": True, 'laser_pin': 17, 'pan_pin': 15, 'tilt_pin': 1}
  t = Turret(tdict, kit, None)
  # start Centered
  t.begin()
  t.pan_to(90)
  t.tilt_to(90)
  while True:
    ap = 0
    at = 0
    pp = input('Pan  angle between 0 & 180: ')
    if pp == 'q' or pp == 'quit':
      break
    if len(pp) > 0:
      ap = float(pp)
      t.begin()
      s = time.monotonic()
      #t.pan_to(ap)
      t.pan_to(ap, {'method': Move.steps, 'pause': 0.2})
      #t.pan_to(ap, {'method': Move.time, 'deadline': 3})
      t.stop()
      e = time.monotonic()
      print('time:', e - s)
    
    tp = input('Tilt angle between 0 & 180: ')
    if tp == 'q' or tp == 'quit':
      break
    if len(tp) > 0:
      at = float(tp)
      t.begin()
      #t.tilt_to(at)
      t.tilt_to(at, {'method': Move.steps, 'increment': 7, 'pause': 0.1})
      t.stop()

  t.stop()
  GPIO.cleanup()
