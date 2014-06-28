#!/usr/bin/env python

import smbus

# data bus PCF8574 address
DATABUS_I2C_ADDR = 0x20

# control PCF8574 address
CONTROL_I2C_ADDR = 0x21

i2c = smbus.SMBus(0)

class c011:
	def __init__(self, dbus_addr=None, ctrl_addr=None):
		"""create Inmos Link, optionally specifying i2c addresses"""
		
		if dbus_addr is None:
			self.dbus_addr = DATABUS_I2C_ADDR
		else:
			self.dbus_addr = dbus_addr
		
		if ctrl_addr is None:
			self.ctrl_addr = CONTROL_I2C_ADDR
		else:
			self.ctrl_addr = ctrl_addr
		
	# ctrl maps c011 control signals to PCF8574 bits
	ctrl = [
		'LED0', 'LinkSpeed', 'LED1', 'Reset', 
		'RS0', 'RS1', 'RnotW', 'notCS'
	]

	def reset(self):
		"""Reset the C011 link adapter"""
		# assert reset
		i2c.write_byte(self.ctrl_addr, 1<<self.ctrl.index('Reset'))
		# make databus high for input
		i2c.write_byte(self.dbus_addr, 0xff)
		# deassert reset, deassert notCS
		i2c.write_byte(self.ctrl_addr, 1<<self.ctrl.index('notCS'))
	
	def write_byte(self, data):
		"""write data to the link"""
		# setup regs for write
		i2c.write_byte(self.ctrl_addr, 
			1<<self.ctrl.index('RS0') & 1<<self.ctrl.index('notCS'))
		# copy data to bus
		i2c.write_byte(self.dbus_addr, data)
		# assert notCS
		i2c.write_byte(self.ctrl_addr, 1<<self.ctrl.index('RS0'))
		# deassert notCS
		i2c.write_byte(self.ctrl_addr, 1<<self.ctrl.index('notCS'))
		
	
	def read_byte(self):
		"""read a byte from link"""
		
		return data
	
	def link_ready(self):
		"""test if link is ready (i.e. output buffer empty)"""
		
		return status

