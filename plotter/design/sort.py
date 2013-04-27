#!/usr/bin/env python

"""
Sorters for designs, generally aimed at optimising cutting performance.

A sorter takes a list of line segments ((x,y), (x,y)) and sorts them in an order
more optimal for cutting. Various planners exist which generate plans optimised
in different ways.
"""

from plotter.design.util import Lines, paths_by_dependency


def naive(design, cur_pos = (0,0)):
	"""
	A naive sorter which starts from the line closest to cur_pos and follows on to
	the next nearest segment until all segments have been drawn.
	"""
	
	# Nothing to do with an empty design...
	if len(design) == 0:
		return []
	
	# The sorted list of line segments
	out = []
	
	# The set of lines yet to be plotted
	unplotted_lines = Lines()
	for line in design:
		unplotted_lines.add_line(line)
	
	
	# Process all available lines
	while unplotted_lines:
		# Are there any lines from our current position?
		if len(unplotted_lines.lines_from(cur_pos)) > 0:
			# Yes, pick one of the lines
			target = iter(unplotted_lines.lines_from(cur_pos)).next()
			
			# Plot it
			out.append((cur_pos, target))
			unplotted_lines.remove_line(cur_pos, target)
			cur_pos = target
		else:
			# Nope, move to the nearest line
			def distance(dest):
				delta = (
					dest[0] - cur_pos[0],
					dest[1] - cur_pos[1],
				)
				return delta[0]**2 + delta[1]**2
			
			# Move to the next nearest line
			cur_pos = min(unplotted_lines, key = distance)
	
	return out




def hierarchical( design
                , cur_pos = (0,0)
                , level_sort   = naive
                , path_presort = None
                ):
	"""
	A sort which attempts to cut shapes contained within other shapes before the
	containing shape before using the naive shortest path heuristic. This helps
	prevent a cutter cutting out an area of the media which then becomes detatched
	and thus un-cuttable.
	
	cur_pos is the position of the cursor when the design is about to be plotted.
	
	level_sort is the sorting function applied to the lines for all paths at each
	level of the hierarchy. It is expected to take cur_pos as its second argument.
	By default this is the naive sort.
	
	path_presort is a sorting function which is applied to each paths
	individually before all paths at that level in the hierarchy are sorted.
	"""
	
	# Nothing to do with an empty design...
	if len(design) == 0:
		return []
	
	out = []
	
	for level_paths in paths_by_dependency(design):
		if path_presort is not None:
			level_paths = map(path_presort, level_paths)
		
		out.extend(level_sort(sum(level_paths, []), cur_pos))
		
		# Current position is the end of the last line plotted
		cur_pos = out[-1][1]
	
	return out
