#!/usr/bin/env python

# Generic driver for the Neato XV-11 Robot Vacuum
# Copyright (c) 2010 University at Albany. All right reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University at Albany nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL VANADIUM LABS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
neato_driver.py is a generic driver for the Neato XV-11 Robotic Vacuum.
ROS Bindings can be found in the neato_node package.
"""

__author__ = "ferguson@cs.albany.edu (Michael Ferguson)"

import serial

BASE_WIDTH = 248    # millimeters
MAX_SPEED = 300     # millimeters/second

"""
This driver has been changed from the original version in order to support
a wider range of neato models and firmware versions.

The expected responses are not hardcoded in this driver anymore.

This driver reads responses until it receives a control-z. Neato Robotics has
documented that all responses have a control-Z (^Z) at the end of the
response string: http://www.neatorobotics.com.au/programmer-s-manual
"""
CTRL_Z = chr(26)

class xv11():

    def __init__(self, port="/dev/ttyUSB0"):
        self.port = serial.Serial(port,115200)
        # Storage for motor and sensor information
        self.state = {"LeftWheel_PositionInMM": 0, "RightWheel_PositionInMM": 0}
        self.stop_state = True
        # turn things on
        self.port.flushInput()
        self.port.write("\n")
        self.setTestMode("on")
        self.setLDS("on")

    def exit(self):
        self.port.flushInput()
        self.port.write("\n")
        self.setLDS("off")
        self.setTestMode("off")

    def setTestMode(self, value):
        """ Turn test mode on/off. """
        self.port.write("testmode " + value + "\n")
        self.readResponseString()

    def setLDS(self, value):
        self.port.write("setldsrotation " + value + "\n")
        self.readResponseString()

    def requestScan(self):
        """ Ask neato for an array of scan reads. """
        self.port.flushInput()
        self.port.write("getldsscan\n")

    def readResponseString(self):
        """ Returns the entire response from neato in one string. """
        response = str()
        self.port.timeout = 0.001
        while True:
            try:
                buf = self.port.read(1024)
            except:
                return ""
            if len(buf) == 0:
                self.port.timeout *= 2
            else:
                response += buf
                if buf[len(buf)-1] == CTRL_Z:
                    break;
        self.port.timeout = None
        return response

    def getScanRanges(self):
        """ Read values of a scan -- call requestScan first! """
        ranges = list()
        response = self.readResponseString()
        for line in response.splitlines():
            vals = line.split(",")
            # vals[[0] angle, vals[1] range, vals[2] intensity, vals[3] error code
            if len(vals) >= 2 and vals[0].isdigit() and vals[1].isdigit():
                ranges.append(int(vals[1])/1000.0)
        # sanity check
        if len(ranges) != 360:
            return []
        return ranges

    def setMotors(self, l, r, s):
        """ Set motors, distance left & right + speed """
        #This is a work-around for a bug in the Neato API. The bug is that the
        #robot won't stop instantly if a 0-velocity command is sent - the robot
        #could continue moving for up to a second. To work around this bug, the
        #first time a 0-velocity is sent in, a velocity of 1,1,1 is sent. Then, 
        #the zero is sent. This effectively causes the robot to stop instantly.
        if (int(l) == 0 and int(r) == 0 and int(s) == 0):
            if (not self.stop_state):
                self.stop_state = True
                l = 1
                r = 1
                s = 1
        else:
            self.stop_state = False
        self.port.write("setmotor "+str(int(l))+" "+str(int(r))+" "+str(int(s))+"\n")

    def readResponseAndUpdateState(self):
        """ Read neato's response and update self.state dictionary.
            Call this function only after sending a command. """
        response = self.readResponseString()
        for line in response.splitlines():
            vals = line.split(",")
#            print vals
            if len(vals) >= 2  and (vals[1].isdigit() or vals[1].startswith('-')):
#            if len(vals) >= 2:
#                print "vals[1]" + vals[1]
                self.state[vals[0]] = int(vals[1])
#            elif(len(vals) >= 2):
#                print "no" + "vals[1]" + vals[1]
#                print "isalpha " + str(vals[0].isalpha())
#                print "isdigit " + str(vals[1].isdigit())

    def getMotors(self):
        """ Update values for motors in the self.state dictionary.
            Returns current left, right encoder values. """
        self.port.flushInput()
        self.port.write("getmotor\n")
        self.readResponseAndUpdateState()
#        print "self.state[LeftWheel_PositionInMM] : " + str(self.state["LeftWheel_PositionInMM"])
        return [self.state["LeftWheel_PositionInMM"],self.state["RightWheel_PositionInMM"]]

    def getAnalogSensors(self):
        """ Update values for analog sensors in the self.state dictionary. """
        self.port.write("getanalogsensors\n")
        self.readResponseAndUpdateState()

    def getDigitalSensors(self):
        """ Update values for digital sensors in the self.state dictionary. """
        self.port.write("getdigitalsensors\n")
        self.readResponseAndUpdateState()

    def getCharger(self):
        """ Update values for charger/battery related info in self.state dictionary. """
        self.port.write("getcharger\n")
        self.readResponseAndUpdateState()

    def setBacklight(self, value):
        if value > 0:
            self.port.write("setled backlighton")
        else:
            self.port.write("setled backlightoff")
        self.readResponseString()

    #SetLED - Sets the specified LED to on,off,blink, or dim. (TestMode Only)
    #BacklightOn - LCD Backlight On  (mutually exclusive of BacklightOff)
    #BacklightOff - LCD Backlight Off (mutually exclusive of BacklightOn)
    #ButtonAmber - Start Button Amber (mutually exclusive of other Button options)
    #ButtonGreen - Start Button Green (mutually exclusive of other Button options)
    #LEDRed - Start Red LED (mutually exclusive of other Button options)
    #LEDGreen - Start Green LED (mutually exclusive of other Button options)
    #ButtonAmberDim - Start Button Amber Dim (mutually exclusive of other Button options)
    #ButtonGreenDim - Start Button Green Dim (mutually exclusive of other Button options)
    #ButtonOff - Start Button Off

