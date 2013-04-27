#!/usr/bin/env python

"""
A loader for HPGL files.

This is currently only designed to support the output exported by Inkscape
meaning only PU and PD commands are supported.
"""

from plotter.design import register_loader


def plu_to_mm(plu):
	# 0.025mm per plu
	return plu * 0.025


@register_loader(".plt", "HP Graphics Language")
@register_loader(".hpgl", "HP Graphics Language")
def load_hpgl(data):
	# Split the HPGL file into individual commands
	commands = data.split(";")
	
	# The Design that will be populated from the file.
	design = set()
	
	# The position of the virtual plotter
	cur_pos = (0,0)
	
	for command in commands:
		if command.startswith("PU"):
			if len(command) <= 2:
				continue
			# Pen-Up: Move to the given position with the pen up
			x, y = map(plu_to_mm, map(int, command[2:].split(",")))
			cur_pos = (x,y)
		
		elif command.startswith("PD"):
			if len(command) <= 2:
				continue
			# Pen-Down: Move to the given position with the pen down
			x, y = map(plu_to_mm, map(int, command[2:].split(",")))
			end_pos = (x,y)
			design.add((cur_pos, end_pos))
			cur_pos = end_pos
	
	return design


