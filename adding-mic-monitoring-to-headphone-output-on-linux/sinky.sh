
#!/bin/bash
#
# sinky: enable sidetone for a mic using Pulseaudio or Pipewire
# Copyright (c) 2023 B Tasker
# Released under BSD 3 Clause License
#

# Copyright B Tasker 2023
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# 
#     Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# 
#     Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# 
#     Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


SOURCE=${SOURCE:-"alsa_input.usb-3142_Fifine_Microphone-00.mono-fallback"}
SINK=${SINK:-"alsa_output.usb-C-Media_Electronics_Inc._Mpow-224_20200316-00.analog-stereo"}
LOCKDIR=${LOCKDIR:-"/var/lock/"}
LOCKFILE=${LOCKFILE:-"$LOCKDIR/sinky.$USER.lock"}

function stop(){
        pactl unload-module module-loopback
}

function start(){
        pactl load-module module-loopback \
        source="$SOURCE" \
        sink="$SINK" \
        latency_msec=1
}

# Have we been invoked manually?
case "$1" in
	"disable")
		stop
		touch "$LOCKFILE";;
	"lock")
		touch "$LOCKFILE";;
	"unlock")
		rm "$LOCKFILE" 2> /dev/null;;
	"enable"|"start")
		start;;
	"stop")
		stop;;
esac

# If a command was provided, exit rather than entering the loop
if [ ! "$1" == "" ]
then
	exit
fi

# Initialise
MIC_SOURCE=-1

# Subscribe and read
pactl subscribe | while read a event b type sourcenum
do
		# Is it it a new source-output coming online
		# and have we already triggered for a mic?
        if [ "$event" == "'new'" -a "$type" == 'source-output' -a "$MIC_SOURCE" == "-1" ]
        then
	        if [ ! -f "$LOCKFILE" ]
	        then
                start
                echo "Mic $sourcenum on"
                MIC_SOURCE=$sourcenum
            else
	            echo "Skipping start for $sourcenum - lockfile exists"
            fi
            
        # Otherwise, is it our mic going offline
        elif [ "$event" == "'remove'" -a "$type" == 'source-output' -a "$MIC_SOURCE" == "$sourcenum" ]
        then
	        if [ ! -f "$LOCKFILE" ]
	        then        
                stop
                echo "Mic $sourcenum off"
                MIC_SOURCE=-1
            else
	            echo "Skipping stop for $sourcenum - lockfile exists"
            fi
        fi
done

