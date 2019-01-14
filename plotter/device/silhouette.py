#!/usr/bin/env python

"""
Device drivers for Silhouette cutter/plotters.
"""

import usb.core
import usb.util

from plotter.device import DeviceBase
from plotter.device import MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT
from plotter.device import RegistrationMarkNotFoundError


class SilhouetteBase(DeviceBase):
	"""
	A base driver containing common functions for all Silhouette cutters.
	"""
	
	# The Silhouette vendor ID
	VENDOR  = 0x0b4d
	
	# The product ID, should be overridden by an inherited class
	PRODUCT = None
	
	# The USB endpoint addresses used by the device
	ENDPOINT_CMD_SEND = 0x01
	ENDPOINT_CMD_RECV = 0x82
	
	TOOL_PEN    = 0
	TOOL_CUTTER = 18
	
	def __init__(self):
		DeviceBase.__init__(self)
		
		# A buffer to place items to send in
		self._send_buffer = ""
	
	
	def _find_devices(self):
		"""
		Returns a set of USB devices which have the appropriate product ID.
		"""
		assert(self.PRODUCT is not None)
		return list(usb.core.find(find_all=True
		                         , idVendor=self.VENDOR
		                         , idProduct=self.PRODUCT
		                         ))
	
	
	def is_available(self):
		"""
		Returns the number of such devices available.
		"""
		return len(self._find_devices())
	
	
	def open(self, number = None):
		"""
		Connect to the given device number and initialise it for use. The maximum
		device number is given by is_available. None can be given to pick the
		default.
		"""
		# Get the USB device
		self.dev = self._find_devices()[number or 0]
		
		# Get the first interface
		self.interface = self.dev[0][(0,0)]
		
		# Detach any kernel drivers so we can control the device
		if self.dev.is_kernel_driver_active(self.interface.bInterfaceNumber):
			self.dev.detach_kernel_driver(self.interface.bInterfaceNumber)
		
		# Reset the device
		self.dev.reset()
		
		# Set default configuration to the first
		self.dev.set_configuration(1)
		
		# Claim control of the interface
		usb.util.claim_interface(self.dev, self.interface)
		
		
		# Get references to the send and receive endpoints
		self.ep_send = usb.util.find_descriptor( self.interface
		                                       , bEndpointAddress = self.ENDPOINT_CMD_SEND
		                                       )
		self.ep_recv = usb.util.find_descriptor(self.interface
		                                       , bEndpointAddress = self.ENDPOINT_CMD_RECV
		                                       )
		
		# This seems to initialise the device too...
		self.get_name()
	
	
	def _send(self, data):
		"""
		Send some data to the device.
		"""
		self._send_buffer += data
	
	
	def _receive(self, size = 64, timeout = 0):
		"""
		Send some data to the device.
		"""
		return "".join(map(chr, self.ep_recv.read(size, timeout)))
	
	
	def close(self):
		"""
		Disconnect and clean up after using a device.
		"""
		# Just flush remaining commands
		self.flush()
	
	
	def flush(self):
		"""
		Ensure all outstanding commands have been sent.
		"""
		if len(self._send_buffer) == 0:
			return
		
		# Grab everything in the send buffer
		data = self._send_buffer
		self._send_buffer = ""
		
		# Send it all
		to_send = len(data)
		assert(self.ep_send.write(data, 0) == to_send)
	
	
	def get_name(self):
		"""
		Return the human-readable name of the device.
		"""
		self._send("FG\x03")
		self.flush()
		return self._receive().rstrip(" \x03")
	
	
	def is_idle(self):
		"""
		Is the device currently idle?
		"""
		self._send("\x1b\x05")
		self.flush()
		return self._receive()[0] == "0"
	
	
	def move_continuous_start(self, direction):
		"""
		Stop the carriage moving under use control.
		
		Must be called after move_carriage_start.
		"""
		self._send("\x1b\x00%s"%({
			MOVE_DOWN  : "\x01",
			MOVE_UP    : "\x02",
			MOVE_RIGHT : "\x04",
			MOVE_LEFT  : "\x08",
		}[direction]))
	
	
	def move_continuous_stop(self):
		"""
		Stop the carriage moving under use control.
		
		Must be called after move_carriage_start.
		"""
		self._send("\x1b\x00\x00")
	
	
	def move_home(self):
		"""
		Move the carriage to the home position (with the tool disengaged).
		"""
		self._send("H\x03")
	
	
	def _clamp(self, val, min_val, max_val):
		"""
		Clamp the value to between the two limits.
		"""
		return max(min_val, min(max_val, val))
	
	
	def _mm(self, mm):
		"""
		Convert from mm to machine units (disallow negative numbers)
		"""
		return max(int(mm*20), 0)
	
	
	def move_to(self, x, y, use_tool = False):
		"""
		Move the carriage to the specified (absolute) position in mm. use_tool is a
		boolean specifying whether the current tool should be applied during the
		movement.
		"""
		self._send("%s%d,%d\x03"%(
			"D" if use_tool else "M",
			self._mm(y),
			self._mm(x),
		))
	
	
	def set_tool(self, tool):
		"""
		Set the type of tool to be used. Use get_tools to find out what tools are
		available.
		"""
		assert(tool in self.get_tools().values())
		self._send("FC%d\x03"%tool)
	
	
	def get_tools(self):
		"""
		Returns a dictionary {human_readable_description:tool, ...}
		"""
		return {
			"Pen"    : self.TOOL_PEN,
			"Cutter" : self.TOOL_CUTTER,
		}
	
	
	def _grams(self, grams):
		"""
		Convert a unit in grams into machine units.
		"""
		return self._clamp(int((grams / 7.0) + 0.5), 1, 33)
	
	
	def set_force(self, force):
		"""
		Set the amount of force to be used in grams.
		"""
		self._send("FX%d,0\x03"%self._grams(force))
	
	
	def get_force_range(self):
		"""
		Returns the range of forces this device can exert in grams as a tuple
		(min,max)
		"""
		return (7.0, 230.0)
	
	
	def _mmsec(self, mmsec):
		"""
		Convert a speed in mm/sec into machine units.
		"""
		return self._clamp(mmsec/100.0, 1,10)
	
	
	def set_speed(self, speed):
		"""
		Set the movement speed of the device in mm/sec.
		"""
		self._send("!%d,0\x03"%self._mmsec(speed))
	
	
	def get_speed_range(self):
		"""
		Returns the range of speeds the device can use in mm/sec as a tuple
		(min,max)
		"""
		return (100.0, 1000.0)
	
	
	def set_area(self, width, height):
		"""
		Sets the size of the drawing area in mm to be used.
		"""
		self._send("Z%d,%d\x03"%(
			self._mm(self._clamp(height, *self.get_area_range()[1])),
			self._mm(self._clamp(width,  *self.get_area_range()[0])),
		))
	
	
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
		self._send("FN0\x03")
	
	
	def zero_on_registration_mark( self, width, height, search = True):
		"""
		Zero the device using registration marks printed on the sheet.
		
		width, height: The size of the area the registration mark covers in mm. See
		get_registration_mark_area() for the range of acceptable values.
		
		search: The device should search for the registration mark freely. If false
		the device should be positioned with the tool over the black square.
		
		Reg marks should look like this:
		                  ____
		##                    |
		##                    |
		                      |
		
		
		
		
		
		
		
		|                     |
		|                     |
		|____             ____|
		
		Where the #s are a 5mm black square and the lines are 0.5mm thick and 20mm
		long.
		"""
		
		LINE_THICKNESS = 20.0
		LINE_LENGTH    = 0.5
		
		# Run at maximum speed
		self.set_speed(self.get_speed_range()[1])
		
		# Set the zero position to the place we're about to home in on
		self._send("TB99\x03")
		
		# Set registration mark line length
		self._send("TB51,%d\x03"%self._mm(LINE_LENGTH))
		
		# XXX: Unknown purpose, fails without
		self._send("TB52,2\x03")
		
		# Set registration mark line thickness
		self._send("TB53,%d\x03"%self._mm(LINE_THICKNESS))
		
		# The offset of the black square from the correct location
		self._send("TB54,0,0\x03")
		
		# Use registration marks to calibrate scale and rotation
		self._send("TB55,1\x03")#
		
		# Scan for registration marks
		self._send("TB%s23,%d,%d,117,75\x03"%(
			"1" if search else "",
			self._mm(self._clamp(height, *self.get_registration_mark_area()[1])),
			self._mm(self._clamp(width,  *self.get_registration_mark_area()[0])),
		))
		
		self.flush()
		
		# Wait for a response (this may take some time!)
		if self._receive() != "    0\x03":
			raise RegistrationMarkNotFoundError()
	
	
	def get_registration_mark_area(self):
		"""
		Gets the range of areas which can be contained by the registration mark in
		mm as a tuple
		((min_width, max_width), (min_height, max_height))
		"""
		# Just the same as the page area. Probably not true but whatever!
		return self.get_area_range()



class Portrait(SilhouetteBase):
	# The product ID of the Silhouette Portrait
	PRODUCT = 0x1123
	
	
	def get_area_range(self):
		"""
		Gets the range of areas which can be cut in mm as a tuple
		((min_width, max_width), (min_height, max_height))
		"""
		# As taken from the original software's manual:
		#   Width: 3 to 8.5 inches
		#   Height: 3 to 40 inches
		return ((76.2, 203.2), (76.2, 1016.0))

