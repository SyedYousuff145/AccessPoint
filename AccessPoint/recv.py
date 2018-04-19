#!/usr/bin/env python

# Read lirc output, in order to sense key presses on an IR remote.
# There are various Python packages that claim to do this but
# they tend to require elaborate setup and I couldn't get any to work.
# This approach requires a lircd.conf but does not require a lircrc.
# If irw works, then in theory, this should too.
# Based on irw.c, https://github.com/aldebaran/lirc/blob/master/tools/irw.c

import socket
import RPi.GPIO as GPIO
import time
import math
import fcntl, os, errno
import paho.mqtt.client as mqtt

SOCKPATH = "/var/run/lirc/lircd"

sock = None
#client = mqtt.Client()
#client.connect('127.0.0.1', port=1883)
#client.loop_start()

LED = 13
MAINS = 21
BUZZER = 5

def init_irw():
	global sock
	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	print ('starting up on %s' % SOCKPATH)
	sock.connect(SOCKPATH)	
	fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)
	print "Initialization complete"

def next_key():
	'''Get the next key pressed. Return keyname, updown.
	'''
	try:
		data = sock.recv(128)
		data = data.strip()
		words = data.split()
		return words[2], words[1]
	except socket.error, e:
		if e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK:
			time.sleep(0.001)
		return None, None
	except IndexError:
		return None, None

import threading
class DeviceManager(object):
	def __init__(self, gpio):
		self.end_time = time.time()*1000
		self.device_thread = None
		self.gpio = gpio
		# GPIO.output(gpio,False)

	def turn_on(self, duration):
		self.end_time = time.time()*1000 + duration
		if not self.device_thread or not self.device_thread.is_alive():
			self.device_thread = threading.Thread(target=self.__turn_on)
			self.device_thread.start()					
	
	def __turn_on(self):
		GPIO.output(self.gpio,True)
		while time.time()*1000 < self.end_time:
			time.sleep(0.01)
		GPIO.output(self.gpio,False)	

class BuzzerManager(DeviceManager):
	def __init__(self):
		self.name = "buzzer"
		GPIO.setmode(GPIO.BCM)
                GPIO.setup(BUZZER,GPIO.OUT)
		super(BuzzerManager, self).__init__(BUZZER)	

class LedManager(DeviceManager):
	def __init__(self):
		self.name = "led"
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(LED,GPIO.OUT)
		self.pwm = GPIO.PWM(LED, 200)
		self.pwm.start(0)
		self.keep_breathing = True
		self.breathing_thread = threading.Thread(target=self.__breathe)
		self.breathing_thread.start()
		super(LedManager, self).__init__(LED)	

	def turn_on(self,duration):
		super(LedManager, self).turn_on(duration)
		self.keep_breathing = False
		self.pwm.ChangeDutyCycle(100)
	
	def __breathe(self):
		x = 0
		step = 0.03
		while True:
			if self.keep_breathing: 
				duty = self.__mapFun(self.__sin(x),-1,1,0,100)	
				x += step	
				self.pwm.ChangeDutyCycle(duty)
				time.sleep(0.01)
				if x >= 2*math.pi:
					x = 0
			elif not self.device_thread.is_alive():
				x = 3*math.pi/4 
				#time.sleep(1)
				self.keep_breathing = True

	# Function to simplify calling the sine function
	def __sin(self, x):
    		return math.sin(x)

	# Linearly map an input scale to an output scale. This can be used
	# to map the sin function (-1 to 1) into a duty cycle (0 to 100)%
	def __mapFun(self, x, inLo, inHi, outLo, outHi):
    		inRange = inHi - inLo
    		outRange = outHi - outLo
    		inScale = (x - inLo) / inRange  # normalised input (0 to 1)
    		return outLo + (inScale * outRange) # map normalised input to output

if __name__ == '__main__':
	LED_ON_TIME = 100
   	BUZZER_ON_TIME = 100
	MAINS_STATE = None
	if socket.gethostname() == "chrysalis-lumos":
		MAINS_STATE = False
	elif socket.gethostname() == "chrysalis-gate":
		MAINS_STATE = True
	KEY_TEST_INTERVAL_THRESH = 300 
	KEY_POWER_INTERVAL_THRESH = 300
	init_irw()
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(MAINS,GPIO.OUT)
	GPIO.output(MAINS, MAINS_STATE)

	last_key_power = 0
	last_key_test = 0 

	led_manager = LedManager()
	buzzer_manager = BuzzerManager()

	while True:
		keyname, updown = next_key()
		if keyname == 'KEY_TEST':
			led_manager.turn_on(LED_ON_TIME)
			if time.time()*1000 - last_key_test > KEY_TEST_INTERVAL_THRESH:
				buzzer_manager.turn_on(BUZZER_ON_TIME)
		  	last_key_test = time.time()*1000

		if keyname == 'KEY_POWER':
			if time.time()*1000 - last_key_power > KEY_POWER_INTERVAL_THRESH:
				led_manager.turn_on(LED_ON_TIME)
				buzzer_manager.turn_on(BUZZER_ON_TIME + 100)		
				if MAINS_STATE:
					GPIO.output(MAINS, False)
					MAINS_STATE = False
				else:
					GPIO.output(MAINS, True)
					MAINS_STATE = True
			last_key_power = time.time()*1000 

