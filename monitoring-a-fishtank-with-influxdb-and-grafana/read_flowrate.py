#!/usr/bin/env python3
#
#
# Read pulses from a flow rate sensor and convert to l/hr
#
# Copyright (c) 2023 B Tasker
#
# Released under BSD 3 clause:

'''
Redistribution and use in source and binary forms, with or without modification, are permitted provided that the 
following conditions are met:
    (1) Redistributions of source code must retain the above copyright notice, this list of conditions and the 
    following disclaimer. (2) Redistributions in binary form must reproduce the above copyright notice, this 
    list of conditions and the following disclaimer in the documentation and/or other materials provided with 
    the distribution.
    
    (3)The name of the author may not be used to endorse or promote products derived from this software without 
    specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO 
EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT 
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN 
IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

'''

import math
import RPi.GPIO as GPIO
import requests
import sys
import statistics
import time


# Based on 
# https://tutorials-raspberrypi.com/reading-out-the-flow-meter-water-flow-sensor-on-the-raspberry-pi/

# Which GPIO is the flow meter connected to?
GPIO_NUM = 5

# How often should we calculate stats and write them?
WRITE_REGULARITY = 4

# How long to sleep between iterations
SLEEP_INT = 5

INFLUXDB_URL = "http://127.0.0.1:8086"
INFLUXDB_AUTH = ""
INFLUXDB_DB = "telegraf"

MEASUREMENT = "aquarium"
LOCATION = "diningroom"

def countPulse(channel):
    ''' Increment the counter, assuming the counter is active
    '''
    global counter
    if start_counter == 1:
        counter += 1


def calcStats(flowrates):
    ''' Calculate some stats
    '''
    stats = {
        "min" : min(flowrates),
        "max" : max(flowrates),
        "mean" : sum(flowrates) / len(flowrates)
    }
    return stats


def writeStat(stats, session):
    ''' Take a stats dict, convert to LP
    and write into InfluxDB
    '''
    
    ts = math.floor(time.time())
    lp = f"{MEASUREMENT},location={LOCATION} "
    fields = []
    for stat in stats:
        fields.append(f"flow_{stat}={stats[stat]}")
        
    lp += ",".join(fields)
    lp += f" {ts}"
    #print(lp)
    
    headers = {}
    if len(INFLUXDB_AUTH) > 0:
        headers = {
                "Authorization" : INFLUXDB_AUTH
            }
    
    session.post(
        url = f"{INFLUXDB_URL}/write?db={INFLUXDB_DB}&precision=s",
        headers = headers,
        data = lp
        )
    

# Set up the GPIO
global counter
counter = 0

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_NUM, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.add_event_detect(GPIO_NUM, GPIO.FALLING, callback=countPulse)

# Create a session so we can use keep-alive
session = requests.session()

# We use this list to track rates between writes
flowrates = []

while True:
    try:
        # Capture some pulses
        start_counter = 1
        time.sleep(1)
        start_counter = 0
        
        # Calculate the flow rate
        flow = (counter / 7.5) # Pulse frequency (Hz) = 7.5Q, Q is flow rate in L/min.
        
        # Add to the list of rates
        flowrates.append(flow)
        
        # Write out
        if len(flowrates) >= WRITE_REGULARITY:
            stats = calcStats(flowrates)
            #print(stats)
            writeStat(stats, session)
            flowrates = []
            
        counter = 0
        time.sleep(SLEEP_INT)
    except KeyboardInterrupt:
        print('\nkeyboard interrupt!')
        GPIO.cleanup()
        sys.exit()
