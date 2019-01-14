#!/usr/bin/env python

"""
An common interface to plotting devices.

DeviceBase is the base class from which all Devices descend and specifies a
common interface for plotters.
"""

# All modules containing devices should be listed here
__all__ = [
	"silhouette",
]

# The base class for all devices
from plotter.device.base import DeviceBase

# Directions for continuous movement
MOVE_UP    = object()
MOVE_DOWN  = object()
MOVE_LEFT  = object()
MOVE_RIGHT = object()

class RegistrationMarkNotFoundError(Exception):
	"""
	Raised when an attempt is made to zero on the registration marks fails.
	"""
	pass


