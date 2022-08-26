#!/usr/bin/env python3
"""\
@file head_nod.py
@brief simple LEAP script to move the avatar's head up and down, and back and forth

$LicenseInfo:firstyear=2022&license=viewerlgpl$
Second Life Viewer Source Code
Copyright (C) 2022, Linden Research, Inc.
 
This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation;
version 2.1 of the License only.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Linden Research, Inc., 945 Battery Street, San Francisco, CA  94111  USA
$/LicenseInfo$
"""

'''
head_nod.py -- use Puppetry to update head's local orientation

Run this script via viewer menu...
    Advanced --> Puppetry --> Launch LEAP plug-in...
This script uses the LEAP framework for sending messages to the viewer.
The joint data is a dictionary with the following format:
    data={"joint_name":{"type":[1.23,4.56,7.89]}, ...}
Where:
    joint_name = string recognized by LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"
    type = "local_rot" | "rot" | "pos" | "scale"
    type's value = array of three floats (e.g. [x,y,z])
Multiple joints can be combined into the same dictionary.

Note: When you test this script at the command line it will block
because the leap.py framework is waiting for the initial message
from the viewer.  To unblock the system paste the following
string into the script's stdin:

119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}

Also, for more readable text with newlines between messages
uncomment the print("") line in the main loop below.
'''

import eventlet
import math
import os
import sys
import time

try:
    import puppetry
except ImportError as err:
    # modify sys.path so we can find puppetry module in parent directory
    currentdir = os.path.dirname(os.path.realpath(__file__))
    parentdir = os.path.dirname(currentdir)
    sys.path.append(parentdir)

# now we can really import puppetry
try:
    import puppetry
except ImportError as err:
    sys.exit("Can't find puppetry module")

# The avatar's head coordinate frame:
#
#             ______       turn(z)
#            /o   o \       | 
#           |   C    |      @-nod(Y)
#           |  ---   |     /
#            \______/   tilt(X)
#               |       
#     R-+-+-+-+ | +-+-+-+-L
#               +
#               |
#               |
#             +-@-+
#             |   |
#             +   +
#             |   |
#            /   /
#

class Sho:
    '''Simple Harmonic Oscillator'''
    def __init__(self, frequency=1.0, phase=0.0):
        frequency = abs(frequency)
        self.wave_speed = 2.0 * math.pi * frequency
        self.period = 1.0 / frequency
        self.t = phase / self.wave_speed
        if self.t > self.period or self.t < -self.period:
            self.t -= int(self.t / self.period) * self.period
    def advance(self, dt):
        self.t += dt
        if self.t > self.period or self.t < -self.period:
            self.t -= int(self.t / self.period) * self.period
    def sin(self):
        return math.sin(self.t * self.wave_speed)
    def cos(self):
        return math.cos(self.t * self.wave_speed)
    def theta(self):
        return self.t * self.wave_speed

# we will alterately nod and shake the head using sinusoidal motion
pulse_period = 16.0
oscillation_period = 2.0
pulse_speed = 2.0 * math.pi / pulse_period
oscillation_speed = 2.0 * math.pi / oscillation_period

pulsor = Sho(frequency = 1.0 / pulse_period, phase=0)
rotator = Sho(frequency = 1.0 / oscillation_period, phase=0)
amplitude = math.pi / 6.0

update_period = 0.1


def computeData(time_step):
    # advance the oscillators
    pulsor.advance(time_step)
    rotator.advance(time_step)

    # compute
    ps = pulsor.sin()
    tilt = 0.0
    if ps > 0.0:
        # nod
        nod = (amplitude * ps) * rotator.sin()
        turn = 0.0
    else:
        # shake
        nod = 0.0
        turn = (amplitude * ps) * rotator.sin()

    # assemble the message
    packed_rot = puppetry.packedQuaternionFromEulerAngles(tilt, nod, turn)
    data = {
        'mHead':{'local_rot': packed_rot}
    }
    return data

def puppetry_coroutine():
    t0 = time.monotonic()
    delta_time = update_period
    while puppetry.isRunning():
        # sleep to yield to other eventlet coroutines
        eventlet.sleep(max(0.0, 2 * update_period - delta_time))
        t1 = time.monotonic()
        delta_time = t1 - t0
        t0 = t1
        data = computeData(delta_time)
        puppetry.sendPuppetryData(data)
        #print("") # uncomment this when debugging at command-line

# start the real work
puppetry.start()
eventlet.spawn(puppetry_coroutine)

# loop until puppetry stops
while puppetry.isRunning():
    eventlet.sleep(0.2)