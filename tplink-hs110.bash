#!/bin/bash

cur=$PWD
cd /home/pi/hs110
nohup python tplink-hs110.py &
ps -ef | grep tplink-hs110 > tplink-hs110.pid
cd $cur

