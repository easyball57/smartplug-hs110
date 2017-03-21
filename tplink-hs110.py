#!/usr/bin/env python

# Copyright (C) 2017 Eric Mely
#
# This file is part of tplink-hs1xx
#
# tplink-hs1xx is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tplink-hs1xx is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tplink-hs1xx .  If not, see <http://www.gnu.org/licenses/>. 
#
# The program is a major modification and extension to:
#   
# TODO:
#   


from util.util import *
from util.tpmqtt import *
from util.tp_api import *

from datetime import datetime, timedelta
import time
import calendar
import subprocess
import glob
import os
import logging
import Queue
import threading
import itertools

mqtt = True
try:
	import paho.mqtt.client as mosquitto
except:
	mqtt = False

import pprint as pp
import json


#DEBUG_PROTOCOL = False
log_comm(True)
#LOG_LEVEL = 2

cfg = json.load(open("config/tp-hostconfig.json"))
perpath = cfg['permanent_path']+'/'
logpath = cfg['log_path']+'/'
#make sure log directory exists
if not os.path.exists(logpath):
	os.makedirs(logpath)

epochf = False
if cfg.has_key('log_format') and cfg['log_format'] == 'epoch':
	epochf = True
	
actdir = 'tpact/'
actpre = 'tpact-'
actpost = '.log'
logdir = 'tplog/'
logpre = 'tp-'
logpost = '.log'

#prepare for cleanup of /tmp after n days.
cleanage = 604800; # seven days in seconds

locnow = datetime.utcnow()-timedelta(seconds=time.timezone)
now = locnow
yrfolder = str(now.year)+'/'
if not os.path.exists(perpath+yrfolder+actdir):
	os.makedirs(perpath+yrfolder+actdir)
if not os.path.exists(perpath+yrfolder+logdir):
	os.makedirs(perpath+yrfolder+logdir)

