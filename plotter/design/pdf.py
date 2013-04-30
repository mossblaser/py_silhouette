#!/usr/bin/env python

"""
A loader for PDF files.

Uses external tool pdf-to-paths taken from the robocut project which uses
Poppler to render the PDF onto a Qt surface which dumps the line segments drawn.
"""

from subprocess import Popen, PIPE

from plotter.design import register_loader


class BadPDF(Exception):
	pass


@register_loader(".pdf", "Portable Document Format")
def load_pdf(data):
	pdf_to_paths = Popen(["pdf-to-paths"],
	                     stdin   = PIPE, # Source stdin from the protocol
	                     stdout  = PIPE, # Supply stdout to the protocol
	                     stderr  = None  # Stderr should not be redirected
	                     ) # Execute in a shell
	design = []
	
	# Run the data through pdf-to-paths
	raw_data, stderr = pdf_to_paths.communicate(data)
	if pdf_to_paths.returncode != 0:
		raise BadPDF()
	
	raw_page_size, _, raw_paths = raw_data.partition("\n\n")
	
	# Presently Unused...
	width, height = map(float, raw_page_size.split("\n"))
	
	for path in raw_paths.split("\n\n"):
		segments = [tuple(map(float,p.strip().split(" ")))
		            for p in path.strip().split("\n")]
		
		for line_segment in zip(segments, segments[1:]):
			design.append(line_segment)
	
	return (width, height), design

