#!/usr/bin/env python

"""
Filters for designs which modify the input design.
"""

from operator import sub

from plotter.design.util import to_paths, get_subpath


def offset(design, origin):
	"""
	Shifts all lines such that (0,0) would be at the coordinate origin in the
	original design.
	"""
	
	out = []
	for line in design:
		out.append(tuple(map( (lambda point: tuple(map( sub
		                                              , point
		                                              , origin)))
		                    , line)))
	
	return out


def overcut_closed_paths(design, amount = 1.0):
	"""
	For all closed paths (those whose cutting order starts and ends at the same
	position) extend the cut slightly at the end to ensure clean seperation.
	
	amount is the distance in design units (presumably mm) to over-cut.
	"""
	
	paths = to_paths(design)
	
	for path in paths:
		if path[0][0] == path[-1][1]:
			path.extend(get_subpath(path, amount))
	
	return sum(paths, [])

