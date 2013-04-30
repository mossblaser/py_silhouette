#!/usr/bin/env python

"""
Filters for designs which modify the input design.
"""

from operator import sub, lt

from plotter.design.util import to_paths, get_subpath, bounding_box


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



class NoRegMarksInDesign(Exception):
	"""
	Thrown when extract_regmarks fails to find any registration marks.
	"""
	pass


def extract_regmarks(design):
	"""
	Removes registration marks from the design. Returns a tuple:
	
		(design, (regmark_left, regmark_top, regmark_width, regmark_height))
	
	Where design is the original design with the registration marks removed and
	the other values are the size and loation of the registered regieon
	
	Currently only able to detect Silhouette cutter style registration marks.
	"""
	
	if len(design) == 0:
		raise NoRegMarksInDesign("Empty Design")
	
	design_bb = bounding_box(design)
	
	# The path of the three registration features
	top_left_box   = None
	btm_left_line  = None
	top_right_line = None
	
	# Size of the box and line registrationfeatures
	box_width   = 5.0
	line_length = 20.0
	
	# Feature fuzz threshold
	fuzz_threshold = 0.5
	
	# The design without registration marks
	out = []
	
	def fuzzy_eq(a, b):
		return abs(a - b) < fuzz_threshold
	
	def fuzzy_compare_size(bounding_box, size):
		"""
		Takes a bounding box and a size and returns True if the path's bounding box is
		approximately (size, size) in (w, h).
		"""
		bb_size = map(sub, bounding_box[1], bounding_box[0])
		return fuzzy_eq(bb_size[0], size) \
		   and fuzzy_eq(bb_size[1], size)
	
	
	# Try and find the registration features in the design
	for path in to_paths(design):
		path_bb = bounding_box(path)
		
		# Top left box
		if   fuzzy_eq(path_bb[0][0], design_bb[0][0]) \
		 and fuzzy_eq(path_bb[0][1], design_bb[0][1]) \
		 and fuzzy_compare_size(path_bb, box_width):
			if top_left_box is not None:
				raise NoRegMarksInDesign("More than one top-left box.")
			top_left_box = path_bb
		# Bottom-left line
		elif fuzzy_eq(path_bb[0][0], design_bb[0][0]) \
		 and fuzzy_eq(path_bb[1][1], design_bb[1][1]) \
		 and fuzzy_compare_size(path_bb, line_length):
			if btm_left_line is not None:
				raise NoRegMarksInDesign("More than one bottom-left line.")
			btm_left_line = path_bb
		# Top-right line
		elif fuzzy_eq(path_bb[1][0], design_bb[1][0]) \
		 and fuzzy_eq(path_bb[0][1], design_bb[0][1]) \
		 and fuzzy_compare_size(path_bb, line_length):
			if btm_left_line is not None:
				raise NoRegMarksInDesign("More than one top-right line.")
			top_right_line = path_bb
		# Non-regmark shape
		else:
			out.extend(path)
	
	# Check all registration features are present
	if top_left_box is None:
		raise NoRegMarksInDesign("Top-left box not found!")
	elif top_right_line is None:
		raise NoRegMarksInDesign("Top-right line not found!")
	elif btm_left_line is None:
		raise NoRegMarksInDesign("Btm-left line not found!")
	
	return (out, (top_left_box[0][0], top_left_box[0][1], # Left, Top
	              top_right_line[1][0] - top_left_box[0][0], # Width
	              btm_left_line[1][1] - top_left_box[0][1])) # Height
