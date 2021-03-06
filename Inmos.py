#!/usr/bin/env python

# Inmos link controller Python module
# Copyright (C) 2014 Hessel Schut, hessel@isquared.nl

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import MCP23017
from time import sleep

# SIGNALS maps IMSC012 signals to gpio port B bits (port A is used 
# for the databus.)
SIGNALS = (
        'RnotW', 'RS0', 'RS1',
        'NotCS', 'LinkSpeed', 'Reset',
        'Status', 'LinkReset' )

STROBE_uS = 1   # Number of microseconds to hold strobed signal. 
		# Inmos datasheet states TCSLCSH as 60 ns, 1 us 
		# should be more than adequate.


class Interface:
	"""Link interface adapter class, glues Inmos link adapter to
	i2c bus and abstracts its signals.
	With default i2c addresses, one should not need to deal with
	this class.
	"""
	def __init__(self, i2c_bus_addr=None):
		"""Create Inmos Link, optionally specifying i2c addresses
		of the MCP23017.

		Todo: this should allow for overriding the SIGNALS tuple.
		"""
		if i2c_bus_addr is None:
			self.i2c_bus_addr = MCP23017.DEVICE_ADDRESS
		else:
			self.i2c_bus_addr = i2c_bus_addr
		
		self.gpio = MCP23017.gpio(self.i2c_bus_addr)
		
		# initally tri-state databus to input
		self.gpio.write(MCP23017.IODIRA, MCP23017.INPUT)

		# Control pins are all output
		self.gpio.write(MCP23017.IODIRB, MCP23017.OUTPUT)
		self.gpio.write(MCP23017.OLATB, 0x00)
		
	def read_data(self):
		"""Read data from link adapter.
		"""
		self.gpio.write(MCP23017.IODIRA, MCP23017.INPUT)
		return self.gpio.read(MCP23017.GPIOA)

	def write_data(self, data):
		"""Latch a byte of data on the databus.
		"""
		self.gpio.write(MCP23017.IODIRA, MCP23017.OUTPUT)
		self.gpio.write(MCP23017.OLATA, data)

	def set_signals(self, *args, **kwargs):
		"""Update state of one or more signals.
        	e.g.: set_signal(RnotW = True, RS0 = False, RS1 = True)
        	set_signals() Does not return a value.
		"""
		control_word = self.gpio.read(MCP23017.OLATB)
		for s in kwargs.keys():
			if kwargs.get(s):
				control_word |= (1 << SIGNALS.index(s))
			else:
				control_word &= ~(1 << SIGNALS.index(s))
		self.gpio.write(MCP23017.OLATB, control_word)

	def strobe_signal(self, *args, **kwargs):
		"""Invert a signal's value momentarily.
			e.g.: strobe_signal(NotCS)
		"""
		if len(args) > 1:
			raise AttributeError
		for t in range(0,2):
			self.gpio.write(
				MCP23017.OLATB,
				self.gpio.read(MCP23017.OLATB) ^ (
					1 << SIGNALS.index(args[0]))) 
		sleep(1/(STROBE_uS * 1000000))

class Link:
	"""Create Inmos link instance. 

	An optional linkspeed parameter can be supplied, this defaults to
	10 Mbit/s. The only supported values for link_speed are 10 and 20 
	Mbit/s.
	
	The required link interface instance will be created automatically.
	
	An existing link interface instance can be supplied to the initializer
	if some of its parameters should be overridden.  This can be useful if
	multiple link adapters are to be used, or the default parameters (i2c 
	addresses etc.) are inappropriate.
	"""

	def __init__(self, interface = None, linkspeed = 10):
		if interface is None:
			self.interface = Interface()
		else:
			self.interface = interface

		# assert Reset, deassert NotCS
		self.interface.set_signals(Reset = True, NotCS = True)

		self.linkspeed = linkspeed
		if self.linkspeed == 10: 
			self.interface.set_signals(LinkSpeed = False)
		elif self.linkspeed == 20: 
			self.interface.set_signals(LinkSpeed = True)
		else:
			raise ValueError

		# initialization done, deassert Reset
		self.interface.set_signals(Reset = False)

	def data_present(self):
		"""Read input status register of link adapter for 
		data present, returns True if data is present.
		"""
		self.interface.set_signals(
                        RnotW = True,
                        RS0 = False,
                        RS1 = True,
                        Status = True)

                self.interface.set_signals(NotCS = False)

                data = self.interface.read_data()
                self.interface.set_signals(
                        NotCS = True,
                        Status = False)
                return (data & 0x01 == 0x01)
		

	def output_ready(self):
		"""Read output status register of the link adapter
		to determine if the link is ready. Returns True for
		a ready link.
		"""
		self.interface.set_signals(
                        RnotW = True,
                        RS0 = True,
                        RS1 = True,
                        Status = True)

                self.interface.set_signals(NotCS = False)

                data = self.interface.read_data()
                self.interface.set_signals(
                        NotCS = True,
                        Status = False)
                return (data & 0x01 == 0x01)

	def enable_interrupts(self):
		"""Enable the InputInt and OutputInt lines.
		N.B. enable_interrupts() clears the link ISR and OSR registers.
		"""
		# Enable InputInt (write to ISR)
		self.interface.set_signals(
			RnotW = False,
			RS0 = False, 
			RS1 = True,
			Status = True)
		self.interface.write_data(0x02)
		self.interface.strobe_signal('NotCS')

		# Enable OutputInt (write to OSR)
		self.interface.set_signals(
			RnotW = False,
			RS0 = True, 
			RS1 = True)
		self.interface.write_data(0x02)
		self.interface.strobe_signal('NotCS')

		self.interface.set_signals(Status = False)

	def disable_interrupts(self):
		"""Disable the InputInt and OutputInt lines.
		N.B. disable_interrupts() clears the link ISR and OSR registers.
		"""
		# Disable InputInt (write to ISR)
		self.interface.set_signals(
			RnotW = False,
			RS0 = False, 
			RS1 = True,
			Status = True)
		self.interface.write_data(0x00)
		self.interface.strobe_signal('NotCS')

		# Disable OutputInt (write to OSR)
		self.interface.set_signals(
			RnotW = False,
			RS0 = True, 
			RS1 = True)
		self.interface.write_data(0x00)
		self.interface.strobe_signal('NotCS')

		self.interface.set_signals(Status = False)

	def write(self, data):
		"""Write a byte of data to the link.
		"""

		self.interface.set_signals(
			RnotW = False,
			RS0 = True, 
			RS1 = False,
			Status = True)
		self.interface.write_data(data)
		self.interface.strobe_signal('NotCS')
		self.interface.set_signals(Status = False)

	def read(self):
		"""Read a byte of data from the link.
		"""

		self.interface.set_signals(
			RnotW = True,
			RS0 = False,
			RS1 = False,
			Status = True)

		# Separate to make sure register selects are stable
		# before asserting ~CS. (Should check if this is 
		# neccessary, though.)
		self.interface.set_signals(NotCS = False)

		data = self.interface.read_data()
		self.interface.set_signals(
			NotCS = True, 
			Status = False)
		return data

	def reset(self, *args):
		"""Strobe LinkReset, this resets a device connected
		to the link adapter.
		When an optional state is given, the LinkReset line
		will latch to that state.
		"""
		
		if len(args) == 0:
			self.interface.strobe_signal('LinkReset')
		else:
			self.interface.set_signals(LinkReset = args[0])
