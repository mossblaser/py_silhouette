#!/usr/bin/env python

"""
An interface to plotting devices.

get_devices() is provided for users to get the available Device classes for
instantiation.

DeviceBase is the base class from which all Devices descend and specifies a
common interface for plotters.

register_device() is a decorator provided for driver developers and will make a
device class appear in the get_devices() response.
"""

# All modules containing devices should be listed here and will be loaded at the
# end of this file.
__all__ = [
	"silhouette",
]

_devices = []

def register_device(human_name = None):
	"""
	A decorator which should be added to any Device definition which is intended
	to be user facing. A human-readable name should be given for the driver too.
	"""
	def _register_device(device_class):
		global _devices
		_devices.append((device_class, human_name or device_class.__name__))
		return device_class
	
	return _register_device


def get_devices():
	"""
	Returns a list [(device_class, human_name), ...] containing all supported devices.
	"""
	return _devices[:]


# The base class for all devices
from plotter.device.base import DeviceBase

# Directions for continuous movement
MOVE_UP    = object()
MOVE_DOWN  = object()
MOVE_LEFT  = object()
MOVE_RIGHT = object()

# Import all our sub-modules to get all the device drivers
from plotter.device import *
