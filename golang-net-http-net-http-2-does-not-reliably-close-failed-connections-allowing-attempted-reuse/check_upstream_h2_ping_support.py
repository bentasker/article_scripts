#!/usr/bin/env python3
#
# Establish a HTTP/2 connection to an upstream server
# then send it a HTTP2 Pingg and print response frames
#
# Copyright (c) 2023 B Tasker
# Released under BSD 3-Clause License
#
# Usage:
#
# pip install h2
# ./check_upstream_h2_ping_support.py <server address>
#

'''
Copyright (c) 2023, B Tasker

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of
conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other materials
provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used
to endorse or promote products derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''



import socket
import ssl
import h2.connection
import h2.events
import certifi
import sys


SERVER_NAME = sys.argv[1]
SERVER_PORT = 443

socket.setdefaulttimeout(15)
ctx = ssl.create_default_context(cafile=certifi.where())
ctx.set_alpn_protocols(['h2'])

s = socket.create_connection((SERVER_NAME, SERVER_PORT))
s = ctx.wrap_socket(s, server_hostname=SERVER_NAME)

c = h2.connection.H2Connection()
c.initiate_connection()
c.ping(b'ffffffff')
s.sendall(c.data_to_send())

response_stream_ended = False
while not response_stream_ended:
    data = s.recv(65536 * 1024)
    if not data:
            break
    events = c.receive_data(data)
    for event in events:
        if isinstance(event, h2.events.PingAckReceived):
            print(event)
            response_stream_ended = True
            break

