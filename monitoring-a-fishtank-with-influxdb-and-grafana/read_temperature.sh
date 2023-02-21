#!/bin/bash
#
# Read temperature from a 1-wire temperature sensor
#
# example: ./read_temperature.sh 
#

DEVNAME=${1:-"28-00000e668773"}
LOCATION=${LOCATION:-"diningroom"}

ts=`date +'%s'`
tempread=`cat /sys/bus/w1/devices/$DEVNAME/w1_slave`
temp=`echo "scale=2; "\`echo ${tempread##*=}\`" / 1000" | bc`

lp="aquarium,location=$LOCATION water_temperature=$temp $ts"

# Write the stats out
curl -s -d "$lp" "http://127.0.0.1:8086/write?db=telegraf&precision=s"
