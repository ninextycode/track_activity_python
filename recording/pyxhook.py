"""
# pyxhook -- an extension to emulate some of the PyHook library on linux.
#
#    Copyright (C) 2008 Tim Alexander <dragonfyre13@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#    Thanks to Alex Badea <vamposdecampos@gmail.com> for writing the Record
#    demo for the xlib libraries. It helped me immensely working with these
#    in this library.
#
#    Thanks to the python-xlib team. This wouldn't have been possible without
#    your code.
#
#    This requires:
#    at least python-xlib 1.4
#    xwindows must have the "record" extension present, and active.
#
#    This file has now been somewhat extensively modified by
#    Daniel Folkinshteyn <nanotube@users.sf.net>
#    So if there are any bugs, they are probably my fault. :)

# This license applies to all files in this repository that do not have
# another license otherwise indicated.
#
# Copyright (c) 2014, Jeff Hoogland
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import print_function

import sys
import re
import time
import threading

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq


#######################################################################
# #######################START CLASS DEF###############################
#######################################################################

class HookManager(threading.Thread):
    """ This is the main class. Instantiate it, and you can hand it KeyDown
        and KeyUp (functions in your own code) which execute to parse the
        SimplePyxhookkeyevent class that is returned.

        This simply takes these two values for now:
        KeyDown : The function to execute when a key is pressed, if it
                  returns anything. It hands the function an argument that
                  is the SimplePyxhookkeyevent class.
        KeyUp   : The function to execute when a key is released, if it
                  returns anything. It hands the function an argument that is
                  the SimplePyxhookkeyevent class.
    """

    def __init__(self, parameters=False):
        threading.Thread.__init__(self)
        self.finished = threading.Event()

        # Give these some initial values
        self.mouse_position_x = 0
        self.mouse_position_y = 0
        self.ison = {"shift": False, "caps": False}

        # Compile our regex statements.
        self.isshift = re.compile('^Shift')
        self.iscaps = re.compile('^Caps_Lock')
        self.shiftablechar = re.compile('|'.join((
            '^[a-z0-9]$',
            '^minus$',
            '^equal$',
            '^bracketleft$',
            '^bracketright$',
            '^semicolon$',
            '^backslash$',
            '^apostrophe$',
            '^comma$',
            '^period$',
            '^slash$',
            '^grave$'
        )))
        self.logrelease = re.compile('.*')
        self.isspace = re.compile('^space$')
        # Choose which type of function use
        self.parameters = parameters
        if parameters:
            self.lambda_function = lambda x, y: True
        else:
            self.lambda_function = lambda x: True
        # Assign default function actions (do nothing).
        self.KeyDown = self.lambda_function
        self.KeyUp = self.lambda_function
        self.MouseAllButtonsDown = self.lambda_function
        self.MouseAllButtonsUp = self.lambda_function
        self.MouseMovement = self.lambda_function

        self.KeyDownParameters = {}
        self.KeyUpParameters = {}
        self.MouseAllButtonsDownParameters = {}
        self.MouseAllButtonsUpParameters = {}
        self.MouseMovementParameters = {}

        self.contextEventMask = [X.KeyPress, X.MotionNotify]

        # Hook to our display.
        self.local_dpy = display.Display()
        self.record_dpy = display.Display()

        self.mouse_buttons_map =   {
            1: "mouse left",
            3: "mouse right",
            2: "mouse middle",
            5: "mouse wheel down",
            4: "mouse wheel up"
        }

    def run(self):
        # Check if the extension is present
        if not self.record_dpy.has_extension("RECORD"):
            print("RECORD extension not found", file=sys.stderr)
            sys.exit(1)
        # r = self.record_dpy.record_get_version(0, 0)
        # print("RECORD extension version {major}.{minor}".format(
        #     major=r.major_version,
        #     minor=r.minor_version
        # ))

        # Create a recording context; we only want key and mouse events
        self.ctx = self.record_dpy.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                #                (X.KeyPress, X.ButtonPress),
                'device_events': tuple(self.contextEventMask),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }])

        # Enable the context; this only returns after a call to
        # record_disable_context, while calling the callback function in the
        # meantime
        self.record_dpy.record_enable_context(self.ctx, self.processevents)
        # Finally free the context
        self.record_dpy.record_free_context(self.ctx)

    def cancel(self):
        self.finished.set()
        self.local_dpy.record_disable_context(self.ctx)
        self.local_dpy.flush()

    def printevent(self, event):
        print(event)

    def HookKeyboard(self):
        # We don't need to do anything here anymore, since the default mask
        # is now set to contain X.KeyPress
        # self.contextEventMask[0] = X.KeyPress
        pass

    def HookMouse(self):
        # We don't need to do anything here anymore, since the default mask
        # is now set to contain X.MotionNotify

        # need mouse motion to track pointer position, since ButtonPress
        # events don't carry that info.
        # self.contextEventMask[1] = X.MotionNotify
        pass

    def processhookevents(self, action_type, action_parameters, events):
        # In order to avoid duplicate code, i wrote a function that takes the
        # input value of the action function and, depending on the initialization,
        # launches it or only with the event or passes the parameter
        if self.parameters:
            action_type(events, action_parameters)
        else:
            action_type(events)

    def processevents(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            print("* received swapped protocol data, cowardly ignored")
            return
        try:
            # Get int value, python2.
            intval = ord(reply.data[0])
        except TypeError:
            # Already bytes/ints, python3.
            intval = reply.data[0]
        if (not reply.data) or (intval < 2):
            # not an event
            return
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(
                data,
                self.record_dpy.display,
                None,
                None
            )
            if event.type == X.KeyPress:
                hookevent = self.keypressevent(event)
                self.processhookevents(self.KeyDown, self.KeyDownParameters, hookevent)
            elif event.type == X.KeyRelease:
                hookevent = self.keyreleaseevent(event)
                self.processhookevents(self.KeyUp, self.KeyUpParameters, hookevent)
            elif event.type == X.ButtonPress:
                hookevent = self.buttonpressevent(event)
                self.processhookevents(self.MouseAllButtonsDown, self.MouseAllButtonsDownParameters, hookevent)
            elif event.type == X.ButtonRelease:
                hookevent = self.buttonreleaseevent(event)
                self.processhookevents(self.MouseAllButtonsUp, self.MouseAllButtonsUpParameters, hookevent)
            elif event.type == X.MotionNotify:
                # use mouse moves to record mouse position, since press and
                # release events do not give mouse position info
                # (event.root_x and event.root_y have bogus info).
                hookevent = self.mousemoveevent(event)
                self.processhookevents(self.MouseMovement, self.MouseMovementParameters, hookevent)

        # print("processing events...", event.type)

    def keypressevent(self, event):
        matchto = self.lookup_keysym(
            self.local_dpy.keycode_to_keysym(event.detail, 0)
        )
        if self.shiftablechar.match(
                self.lookup_keysym(
                    self.local_dpy.keycode_to_keysym(event.detail, 0))):
            # This is a character that can be typed.
            if not self.ison["shift"]:
                keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
                return self.makekeyhookevent(keysym, event)
            else:
                keysym = self.local_dpy.keycode_to_keysym(event.detail, 1)
                return self.makekeyhookevent(keysym, event)
        else:
            # Not a typable character.
            keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
            if self.isshift.match(matchto):
                self.ison["shift"] = self.ison["shift"] + 1
            elif self.iscaps.match(matchto):
                if not self.ison["caps"]:
                    self.ison["shift"] = self.ison["shift"] + 1
                    self.ison["caps"] = True
                if self.ison["caps"]:
                    self.ison["shift"] = self.ison["shift"] - 1
                    self.ison["caps"] = False
            return self.makekeyhookevent(keysym, event)

    def keyreleaseevent(self, event):
        if self.shiftablechar.match(
                self.lookup_keysym(
                    self.local_dpy.keycode_to_keysym(event.detail, 0))):
            if not self.ison["shift"]:
                keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
            else:
                keysym = self.local_dpy.keycode_to_keysym(event.detail, 1)
        else:
            keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
        matchto = self.lookup_keysym(keysym)
        if self.isshift.match(matchto):
            self.ison["shift"] = self.ison["shift"] - 1
        return self.makekeyhookevent(keysym, event)

    def buttonpressevent(self, event):
        # self.clickx = self.rootx
        # self.clicky = self.rooty
        return self.makemousehookevent(event)

    def buttonreleaseevent(self, event):
        # if (self.clickx == self.rootx) and (self.clicky == self.rooty):
        #     # print("ButtonClock {detail} x={s.rootx y={s.rooty}}".format(
        #     #    detail=event.detail,
        #     #    s=self,
        #     # ))
        #     if event.detail in (1, 2, 3):
        #         self.captureclick()
        # else:
        #     pass
        #     print("ButtonDown {detail} x={s.clickx} y={s.clicky}".format(
        #         detail=event.detail,
        #         s=self
        #     ))
        #     print("ButtonUp {detail} x={s.rootx} y={s.rooty}".format(
        #         detail=event.detail,
        #         s=self
        #     ))
        return self.makemousehookevent(event)

    def mousemoveevent(self, event):
        self.mouse_position_x = event.root_x
        self.mouse_position_y = event.root_y
        return self.makemousehookevent(event)

    # need the following because XK.keysym_to_string() only does printable
    # chars rather than being the correct inverse of XK.string_to_keysym()
    def lookup_keysym(self, keysym):
        for name in dir(XK):
            if name.startswith("XK_") and getattr(XK, name) == keysym:
                return name.lstrip("XK_")
        return "[{}]".format(keysym)

    def asciivalue(self, keysym):
        asciinum = XK.string_to_keysym(self.lookup_keysym(keysym))
        return asciinum % 256

    def makekeyhookevent(self, keysym, event):
        pressed = (event.type == X.KeyPress)

        return SimplePyxhookKeyEvent(
            pressed=pressed,
            key=self.lookup_keysym(keysym)
        )

    def makemousehookevent(self, event):
        default = "mouse {} ".format(event.detail)
        button = self.mouse_buttons_map.get(event.detail, default)
        position=(self.mouse_position_x, self.mouse_position_y)

        button_event = (event.type == X.ButtonPress) or (event.type == X.ButtonRelease)

        if button_event:
            return SimplePyxhookMouseButtonEvent(button=button, pressed=(event.type == X.ButtonPress))
        else:
            return SimplePyxhookMouseEvent(position=position)


class pyxhookkeyevent:
    """ This is the class that is returned with each key event.f
        It simply creates the variables below in the class.

        Window         : The handle of the window.
        WindowName     : The name of the window.
        WindowProcName : The backend process for the window.
        Key            : The key pressed, shifted to the correct caps value.
        Ascii          : An ascii representation of the key. It returns 0 if
                         the ascii value is not between 31 and 256.
        KeyID          : This is just False for now. Under windows, it is the
                         Virtual Key Code, but that's a windows-only thing.
        ScanCode       : Please don't use this. It differs for pretty much
                         every type of keyboard. X11 abstracts this
                         information anyway.
        MessageName    : "key down", "key up".
    """

    def __init__(
            self, Window, WindowName, WindowProcName, Key, Ascii, KeyID,
            ScanCode, MessageName):
        self.Window = Window
        self.WindowName = WindowName
        self.WindowProcName = WindowProcName
        self.Key = Key
        self.Ascii = Ascii
        self.KeyID = KeyID
        self.ScanCode = ScanCode
        self.MessageName = MessageName

    def __str__(self):
        return '\n'.join((
            'Window Handle: {s.Window}',
            'Window Name: {s.WindowName}',
            'Window\'s Process Name: {s.WindowProcName}',
            'Key Pressed: {s.Key}',
            'Ascii Value: {s.Ascii}',
            'KeyID: {s.KeyID}',
            'ScanCode: {s.ScanCode}',
            'MessageName: {s.MessageName}',
        )).format(s=self)


class pyxhookmouseevent:
    """This is the class that is returned with each key event.f
    It simply creates the variables below in the class.

        Window         : The handle of the window.
        WindowName     : The name of the window.
        WindowProcName : The backend process for the window.
        Position       : 2-tuple (x,y) coordinates of the mouse click.
        MessageName    : "mouse left|right|middle down",
                         "mouse left|right|middle up".
    """

    def __init__(
            self, Window, WindowName, WindowProcName, Position, MessageName):
        self.Window = Window
        self.WindowName = WindowName
        self.WindowProcName = WindowProcName
        self.Position = Position
        self.MessageName = MessageName

    def __str__(self):
        return '\n'.join((
            'Window Handle: {s.Window}',
            'Window\'s Process Name: {s.WindowProcName}',
            'Position: {s.Position}',
            'MessageName: {s.MessageName}',
        )).format(s=self)


class SimplePyxhookKeyEvent:
    def __init__(self, key, pressed):
        self.key = key
        self.pressed = pressed
        self.released = not pressed

    def __str__(self):
        return "{} {}".format(self.key, "pressed" if self.pressed else "released")


class SimplePyxhookMouseButtonEvent:
    def __init__(self, button, pressed):
        self.button = button
        self.pressed = pressed
        self.released = not pressed

    def __str__(self):
        return "{} {}".format(self.button, "pressed" if self.pressed else "released")


class SimplePyxhookMouseEvent:
    def __init__(self, position):
        self.position = position

    def __str__(self):
        return "Move at {}".format(self.position)


#######################################################################
# ########################END CLASS DEF################################
#######################################################################

if __name__ == '__main__':
    hm = HookManager()
    hm.HookKeyboard()
    hm.HookMouse()
    hm.KeyDown = lambda x: print(x)
    hm.KeyUp = lambda x: print(x)
    hm.MouseAllButtonsDown = hm.printevent
    hm.MouseAllButtonsUp = lambda x: print(x)
    hm.MouseMovement = lambda x: print(x)
    hm.start()
    try:
        time.sleep(100)
    except KeyboardInterrupt:
        pass
    finally:
        hm.cancel()
