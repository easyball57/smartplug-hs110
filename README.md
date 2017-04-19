
# smartplug-hs110
Integrate TP-link Smartplug HS110 into Jeedom, with the help of MQTT messages

# TP-Link WiFi SmartPlug Client and Wireshark Dissector

For the full story, see [Reverse Engineering the TP-Link HS110](https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/)

Work based on [softScheck/tplink-smartplug](https://github.com/softScheck/tplink-smartplug)


Installation

Prerequisits :

Python and PIP have to be installed

Installation of Mosquitto for Python

#sudo pip install paho-mqtt

Copy the zip and unzip it into a directory for example "hs110"

Update the configuration files located in the subdirectory "config"

You need to update the 2 files :

tp-hostconfig.json -> to add the ip address of the mqtt broker
tp-conf.json -> to add the TLINK Smartplug properties (mac address, ip, name, location)

Then go to the root directory and start the python script into the background

.../hs110 $ python tplink-hs110.py &


Auto start 

Copy the startup script tplink-hs110.bash to /etc

Make the file executable

#chmod +x /etc/plugwise.bash

Add it to the crontab

#crontab –e

@reboot /etc/tplink-hs110.bash
