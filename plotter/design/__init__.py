#!/usr/bin/env python

"""
The design package contains functions for loading and manipulating designs for
plotting.

Designs are represented as ordered lists of line segments to cut/plot which in
turn are represented as tuples ((x,y), (x,y)).

Designs can be loaded from common file formats using load_file(filename) or
using a loader function from get_loaders() which conventionally accept a string
of data and return a design. See load.py for details on adding new loaders.

All design loaders return ((width, height), design)

The sort and filter modules contain functions which manipulate designs to
improve plotting/cutting performance. See these files for more details.
"""

# All loader modules should be defined here
__all__ = [
	"hpgl",
	"svg",
	"pdf",
	
	"sort",
	"filter",
]


from load import register_loader, get_loaders, load_file


# Import all our sub-modules to get all the loaders
from plotter.design import *

