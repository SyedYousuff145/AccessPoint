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

SOCKPATH = "/var/run/lirc/lircd"

sock = None

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
	LED = 16
	LED_ON_TIME = 100
	LED_STATE = False

	init_irw()
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(LED,GPIO.OUT)
	GPIO.output(LED, LED_STATE)
		
	while True:
		keyname, updown = next_key()
		if keyname == 'KEY_POWER':
			if not LED_STATE:
				GPIO.output(LED, True)
				LED_STATE = True
			start = time.time()*1000
		if (LED_STATE and time.time()*1000 - start > LED_ON_TIME):
			GPIO.output(LED, False)
			LED_STATE = False

