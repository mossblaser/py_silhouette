#!/usr/bin/env python

"""
Utilities for registering and acessing design loader functions.
"""


_loaders = []


def register_loader(extension, human_name = None):
	"""
	A decorator which should be added to any loaders which registers them for use
	by load_file() etc.
	"""
	def _register_loader(loader):
		global _loaders
		_loaders.append((loader, extension, human_name))
		return loader
	
	return _register_loader



def get_loaders():
	"""
	Returns a list [(loader, extension, human_name), ...] containing all supported
	loaders.
	"""
	return _loaders[:]



def load_file(filename):
	"""
	Given a filename, picks a loader and returns a set of line segments as
	((startx,starty),(endx,endy)). If no loader was found, returns None.
	"""
	for loader, extension, _ in _loaders:
		if filename.endswith(extension):
			return loader(open(filename,"r").read())
	
	return None

