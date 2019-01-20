.. py:module:: py_silhouette

``py_silhouette``: Control Silhouette plotters/cutters from Python
==================================================================

.. _Silhouette: https://www.silhouetteamerica.com/

``py_silhouette`` is a Python library for controlling the Silhouette_ series of
desktop plotters/cutters.

This library is intended to serve two purposes:

* It is intended to form the basis of both general and special purpose plotting
  software.
* To document the outcome of a reverse engineering effort for the protocol used
  to control Silhouette plotters.

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


Quick-and-dirty example
-----------------------

The following complete example illustrates how this library could be used to
draw a simple 20mm x 10mm rectangle::

    from py_silhouette import SilhouetteDevice
    
    # Connect to first available device
    d = SilhouetteDevice()
    
    # Move to (10, 10) mm as a starting point without drawing
    d.move_to(10, 10, False)
    
    # Draw the rectangle
    d.move_to(30, 10, True)
    d.move_to(30, 20, True)
    d.move_to(10, 20, True)
    d.move_to(10, 10, True)
    
    # Finish plotting and return to the home position (don't forget this!)
    d.move_home()
    
    # Flush the command buffer and wait for all commands to be acknowledged
    # (nothing will happen until this is called)
    d.flush()

A better example
----------------

The minimal example above will work but has numerous shortcomings.
Specifically:

* If multiple devices are connected, one will be chosen arbitrarily.
* Printed registration marks will be ignored.
* The speed and force applied by the device is undefined.
* If using a cutting tool, corners will not be cut correctly.

To improve this example we should first present the user with a choice of
devices by using :py:func:`enumerate_devices` to discover what is available::

    from py_silhouette import SilhouetteDevice, enumerate_devices
    
    devices = list(enumerate_devices())
    for num, (usb_device, device_params) in enumerate(devices):
        print("{}: {}".format(num, device_params.name))
    
    num = int(input("Choose a device number to use: "))
    usb_device, device_params = devices[num]
    
    d = SilhouetteDevice(usb_device, device_params)

Next we can use :py:meth:`SilhouetteDevice.zero_on_registration_mark` to zero
the device's coordinate system on a set of printed registration marks (which
we'll assume in this example mark a 200x100mm area)::


    from py_silhouette import RegistrationMarkNotFoundError
    
    try:
        d.zero_on_registration_mark(200, 100)
    except RegistrationMarkNotFoundError:
        print("Registration marks not found! Continuing without...")

Next, we can inform the device of the tool's diameter which will ensure corners
will be cut out correctly using :py:meth:`SilhouetteDevice.set_tool_diameter`
and tool information in :py:attr:`SilhouetteDevice.params`\
:py:class:`.tool_diameters <DeviceParameters.tool_diameters>`::

    d.set_tool_diameter(d.params.tool_diameters["Knife"])

Next we'll choose what speed and force we wish to use, again choosing
parameters based on the :py:class:`DeviceParameters` object in
:py:attr:`DeviceParameters.params`::

    d.set_speed(d.params.tool_speed_min)
    d.set_force(d.params.tool_force_max)

Now we're ready to cut out the rectangle::

    d.move_to(10, 10, False)
    
    d.move_to(30, 10, True)
    d.move_to(30, 20, True)
    d.move_to(10, 20, True)
    d.move_to(10, 10, True)
    
    d.move_home()
    
    d.flush()

The :py:meth:`SilhouetteDevice.flush` method will block untli all commands have
been received into the plotters buffer and so will probably return before
plotting has actually completed. We can use
:py:meth:`SilhouetteDevice.get_state` to wait until the plotter has actually
finished plotting (i.e. is nolonger in the :py:attr:`DeviceState.moving`
state)::

    import time
    from py_silhouette import DeviceState
    
    while d.get_state() == DeviceState.moving:
        time.sleep(0.5)
    
    print("Cutting complete!")


API
---

The complete API is contained within the ``py_silhouette`` module.  The
principal class, :py:class:`SilhouetteDevice`, represents a connection to a
plotter connected via USB and provides a number of low-level methods for
controling the device (e.g. :py:meth:`SilhouetteDevice.move_to`). A number of
supporting functions and data structures are defined which descover or describe
available devices and may be used to construct or configure a
:py:class:`SilhouetteDevice` (e.g. :py:func:`enumerate_devices`).

