#!/bin/bash

# Enable i2c
modprobe i2c-dev

# Enable camera driver.
modprobe bcm2835-v4l2

# Setup host DBUS socket location, which is needed for NetworkManager.
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket

# Power off HDMI.
tvservice -o

# Start the pigpio daemon.
systemctl start pigpiod

# Start the main application.
python pira/main.py