class TPControl(object):
	def __init__(self):
		"""
		...
		"""
		global port
	
		self.staticconfig_fn = 'config/tp-conf.json'
	
	
		self.smartplugs = []
		
		self.bymac = dict()
		self.byname = dict()
		
		self.actfiles = dict()
		self.logfnames = dict()
		self.daylogfnames = dict()
	
		#read the static configuration
		sconf = json.load(open(self.staticconfig_fn))
		i=0
		for item in sconf['static']:
			#remove tabs which survive dialect='trimmed'
			for key in item:
				if isinstance(item[key],str): item[key] = item[key].strip()
			self.bymac[item.get('mac')]=i
			self.byname[item.get('name')]=i
			#exception handling timeouts done by circle object for init
			self.smartplugs.append(Smartplug(item['mac'], item))
			i += 1
			info("adding smartplug: %s" % (self.smartplugs[-1].attr['name'],))
		self.setup_actfiles()

	def setup_actfiles(self):
		global perpath
		global actpre
		global actpost
		
		#close all open act files
		for m, f in self.actfiles.iteritems():
			f.close()
		#open actfiles according to (new) config
		self.actfiles = dict()
		#now = datetime.now()			
		locnow = datetime.utcnow()-timedelta(seconds=time.timezone)
		now = locnow
		today = now.date().isoformat()
		yrfold = str(now.year)+'/'
		if not os.path.exists(perpath+yrfold+actdir):
			os.makedirs(perpath+yrfold+actdir)
		for c in self.smartplugs:
			mac = c.mac
			fname = perpath + yrfold + actdir + actpre + today + '-' + mac + actpost
			f = open(fname, 'a')
			self.actfiles[mac]=f


	def cleanup_tmp(self):
		perfiles = perpath + '*/' + actdir + actpre + '*' + actpost
		for fn in glob.iglob(perfiles):
			 if time.time()-os.path.getmtime(fn) > cleanage:
				os.unlink(fn)

	def apply_switch_to_smartplug(self, control, mac, status):
		"""apply switch settings to smartplug
		"""
		try:
			c = self.smartplugs[self.bymac[mac]]
		except:
			info("mac from controls not found in smartplugs")
			return False
		switched = False
		#switch on/off if required
		if status != c.relay_state:
			info('Smartplug mac: %s needs to be switched %s' % (mac, sw_state))
			try:
				c.switch(status)
			except (ValueError, TimeoutException, SerialException) as reason:
				error("Error in apply_control_to_smartplug failed to switch: %s" % (reason,))
				return False
			switched = True
		return switched


	def process_mqtt_commands(self):
		updated = False
		while not qsub.empty():
			rcv = qsub.get()
			topic = rcv[0]
			payl = rcv[1]
			info("process_mqtt_commands: %s %s" % (topic, payl)) 
			print (topic, payl)
			#Modification Jeedom
			#Topic format: tplink/cmd/<mac>/<cmdname>
			st = topic.split('/')
			try:
				#Modification Jeedom
				cmd = st[-1]
				mac = st[-2]
				print (mac, cmd)
				#msg format: json: {"mac":"...", "cmd":"", "val":""}
				msg = json.loads(payl)
				print (msg)
				val = msg['val']
				print (val)
				try:
					source = msg['uid']
				except: #KeyError:
					source = "anonymous_mqtt"
			except:
				#Modification Jeedom : Jeedom 1.6 payl are no more json, but Jeedom 2.0 ok  
				error ("MQTT: Invalid message format in topic or JSON payload")
				continue
			if cmd == "switch":
				val = val.lower()
				c = self.smartplugs[self.bymac[mac]]
				if val == "on":
					c.switch_on()
				elif val == "off":
					c.switch_off()
			elif cmd == "reqstate":
				try:
					c = self.smartplugs[self.bymac[mac]]
					c.get_realtime()
					info("Just read power for status update")
				except:
					info("Error in reading power for status update")
				#return message is generic state message below
				
			self.publish_smartplug_state(mac)
	
	#Ftopic for Jeedom	
	def ftopicJeedom(self, keyword, mac):
		return str("tplink/" + mac + "/" + keyword)
		

	def publish_smartplug_state(self, mac):
		#Modification pour Jeedom
		qpub.put((self.ftopicJeedom("status", mac), str(self.get_status_json(mac)), True))

	def get_status_json(self, mac):
		try:
			c = self.smartplugs[self.bymac[mac]]
		except:
			info("get_status_json: mac not found in smartplugs")
			return ""
		try:
			status = c.get_status()
			msg = json.dumps(status)
		except (ValueError) as reason:
			error("Error in get_status_json: %s" % (reason,))
			msg = ""
		return str(msg)

	def ten_seconds(self):
		"""
		"""
		for mac, f in self.actfiles.iteritems():
			try:
				c = self.smartplugs[self.bymac[mac]]
			except:
				error("Error in ten_seconds(): mac from controls not found in smartplugs")
				continue  
			#prepare for logging values
			if epochf:
				ts = calendar.timegm(datetime.utcnow().utctimetuple())
			else:
				t = datetime.time(datetime.utcnow()-timedelta(seconds=time.timezone))
				ts = 3600*t.hour+60*t.minute+t.second
			try:
				current, voltage, power, total, err_code = c.get_realtime()
				relay_status = c.get_relay_status()
				#print("%5d, %3.6f, %4.6f, %4.6f, %4.6f, %d\n" % (ts, current, voltage, power, total, err_code))
				f.write("%5d, %3.6f, %4.6f, %4.6f, %4.6f, %d\n" % (ts, current, voltage, power, total, err_code))
				#debug("MQTT put value in qpub")
				msg = str('{"ts":%d,"mac":"%s","power":%.2f,"switch":%d}' % (ts, mac, power, relay_status))
				#msg compatible with Jeedom 1.6, Jeedom 2.0 interpret now JSON
				qpub.put((self.ftopicJeedom("realtime", mac), msg, True))
			except ValueError:
				#print("%5d, " % (ts,))
				f.write("%5d, \n" % (ts,))
			f.flush()
			#prevent backlog in command queue
			if mqtt: self.process_mqtt_commands()
		return

	def run(self):
		global mqtt
		
		locnow = datetime.utcnow()-timedelta(seconds=time.timezone)
		now = locnow
		day = now.day
		hour = now.hour
		minute = now.minute

		while 1:
			#align to next 10 second boundary, while checking for input commands.
			ref = datetime.now()
			proceed_at = ref + timedelta(seconds=(10 - ref.second%10), microseconds= -ref.microsecond)
			while datetime.now() < proceed_at:
				#print ("now %s, proceed %s" % (datetime.now(), proceed_at))
				if mqtt: self.process_mqtt_commands()
				time.sleep(0.5)
			#prepare for logging values
			prev_day = day
			prev_hour = hour
			prev_minute = minute
			
			#now = datetime.now()			
			locnow = datetime.utcnow()-timedelta(seconds=time.timezone)
			now = locnow
			day = now.day
			hour = now.hour
			minute = now.minute
	
			if day != prev_day:
				self.setup_actfiles()
				self.cleanup_tmp()
			self.ten_seconds()
				
init_logger(logpath+"tp-logger.log", "tp-logger")
log_level(logging.DEBUG)

try:
	qpub = Queue.Queue()
	qsub = Queue.Queue()
	mqtt_t = None
	if  not mqtt:
		error("No MQTT python binding installed (mosquitto-python)")
	elif cfg.has_key('mqtt_ip') and cfg.has_key('mqtt_port'):
		#connect to server and start worker thread.
		if cfg.has_key('mqtt_user') and cfg.has_key('mqtt_password'):
			mqttclient = Mqtt_client(cfg['mqtt_ip'], cfg['mqtt_port'], qpub, qsub,"tplink-hs1xx",cfg['mqtt_user'],cfg['mqtt_password'])
		else:
			mqttclient = Mqtt_client(cfg['mqtt_ip'], cfg['mqtt_port'], qpub, qsub, "tplink-hs1xx")
		#Modification tp-link	
		mqttclient.subscribe("tplink/cmd/#")
		mqtt_t = threading.Thread(target=mqttclient.run)
		mqtt_t.setDaemon(True)
		mqtt_t.start()
		info("MQTT thread started")
	else:
		error("No MQTT broker and port configured")
		mqtt = False

	main=TPControl()
	main.run()
except:
	raise
	