Device Discovery & Connection
`````````````````````````````

To construct a :py:class:`SilhouetteDevice` we must first discover a connected
device for it to control using :py:func:`enumerate_devices`:

.. autofunction:: py_silhouette.enumerate_devices(supported_device_parameters=SUPPORTED_DEVICE_PARAMETERS)

At this point you may wish to present your users with a prompt to select a
plotter (perhaps using :py:attr:`DeviceParameters.name` as a hint) or select
one automatically according to your own logic (perhaps using
:py:attr:`DeviceParameters.area_width_min` and friends to make an informed
choice).

Once a specific device has been chosen, pass the USB device and
:py:class:`DeviceParameters` object to the :py:class:`SilhouetteDevice`
constructor:

.. autoclass:: SilhouetteDevice

The :py:class:`DeviceParameters` used to configure the device can be obtained
from:

.. autoattribute:: SilhouetteDevice.params

For diagnostic purposes you can request the device name and state:

.. automethod:: SilhouetteDevice.get_name

.. automethod:: SilhouetteDevice.get_state

.. autoclass:: DeviceState
    :members:

Once you've finished using a device, you should close the connection using:

.. automethod:: SilhouetteDevice.close


Setting the plotter origin
``````````````````````````

Before beginning a plot it is important to decide how the coordinate axis is
zeroed. This library presents you with two options:

* Do nothing and the device's 'home' position will be the origin for plotting
  coordinates.
* Use :py:meth:`SilhouetteDevice.zero_on_registration_mark` to zero the
  plotting axes on registration marks printed on the page.

.. automethod:: SilhouetteDevice.zero_on_registration_mark


Setting tool parameters
```````````````````````

Prior to plotting it is important to set the plotting speed, force and tool
parameters according to the tool and material in use. There are no
hard-and-fast rules for setting these parameters so experimentation is
required.

.. automethod:: SilhouetteDevice.set_speed

.. automethod:: SilhouetteDevice.set_force


Depending on the type of tool used, the device will automatically tweak the
toolpath supplied to compensate for the tool diameter. For this function to
work correctly, the diameter of the tool must also be supplied.

.. automethod:: SilhouetteDevice.set_tool_diameter


Plotting
````````

Plotting is performed by making a series of :py:meth:`SilhouetteDevice.move_to`
calls followed by :py:meth:`SilhouetteDevice.move_home` and
:py:meth:`SilhouetteDevice.flush`\ .

.. automethod:: SilhouetteDevice.move_to

.. automethod:: SilhouetteDevice.move_home

.. automethod:: SilhouetteDevice.flush


Device Parameters and Tools
```````````````````````````

Device parameters for widely used Silhouette devices are included in:

.. data:: SUPPORTED_DEVICE_PARAMETERS

    A list of :py:class:`DeviceParameters` describing a particular supported
    device. At the time of writing, only support for the Silhouette Potrait v1
    has been verified.

For each supported device type, information defining its USB interface
identifiers, plotter dimensions and out-of-the-box tool support is included.

.. autoclass:: DeviceParameters
    :members:


Exceptions
``````````

The following exceptions may be thrown by this library.

.. autoexception:: DeviceError

.. autoexception:: NoDeviceFoundError

.. autoexception:: RegistrationMarkNotFoundError


Origins and Acknowledgements
````````````````````````````

This software is primarily based on my own reverse engineering efforts
targeting the Silhouette Portrait USB protocol based on observing the behaviour
of the Silhouette Studio software running under Windows back in 2013. This
first reverse-engineering pass uncovered an easy to use and understand subset
of the Silhouette control protocol allowing the device to be satisfactorily
used under Linux and other platforms.

Later, I discovered others' efforts to reverse engineer and drive the
Silhouette series of plotters (in particular Robocut_ and later
Inkscape-Silhouette_). Based hints in these other codebases I managed to
document the remaining 'unknowns' within my minimal subset of the USB protocol
used by Silhouette Studio.

.. _Robocut: https://github.com/nosliwneb/robocut
.. _Inkscape-Silhouette: https://github.com/fablabnbg/inkscape-silhouette
