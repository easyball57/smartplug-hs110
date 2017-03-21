#!/bin/env python

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

import re
import sys
import time
import math
from datetime import datetime, timedelta
import time
import calendar
import logging

from .util import *

import socket
import json


DEFAULT_TIMEOUT = 1

		
class Smartplug(object):
	"""provides interface to the SmarPlug devices
	"""

	def __init__(self, mac, attr=None):
		"""
		will raise ValueError if ip doesn't exist
		"""
		self.attr = attr
		
		
		if self.validIP(self.attr["ip"]): 
			self.ip = self.attr["ip"]
		else:
			raise ValueError("Valid IP is expected : "+str(ip))

		self.port = 9999
		
		mac = str(mac).upper()
		if self.validateMac(mac) == False:
			raise ValueError("MAC address is in unexpected format: "+str(mac))
		self.mac = sc(mac)
		
		self.online = True
		self.relay_state = '?'
		self.last_seen = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
		
		self.power = 0
		self.current = 0
		self.total = 0
		self.voltage = 0
				
		self.interval=60
		
		# Predefined Smart Plug Commands
		# For a full list of commands, consult tplink_commands.txt
		self.commands = {'info'	 : '{"system":{"get_sysinfo":{}}}',
				'on'	   : '{"system":{"set_relay_state":{"state":1}}}',
				'off'	  : '{"system":{"set_relay_state":{"state":0}}}',
				'cloudinfo': '{"cnCloud":{"get_info":{}}}',
				'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
				'time'	 : '{"time":{"get_time":{}}}',
				'schedule' : '{"schedule":{"get_rules":{}}}',
				'countdown': '{"count_down":{"get_rules":{}}}',
				'antitheft': '{"anti_theft":{"get_rules":{}}}',
				'reboot'   : '{"system":{"reboot":{"delay":1}}}',
				'reset'	: '{"system":{"reset":{"delay":1}}}',
				'realtime'	: '{"emeter":{"get_realtime":{}}}'
		}

	def get_status(self):
		retd = {}
		retd["mac"] = self.mac
		retd["name"] = self.attr["name"]
		retd["location"] = self.attr["location"]
		retd["lastseen"] = self.last_seen
		retd["relay"] = self.relay_state
		retd["power"] = round(self.power, 3)
		retd["current"] = round(self.current, 3)
		retd["total"] = round(self.total, 3)
		retd["voltage"] = round(self.voltage, 3)
		retd["interval"] = self.interval
		return retd		  
		   
	def dump_status(self):
		retd = {}
		for key in dir(self):
			ptr = getattr(self, key)
			if not hasattr(ptr, '__call__') and not key[0] == '_':
				retd[key] = ptr
		return retd		  
			

	def switch(self, on):
		"""switch power on or off
		"""
		info("API  %s %s smartplug switch: %s" % (self.mac, self.attr["name"], 'on' if on else 'off',))

		if on == True:
			self.switch_state = 'on'
		else:
			self.switch_state = 'off'
		self.send_cmd_smartplug(self.switch_state)
		return 

	def switch_on(self):
		self.switch(True)

	def switch_off(self):
		self.switch(False)

	def response_to_dict(r):
		retd = {}
		for key in dir(r):
			ptr = getattr(r, key)
			if isinstance(ptr, BaseType):
				retd[key] = ptr.value
		return retd
		
		# Check if IP is valid
	def validIP(self, ip):
		try:
			socket.inet_pton(socket.AF_INET, ip)
		except socket.error:
			return False
		return True 
	
	# Encryption and Decryption of TP-Link Smart Home Protocol
	# XOR Autokey Cipher with starting key = 171
	def encrypt(self, string):
		key = 171
		result = "\0\0\0\0"
		for i in string: 
			a = key ^ ord(i)
			key = a
			result += chr(a)
		return result
	
	def decrypt(self,string):
		key = 171 
		result = ""
		for i in string: 
			a = key ^ ord(i)
			key = ord(i) 
			result += chr(a)
		return result

	def send_cmd_smartplug(self, cmd):
		
		# Send command and receive reply 
		try:
			sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock_tcp.connect((self.ip, self.port))
			sock_tcp.send(self.encrypt(cmd))
			data = sock_tcp.recv(2048)
			sock_tcp.close()
		  
			result_json = self.decrypt(data[4:])
			return result_json
		except socket.error:
			error("Error Smartplug '%s' during sending request $s" % (self.attr['name'], request))
			return ""

	def validateMac(self, mac):
		if not re.match("^[A-F0-9]+$", mac):
			return False
		try:
			_ = int(mac, 16)
		except ValueError:
				return False
		return True
		

	def get_realtime(self):
		result_json = self.send_cmd_smartplug(self.commands["realtime"])
		decoded = json.loads(result_json)
		self.current = decoded["emeter"]["get_realtime"]["current"]
		self.voltage = decoded["emeter"]["get_realtime"]["voltage"]
		self.power = decoded["emeter"]["get_realtime"]["power"]
		self.total = decoded["emeter"]["get_realtime"]["total"]
		self.err_code = decoded["emeter"]["get_realtime"]["err_code"]
		return (self.current, self.voltage, self.power, self.total, self.err_code)

	def get_daily_stat(self, month, year):
		cmd = '{"emeter":{"get_daystat":{"month":' + str(month) + ',"year":' + str(year) + '}}}'
		result_json = self.send_cmd_smartplug(cmd)
		decoded = json.loads(result_json)
		print (result_json)
		
	def get_monthly_stat(self, year):
		cmd = '{"emeter":{"get_monthstat":{"year":' + str(year) + '}}}'
		result_json = self.send_cmd_smartplug(cmd)
		decoded = json.loads(result_json)
		print (result_json)

	def get_relay_status(self):
		result_json = self.send_cmd_smartplug(self.commands["info"])
		decoded = json.loads(result_json)
		self.relay_state = decoded["system"]["get_sysinfo"]["relay_state"]
		return self.relay_state
		
		
	
