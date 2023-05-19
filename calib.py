import RPi.GPIO as GPIO
from adafruit_servokit import ServoKit
import time

# calibrate servo range

kit = ServoKit(channels=16)
kit.servo[0].set_pulse_width_range(1000, 2000)
kit.servo[0].actuation_range = 180
kit.servo[0].angle = 45			# pan

kit.servo[0].set_pulse_width_range(800, 2200)
kit.servo[1].actuation_range = 200
kit.servo[1].angle = 200		# tilt
