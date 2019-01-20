`py_silhouette`: Control Silhouette plotters/cutters from Python
================================================================

This repository contains a library for controlling the
[Silhouette](https://www.silhouetteamerica.com/) series of desktop
plotters/cutters. It is intended as a base for building generic or specialised
plotting/cutting software.

This library is not:

* A complete plotting tool -- it is just a library.
* A general purpose plotter control library -- it only controls the Silhouette
  series of desktop plotters.
* A library of generic utilities for plotting -- it only contains low-level
  device control functionality.
* A complete reverse engineering of every hardware command -- it contains
  enough to implement all advertised device functionality though some software
  emulation of certain functions may be required (e.g. for manual head movement
  control).

Usage Example
-------------

A quick-and-dirty example uses `py_silhouette` to draw a rectangle is
shown below:

    from py_silhouette import SilhouetteDevice
    
    # Connect to first available device
    d = SilhouetteDevice()
    
    # Find printed registration marks indicating a 200x100 mm area
    d.zero_on_registration_mark(200, 100)
    
    # Set plotting parameters
    d.set_speed(d.params.tool_speed_min)
    d.set_force(d.params.tool_force_max)
    d.set_tool_diameter(d.params.tool_diameters["Pen"])
    
    # Move to (10, 10) mm as a starting point without drawing
    d.move_to(10, 10, False)
    
    # Draw the rectangle
    d.move_to(30, 10, True)
    d.move_to(30, 20, True)
    d.move_to(10, 20, True)
    d.move_to(10, 10, True)
    
    # Finish plotting and return to the home position
    d.move_home()
    
    # Flush the command buffer and wait for all commands to be acknowledged
    d.flush()

Documentation
-------------

[Fairly detailed API documentation can be found in
ReadTheDocs](http://py_silhouette.rtfd.org/) or built from scratch using sphinx:

    $ pip install -r requirements-docs.txt
    $ cd docs/
    $ make html

Disclaimer
----------

This software is based on my reverse engineering of the USB protocol used by
this device and so may or may not work well or be good for the device.

I'm also developing this for my own personal use. As such that means I'm
prioritising features which matter to me (correctness, predictability,
reliability) and not those which might matter to others (ease of use, features
I don't happen to care about). I'd be delighted if you wish to use this
software or even contribute but I'd work on the principle that if you want to
use this long term you might have to maintain your own fork!
