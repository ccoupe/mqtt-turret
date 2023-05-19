import RPi.GPIO as GPIO
from adafruit_servokit import ServoKit
import time

# compute time to move a distance, say 45 -> 135

d45 = 0.25
d90 = 0.25
d135 = 0.5
kit = ServoKit(channels=16)
kit.servo[0].angle = 90
kit.servo[1].angle = 90
print('45 degree sweep')
time.sleep(1)
st = time.monotonic()
kit.servo[0].angle = 45
time.sleep(d45)
kit.servo[0].angle = 90
time.sleep(d45)
ed = time.monotonic()
print(f'{ed-st} for 45L,45R = {(ed-st)/90}')

kit.servo[0].angle = 35
print('90 degree sweep')
time.sleep(1)
st = time.monotonic()
kit.servo[0].angle = 125
time.sleep(d90)
kit.servo[0].angle = 35
time.sleep(d90)
ed = time.monotonic()
print(f'{ed-st} for 90L,90R = {(ed-st)/180}')

kit.servo[0].angle = 22
print('135 degree sweep')
time.sleep(1)
st = time.monotonic()
kit.servo[0].angle = 157
time.sleep(d90)
kit.servo[0].angle = 22
time.sleep(d90)
ed = time.monotonic()
print(f'{ed-st} for 135L,135R = {(ed-st)/180}')



