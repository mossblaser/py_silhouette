#!/usr/bin/env python

"""
A rather dirty interactive semi-automated test programme for py_silhouette.

Have a printed copy of test_sheet.svg (or PDF version) to hand, connect your
plotter and run this script, following the instructions and verifying the
expected behaviour.
"""

import math
from py_silhouette import SilhouetteDevice, enumerate_devices

print("Test 0: Discovery and connection.")
print("  Test 0a: Enumerating devices:")
for dev, params in enumerate_devices():
    print("    Found '{}'".format(params.product_name))
input("    The expected device models should have been listed. <Press Enter>")

print("  Test 0b: Connecting to first device")
d = SilhouetteDevice()
print("    Device name: '{}'".format(d.get_name()))
input("    Device name should be sensible. <Press Enter>")

print("  Test 0c: Unloaded state")
print("    Device state: '{}' (expected: unloaded)".format(d.get_state().name))
input("    Load the printed test sheet then <Press Enter>")

print("  Test 0d: Loaded state")
print("    Device state: '{}' (expected: ready)".format(d.get_state().name))
input("    Insert a pen then <Press Enter>")

print("Test 1: Registration marks")
d.zero_on_registration_mark(170, 140)
d.set_speed(d.params.tool_speed_max)
d.set_force(d.params.tool_force_max)
d.set_tool_diameter(0.0)

print("  Test 1a-e: Aligned with top of marks")
d.move_to(40, 0, False)
d.move_to(60, 0, True)

d.move_to(0, 40, False)
d.move_to(0, 60, True)

d.move_to(170, 40, False)
d.move_to(170, 60, True)

d.move_to(40, 140, False)
d.move_to(60, 140, True)

d.move_to(150, 140, False)
d.move_to(170, 140, True)
d.move_to(170, 120, True)

d.move_home()
d.flush()
input("    Lines should be in marked area. <Press Enter>")


print("Test 2: Tool diameter")
print("  Test 2a: Tool diameter = 0")
d.set_tool_diameter(0.0)
d.move_to(20, 100, False)
d.move_to(20, 80, True)
d.move_to(40, 80, True)
d.move_to(40, 100, True)
d.move_to(20, 100, True)
d.move_home()
d.flush()
input("    Rectangle should have perfect corners. <Press Enter>")

print("  Test 2b: Tool diameter = 0,9")
d.set_tool_diameter(0.9)
d.move_to(60, 100, False)
d.move_to(60, 80, True)
d.move_to(80, 80, True)
d.move_to(80, 100, True)
d.move_to(60, 100, True)
d.move_home()
d.set_tool_diameter(0.0)
d.flush()
input("    Rectangle should have extended corners. <Press Enter>")

print("Test 3: Buffer depth test")
num_steps = 300
for step in range(num_steps):
    perc = step / float(num_steps-1)
    dx = math.cos(perc * 2 * math.pi) * 20.0
    dy = math.sin(perc * 2 * math.pi) * 20.0
    d.move_to(125+dx, 90+dy, step != 0)
d.move_home()
d.flush()
input(" Circle should have been drawn correctly. <Press Enter>")

print("Test 4: Speed test")
for dx, speed_perc in [(0, 0.0), (5, 0.25), (10, 0.5), (15, 0.75), (20, 1.0)]:
    tsmin = d.params.tool_speed_min
    tsmax = d.params.tool_speed_max
    d.set_speed(tsmin + ((tsmax-tsmin)*speed_perc))
    d.move_to(55+dx, 55, False)
    d.move_to(75+dx, 35, True)
d.set_speed(d.params.tool_speed_max)
d.move_home()
d.flush()
input(" Lines should have been drawn at different speeds. <Press Enter>")

print("Test 5: Force test")
for dx, force_perc in [(0, 0.0), (5, 0.25), (10, 0.5), (15, 0.75), (20, 1.0)]:
    tfmin = d.params.tool_force_min
    tfmax = d.params.tool_force_max
    d.set_force(tfmin + ((tfmax-tfmin)*force_perc))
    d.move_to(85+dx, 55, False)
    d.move_to(105+dx, 35, True)
d.set_force(d.params.tool_force_max)
d.move_home()
d.flush()
input(" Lines should have been drawn at different forces. <Press Enter>")
