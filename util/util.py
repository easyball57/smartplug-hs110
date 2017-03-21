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

import sys
import serial
from serial.serialutil import SerialException
import datetime
import logging
import logging.handlers

LOG_COMMUNICATION = False

#global var
tp_logger = None
tp_comm_logger = None

def _string_convert_py3(s):
    if type(s) == type(b''):
        return s

    return bytes(s, 'latin-1')

def _string_convert_py2(s):
    # NOOP
    return s

if sys.version_info < (3, 0):
    sc = _string_convert_py2
else:
    sc = _string_convert_py3

def hexstr(s):
    return ' '.join(hex(ord(x)) for x in s)
    
def uint_to_int(val, octals):
    """compute the 2's compliment of int value val for negative values"""
    bits=octals<<2
    if( (val&(1<<(bits-1))) != 0 ):
        val = val - (1<<bits)
    return val
    
def int_to_uint(val, octals):
    """compute the 2's compliment of int value val for negative values"""
    bits=octals<<2
    if val<0:
        val = val + (1<<bits)
    return val

def init_logger(logfname, appname='tplink-hs1xx'):
    global tp_logger
    tp_logger = logging.getLogger(appname)
    log_level()
    # Add the log message handler to the logger
    handler = logging.handlers.RotatingFileHandler(logfname, maxBytes=1000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    tp_logger.addHandler(handler)
    tp_logger.info("logging started")
   
def log_level(level=logging.DEBUG):
    tp_logger.setLevel(level)

def log_comm(enable):
    global LOG_COMMUNICATION
    LOG_COMMUNICATION = enable

def debug(msg):
    #if __debug__ and DEBUG_PROTOCOL:
        #print("%s: %s" % (datetime.datetime.now().isoformat(), msg,))
        #print(msg)
    tp_logger.debug(msg)

def error(msg, level=1):
    #if level <= LOG_LEVEL:
        #print("%s: %s" % (datetime.datetime.now().isoformat(), msg,))
    tp_logger.error(msg)
        
def info(msg):
    #print("%s: %s" % (datetime.datetime.now().isoformat(), msg,))
    tp_logger.info(msg)

def open_logcomm(filename):
    global tp_comm_logger
    tp_comm_logger = logging.getLogger("tpcomm")
    # Add the log message handler to the logger
    handler = logging.handlers.RotatingFileHandler(filename, maxBytes=1000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    tp_comm_logger.addHandler(handler)
    tp_comm_logger.setLevel(logging.INFO) 
    tp_comm_logger.info("logging started")
    #global logcommfile
    #logcommfile = open(filename, 'w')
    
def close_logcomm():
    #logcommfile.close()
    return
    
def logcomm(msg):
    if LOG_COMMUNICATION:
        #logcommfile.write("%s %s \n" % (datetime.datetime.now().isoformat(), msg,))
        tp_comm_logger.info(msg)

