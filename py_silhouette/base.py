#!/usr/bin/env python


class DeviceBase(object):
	"""
	The base class which all devices should inherit and implement.
	"""
	
	
	def __init__(self):
		pass
	
	
	def is_available(self):
		"""
		Returns the number of such devices available.
		"""
		raise NotImplementedError()
	
	
	def open(self, number = None):
		"""
		Connect to the given device number and initialise it for use. The maximum
		device number is given by is_available. None can be given to pick the
		default.
		"""
		raise NotImplementedError()
	
	
	def close(self):
		"""
		Disconnect and clean up after using a device.
		"""
		raise NotImplementedError()
	
	
	def flush(self):
		"""
		Ensure all outstanding commands have been sent.
		"""
		raise NotImplementedError()
	
	
	def is_idle(self):
		"""
		Is the device currently idle?
		"""
		raise NotImplementedError()
	
	
	def get_name(self):
		"""
		Return the human-readable name of the device.
		"""
		raise NotImplementedError()
	
	
	def move_continuous_start(self, direction):
		"""
		Start the cutter carriage moving in the specified direction out of
		MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT
		
		Call should be followed by call to move_carriage_stop.
		"""
		raise NotImplementedError()
	
	
	def move_continuous_stop(self):
		"""
		Stop the carriage moving under use control.
		
		Must be called after move_carriage_start.
		"""
		raise NotImplementedError()
	
	
	def move_home(self):
		"""
		Move the carriage to the home position (with the tool disengaged).
		"""
		raise NotImplementedError()
	
	
	def move_to(self, x, y, use_tool):
		"""
		Move the carriage to the specified (absolute) position in mm. use_tool is a
		boolean specifying whether the current tool should be applied during the
		movement.
		"""
		raise NotImplementedError()
	
	
	def set_tool(self, tool):
		"""
		Set the type of tool to be used. Use get_tools to find out what tools are
		available.
		"""
		raise NotImplementedError()
	
	
	def get_tools(self):
		"""
		Returns a dictionary {tool:human_readable_description, ...}
		"""
		raise NotImplementedError()
	
	
	def set_force(self, force):
		"""
		Set the amount of force to be used in grams.
		"""
		raise NotImplementedError()
	
	
	def get_force_range(self):
		"""
		Returns the range of forces this device can exert in grams as a tuple
		(min,max)
		"""
		raise NotImplementedError()
	
	
	def set_speed(self, speed):
		"""
		Set the movement speed of the device in mm/sec.
		"""
		raise NotImplementedError()
	
	
	def get_speed_range(self):
		"""
		Returns the range of speeds the device can use in mm/sec as a tuple
		(min,max)
		"""
		raise NotImplementedError()
	
	
	def set_area(self, width, height):
		"""
		Sets the size of the drawing area in mm to be used.
		"""
		raise NotImplementedError()
	
	
	def get_area_range(self):
		"""
		Gets the range of areas which can be cut in mm as a tuple
		((min_width, max_width), (min_height, max_height))
		"""
		raise NotImplementedError()
	
	
	def zero_on_home(self):
		"""
		Zero the device at the native home location.
		"""
		raise NotImplementedError()
	
	
	def zero_on_registration_mark( self, width, height, search = True):
		"""
		Zero the device using registration marks printed on the sheet. The style of
		registration mark required is device dependant. See device documentation for
		a specification of what the registration mark looks like.
		
		width, height: The size of the area the registration mark covers in mm. See
		get_registration_mark_area() for the range of acceptable values.
		
		search: The device should search for the registration mark freely. If false
		the device should be positioned such that it will immediately find the
		registration mark.
		"""
		raise NotImplementedError()
	
	
	def get_registration_mark_area(self):
		"""
		Gets the range of areas which can be contained by the registration mark in
		mm as a tuple
		((min_width, max_width), (min_height, max_height))
		"""
		raise NotImplementedError()

