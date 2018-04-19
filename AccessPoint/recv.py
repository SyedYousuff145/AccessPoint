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
import fcntl, os, errno
import paho.mqtt.client as mqtt

SOCKPATH = "/var/run/lirc/lircd"

sock = None
client = mqtt.Client()
client.connect('test.mosquitto.org', port=1883)
client.loop_start()

def init_irw():
	global sock
	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	print ('starting up on %s' % SOCKPATH)
	sock.connect(SOCKPATH)
	# sock.setblocking(0)	
	fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)

def next_key():
	'''Get the next key pressed. Return keyname, updown.
	'''
	
	try:
		data = sock.recv(128)
		# print("Data: " + data)
		data = data.strip()
		words = data.split()
		return words[2], words[1]
	except socket.error, e:
		if e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK:
			time.sleep(0.001)
		return None, None
	except IndexError:
		print data
		return None, None

if __name__ == '__main__':
	LED = 13
	BULB = 21
	BUZZER = 5
	LED_ON_TIME = 300
	LED_STATE = True
	BULB_STATE = True
	BUZZER_STATE = False

	init_irw()
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(LED,GPIO.OUT)
	GPIO.setup(BULB,GPIO.OUT)
	GPIO.setup(BUZZER,GPIO.OUT)
	GPIO.output(LED, LED_STATE)
	GPIO.output(BULB, BULB_STATE)
	GPIO.output(BUZZER, BUZZER_STATE)
		
	while True:
		keyname, updown = next_key()
		if keyname:
			print keyname
			client.publish('buss',keyname)
		if keyname == 'KEY_VOLUMEUP':
			GPIO.output(BULB, True)
		if keyname == 'KEY_VOLUMEDOWN':
			GPIO.output(BULB, False)
		if keyname == 'KEY_POWER':
			if not LED_STATE:
				GPIO.output(LED, True)
				GPIO.output(BUZZER, True)
				LED_STATE = True
				BUZZER_STATE = True
			start = time.time()*1000
		if (LED_STATE and time.time()*1000 - start > LED_ON_TIME):
			GPIO.output(LED, False)
			GPIO.output(BUZZER, False)
			LED_STATE = False
			BUZZER_STATE = False

