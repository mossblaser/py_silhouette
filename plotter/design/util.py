#!/usr/bin/env python

"""
Utilities for sorters/filters. Intended for internal use by the design package.
"""

import operator

from math import sqrt, sin, cos, tan, asin, acos, atan

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



class DependencyTree(object):
	"""
	A dependency tree structure which is designed for efficiently extracting the
	hierarchical dependencies of paths which surround other paths. See
	paths_by_dependency().
	"""
	
	def __init__(self
	            , value    = None
	            , children = None
	            , ordering = None
	            ):
		self.value    = value
		self.children = children or []
		self.ordering = ordering or operator.lt
	
	
	def add(self, value):
		if self.value is None or self.ordering(self.value, value):
			# Is contained by this node
			
			# Is it contained by any child?
			for child in self.children:
				if self.ordering(child.value, value):
					child.add(value)
					return
			
			# Nope, it is a peer of any of our children
			self.children.append(DependencyTree(value, ordering=self.ordering))
		else:
			# Is a parent to this node
			
			# Clone this node and make it a child of this node, resetting its contents
			child_node = DependencyTree(self.value, self.children, self.ordering)
			self.value = value
			self.children = [child_node]
	
	
	def remove(self, value):
		if self.value == value:
			assert(self.children == [])
			self.value = None
		else:
			for child in self.children[:]:
				child.remove(value)
				if child.value is None:
					self.children.remove(child)
	
	
	def get_leaves(self):
		if self.children:
			return sum((child.get_leaves() for child in self.children), [])
		else:
			return [self.value]
	
	
	def __repr__(self):
		children = "\n".join(map(repr, self.children))
		children = "\n  ".join(children.split("\n"))
		
		return ("DependencyTree(%s)\n  %s"%(repr(self.value), children)).rstrip()
	
	
	def __len__(self):
		return (1 if self.value is not None else 0) \
		     + sum(map(len, self.children))



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
	Takes an iterable of lines ((x,y), (x,y)) and returns the bounding box ((x,y),
	(x,y)).
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
		
		h = line_length(line)
		
		theta = asin((line[1][1] - line[0][1]) / h)
		
		h = (h - (length - req_length))
		
		a = cos(theta) * h
		o = sin(theta) * h
		
		out.append((line[0], (line[0][0] + a, line[0][1] + o)))
	
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
	
	tree = DependencyTree(ordering = (lambda x,y:
	                                  box_contains_box(bounding_box(x),
	                                                   bounding_box(y))))
	
	out = []
	
	# Convert design to paths and add those paths to the DependencyTree
	map(tree.add, to_paths(design))
	
	# Repeatedly remove the leaves (i.e. those paths which do not contain any
	# other paths)
	while tree:
		leaves = tree.get_leaves()
		out.append(leaves)
		map(tree.remove, leaves)
	
	return out
