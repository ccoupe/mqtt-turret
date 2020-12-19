# Import libraries
import RPi.GPIO as GPIO
import time

# Set GPIO numbering mode
GPIO.setmode(GPIO.BOARD)

laserPin = 11
lp2 = 13
GPIO.setup(laserPin,GPIO.OUT)
GPIO.output(laserPin, GPIO.HIGH)
GPIO.setup(lp2,GPIO.OUT)
GPIO.output(lp2, GPIO.HIGH)
time.sleep(2)
GPIO.output(laserPin, GPIO.LOW)
GPIO.output(lp2, GPIO.LOW)
#Clean things up at the end
GPIO.cleanup()
print ("Goodbye")


