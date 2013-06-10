#!/usr/bin/env python

"""
Utilities for sorters/filters. Intended for internal use by the design package.
"""

import operator

from math import sqrt

from collections import defaultdict


class Lines(object):
	"""
	An object which contains a set of lines which can be queried by end-point.
	"""
	
	def __init__(self):
		# For every starting point, a set of end-points.
		self._lines_from = defaultdict(set)
	
	
	def add_line(self, line):
		"""
		Add a new line segment.
		"""
		start,end = line
		# Don't add zero-length lines
		if start == end:
			return
		
		self._lines_from[start].add(end)
		self._lines_from[end].add(start)
	
	
	def remove_line(self, start, end):
		"""
		Remove a line segment.
		"""
		# Zero-length lines aren't allowed so don't remove them
		if start == end:
			return
		
		self._lines_from[start].remove(end)
		self._lines_from[end].remove(start)
	
	
	def lines_from(self, point):
		"""
		Returns a list of end-points for lines from this point.
		"""
		return self._lines_from[point]
	
	
	def __iter__(self):
		# Iterative over all non-empty starting points.
		return iter(filter( (lambda p: len(self._lines_from[p]))
		                  , self._lines_from.iterkeys()))
	
	
	def __len__(self):
		return len(list(iter(self)))



class DependencyOrder(object):
	"""
	A structure used for ordering boxes by their dependencies, that is, placing
	outer boxes before their inner boxes. 
	
	When given a set of [(x1,y1), (x2,y2), ...] lists (that is, of paths), returns
	a series of lists where elements in a list may be reordered without
	conciquence but the lists enforce the dependency order.
	
	Hideously expensive in algorithmic complexity but it does, at least, work...
	It feels a lot like a bubble sort and probably has a similar (maybe worse)
	complexity.
	"""
	
	def __init__(self, initial_list = None):
		# List of items which may be reordered freely
		self.items = []
		
		# Gets a DependencyOrder object containing only objects contained by some
		# element of self.items. Access via self.next_set.
		self._next_set = None
		
		# Initialise if specified.
		for item in (initial_list or []):
			self.add(item)
	
	
	@property
	def next_set(self):
		"""
		Get the next set of dependency items in the chain, creating a new one if it
		is None.
		"""
		if self._next_set is None:
			self._next_set = DependencyOrder()
		return self._next_set
	
	
	def a_contains_b(self, a, b):
		"""
		The partial-ordering relation between paths.
		"""
		return box_contains_box(bounding_box(a), bounding_box(b))
	
	
	def add(self, value):
		"""
		Add a new element to the object.
		"""
		for cur_value in self.items[:]:
			# If any value currently in the list is greater than this, place this in
			# the next set.
			if self.a_contains_b(cur_value, value):
				return self.next_set.add(value)
		
		for cur_value in self.items[:]:
			# If any values are less than this, move them into the next set
			if self.a_contains_b(value, cur_value):
				self.next_set.add(cur_value)
				self.items.remove(cur_value)
		
		self.items.append(value)
	
	
	def __iter__(self):
		"""
		Iterate over the lists of lists of reorderable paths.
		"""
		class DependencyOrderIter(object):
			def __init__(self, do): self.do = do
			def next(self):
				if not self.do.items:
					raise StopIteration()
				else:
					do = self.do
					self.do = do.next_set
					return do.items
		return DependencyOrderIter(self)
def to_paths(design):
	"""
	Gets a list of paths as lists of ((x,y),(x,y)) tuples for continuous line
	segments in the input design.
	
	Paths are added in order of when the first line segment of the path was listed
	in the design. Within each path the lines will be in the same order that they
	were listed in the original design. i.e. This method is stable if all paths in
	the input design are contiguous sequences of lines.
	"""
	
	paths = []
	
	# A relation of points to the line segment it belongs to
	point_to_path = dict()
	
	for line in design:
		start,end = line
		path = point_to_path.get(start,
		                         point_to_path.get(end, None))
		if path is None:
			path = []
			paths.append(path)
		
		path.append((start, end))
		
		point_to_path[start] = path
		point_to_path[end]   = path
	
	return paths



def bounding_box(lines):
	"""
	Takes an iterable of lines ((x,y), (x,y)) and returns the bounding box
	((x_left,y_top), (x_right,y_bottom)).
	"""
	points = sum(map(list, lines), [])
	
	assert(len(points) > 0)
	
	return (map(min, zip(*points)), map(max, zip(*points)))


def line_length(line):
	"""
	Returns the length of a line segment ((x,y), (x,y)).
	"""
	return sqrt(sum((a-b)**2 for a,b in zip(*line)))


def get_subpath(path, req_length):
	"""
	Returns the path which is length long starting from the start.
	"""
	
	out = []
	length = 0
	
	# Keep adding line segments until the required length is met
	for line in path:
		if length >= req_length:
			break
		
		out.append(line)
		length += line_length(line)
	
	# Truncate the last segment if needed
	if length > req_length:
		line = out.pop()
		length -= line_length(line)
		
		factor = (req_length - length) / line_length(line)
		
		x,y = map(operator.sub, line[1], line[0])
		x *= factor
		y *= factor
		
		out.append((line[0], (line[0][0] + x, line[0][1] + y)))
	
	return out


def box_contains_box(outer, inner):
	"""
	Tests if box outer fully contains (and doesn't equal) inner.
	"""
	
	return (inner[0][0] >= outer[0][0]
	    and inner[0][1] >= outer[0][1]
	    and inner[1][0] <= outer[1][0]
	    and inner[1][1] <= outer[1][1]
	)


def paths_by_dependency(design):
	"""
	Takes a design and returns a list of lists of paths. Each list of paths
	are those paths contained by the paths in the following list.
	"""
	
	do = DependencyOrder(to_paths(design))
	return list(do)[::-1]
