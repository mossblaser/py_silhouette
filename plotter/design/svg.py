#!/usr/bin/env python

"""
A loader for SVG files.

Uses external tool svg-to-paths taken from the robocut project which uses Qt to
render the SVG onto a surface which dumps the line segments drawn.
"""

from subprocess import Popen, PIPE

from plotter.design import register_loader


class BadSVG(Exception):
	pass


@register_loader(".svg", "Scaleable Vector Graphics")
def load_svg(data):
	svg_to_paths = Popen(["svg-to-paths"],
	                     stdin   = PIPE, # Source stdin from the protocol
	                     stdout  = PIPE, # Supply stdout to the protocol
	                     stderr  = None  # Stderr should not be redirected
	                     ) # Execute in a shell
	design = []
	
	# Run the data through svg-to-paths
	raw_data, stderr = svg_to_paths.communicate(data)
	if svg_to_paths.returncode != 0:
		raise BadSVG()
	
	raw_page_size, _, raw_paths = raw_data.partition("\n\n")
	
	# Presently Unused...
	width, height = map(float, raw_page_size.split("\n"))
	
	for path in raw_paths.split("\n\n"):
		segments = [tuple(map(float,p.strip().split(" ")))
		            for p in path.strip().split("\n")]
		
		for line_segment in zip(segments, segments[1:]):
			design.append(line_segment)
	
	return design



