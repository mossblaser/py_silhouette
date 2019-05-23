"""
A low-level driver for controling the Silhouette family of desktop
plotters and cuters.
"""

import enum
from attr import attrs, attrib

import usb.core
import usb.util


__names__ = [
    "DeviceState",
    "DeviceError",
    "NoDeviceFoundError",
    "RegistrationMarkNotFoundError",
    "DeviceParameters",
    "SUPPORTED_DEVICE_PARAMETERS",
    "enumerate_devices",
    "SilhouetteDevice",
]


"""The USB endpoint addresses used by the device."""
USB_ENDPOINT_CMD_SEND = 0x01
USB_ENDPOINT_CMD_RECV = 0x82


def clamp(value, low, high):
    """Clamp value to be at least low and at most high."""
    return min(max(value, low), high)


def inch2mm(inches):
    """Convert inches to millimetres."""
    return inches * 25.4


def mm2mu(mm):
    """Convert from millimetres to machine units."""
    return int(mm * 20)


def grams2mu(grams):
    """Convert a force in grams (yes, I know...) into machine units."""
    return int((grams / 7.0) + 0.5)


def mmsec2mu(mmsec):
    """Convert a speed in mm/second into machine units."""
    return mmsec/100.0


class DeviceState(enum.Enum):
    """
    What is the device currently doing?
    """
    
    ready = b"0"
    """The device is ready to begin plotting."""
    
    moving = b"1"
    """The plotter is busy plotting or moving."""
    
    unloaded = b"2"
    """Idle with no media loaded."""
    
    paused = b"3"
    """The pause button has been pressed."""
    
    unknown = None
    """Unrecognised device state; probably an error."""


class DeviceError(Exception):
    """Baseclass for all py_silhouette hardware related errors."""


class NoDeviceFoundError(DeviceError):
    """No connected devices were found."""


class RegistrationMarkNotFoundError(DeviceError):
    """The registration mark could not be found."""


@attrs(frozen=True)
class DeviceParameters(object):
    """
    A collection of parameters which define the unique hardware characteristics
    of a particular device.
    """
    
    product_name = attrib()
    """Human readable product name for the device supported by this class."""
    
    usb_vendor_id = attrib()
    """The USB Vendor ID used by device."""
    
    usb_product_id = attrib()
    """The USB Product ID used by device."""
    
    area_width_min = attrib()
    """Minimum width for valid plot areas (mm)"""
    
    area_width_max = attrib()
    """Maximum width for valid plot areas (mm)"""
    
    area_height_min = attrib()
    """Minimum height for valid plot areas (mm)"""
    
    area_height_max = attrib()
    """Maximum height for valid plot areas (mm)"""
    
    tool_diameters = attrib(factory=lambda: {
        "Pen": 0.0,
        "Knife": 0.9,
    })
    """
    A dictionary mapping from tool name to tool diameter (in mm) for all tools
    which ship with or are available for this device for use with
    :py:meth:`SilhouetteDevice.set_tool_diameter`. Generally ``'Pen'`` and
    ``'Knife'`` tools will be defined.
    """
    
    tool_force_min = attrib(default=7.0)
    """Lowest force which may be applied by the machine (in grams)"""
    
    tool_force_max = attrib(default=231.0)
    """Highest force which may be applied by the machine (in grams)"""
    
    tool_speed_min = attrib(default=100.0)
    """Lowest speed at which the machine can move (mm/sec)"""
    
    tool_speed_max = attrib(default=1000.0)
    """Highest speed at which the machine can move (mm/sec)"""
    
    tool_diameter_min = attrib(default=0.0)
    """Lowest valid tool diameter (mm)"""
    
    tool_diameter_max = attrib(default=2.3)
    """Highest valid tool diameter (mm)"""


"""
The parameters for the supported devices.
"""
SUPPORTED_DEVICE_PARAMETERS = [
    DeviceParameters(
        "Silhouette Portrait",
        usb_vendor_id=0x0B4D,
        usb_product_id=0x1123,
        area_width_min=inch2mm(3.0),
        area_width_max=inch2mm(8.5),
        area_height_min=inch2mm(3.0),
        area_height_max=inch2mm(40.0),
    ),
    # Warning: values for entries below taken from
    # https://github.com/fablabnbg/inkscape-silhouette and have not been
    # tested or validated in any way!
    DeviceParameters(
        "Silhouette Portrait2",
        usb_vendor_id=0x0B4D,
        usb_product_id=0x1132,
        area_width_min=inch2mm(3.0),
        area_width_max=inch2mm(8.0),
        area_height_min=inch2mm(3.0),
        area_height_max=inch2mm(40.0),
    ),
    DeviceParameters(
        "Silhouette Cameo",
        usb_vendor_id=0x0B4D,
        usb_product_id=0x1121,
        area_width_min=inch2mm(3.0),
        area_width_max=inch2mm(12.0),
        area_height_min=inch2mm(3.0),
        area_height_max=inch2mm(40.0),
    ),
    DeviceParameters(
        "Silhouette Cameo2",
        usb_vendor_id=0x0B4D,
        usb_product_id=0x112B,
        area_width_min=inch2mm(3.0),
        area_width_max=inch2mm(12.0),
        area_height_min=inch2mm(3.0),
        area_height_max=inch2mm(40.0),
    ),
    DeviceParameters(
        "Silhouette Cameo2",
        usb_vendor_id=0x0B4D,
        usb_product_id=0x112F,
        area_width_min=inch2mm(3.0),
        area_width_max=inch2mm(12.0),
        area_height_min=inch2mm(3.0),
        area_height_max=inch2mm(40.0),
    ),
]


def enumerate_devices(supported_device_parameters=SUPPORTED_DEVICE_PARAMETERS):
    """
    Generator which produces a series of ``(device, device_params)`` pairs for
    all currently connected devices.
    
    Parameters
    ----------
    supported_device_parameters : [:py:class:`DeviceParameters`, ...]
        An optional list of :py:class:`DeviceParameters` objects for the types
        of devices to include in the enumeration. By default this is all of the
        devices enumerated in :py:data:`SUPPORTED_DEVICE_PARAMETERS`.
    """
    vid_pid_to_device_parameters = {
        (p.usb_vendor_id, p.usb_product_id) : p
        for p in supported_device_parameters
    }
    
    for device in usb.core.find(find_all=True):
        device_params = vid_pid_to_device_parameters.get(
            (device.idVendor, device.idProduct))
        if device_params is not None:
            yield (device, device_params)


class SilhouetteDevice(object):
    """
    A generic abstract base implementation which includes the common parts of
    the driver. This class provides low-level control over a plotting device.
    """
    
    params = None
    """
    The :py:class:`DeviceParameters` object passed during construction (or
    selected automatically). Contains useful information about the shape and
    size of media and tools supported by this device.
    """
    
    def __init__(self, device=None, device_params=None):
        """
        Connect to and control the specified plotter/cutter.
        
        See :py:func:`enumerate_devices` for discovering connected devices and
        their parameters.
        
        As a convenience, if no arguments are provided, this class will attempt
        to connect to the first device found by :py:func:`enumerate_devices`,
        throwing a :py:exc:`NoDeviceFoundError` if no devices are found.
        
        Parameters
        ----------
        device : :py:class:`pyusb.core.Device`
            The USB device object for the plotter to control.
        device_params : :py:class:`DeviceParameters`
            Definition of the device's key parameters.
        """
        # Discover and use the first device discovered if none is provided.
        if device is None and device_params is None:
            try:
                device, device_params = next(enumerate_devices())
            except StopIteration:
                raise NoDeviceFoundError()
        
        self.params = device_params
        
        # A buffer into which commands waiting to be sent will be written until
        # flush() is called.
        self._send_buffer = b""
        
        # Get the USB interface to use
        config = device[0]
        interface = config[(0, 0)]
        
        # Detatch kernel drivers already using the interface
        if device.is_kernel_driver_active(interface.bInterfaceNumber):
            device.detach_kernel_driver(interface.bInterfaceNumber)
        
        device.reset()
        
        device.set_configuration(1)
        
        usb.util.claim_interface(device, interface)
        
        # Get endpoint descriptors
        self._usb_send_ep = usb.util.find_descriptor(
            interface,
            bEndpointAddress=USB_ENDPOINT_CMD_SEND,
        )
        self._usb_recv_ep = usb.util.find_descriptor(
            interface,
            bEndpointAddress=USB_ENDPOINT_CMD_RECV,
        )
        
        # Sanity check intialisation was successful. Also, requesting the name
        # (or (probably) sending any command) completes initialisation.
        assert len(self.get_name()) > 3
    
    def _send(self, data):
        """
        Queue up a series of bytes to send to the device. Follow with a call to
        flush()
        """
        self._send_buffer += data
    
    def _receive(self, size=64, timeout=0):
        """
        Receive some data from the device. Returns a bytestring.
        """
        data_array = self._usb_recv_ep.read(size, timeout)
        # NB: This method has been renamed to tobytes() in Python 3x. The
        # deprecated method name is used for compatibility with both Python
        # versions.
        return data_array.tostring()
    
    def flush(self):
        """
        Ensure all outstanding commands have been sent. Blocks until complete.
        """
        while self._send_buffer:
            written = self._usb_send_ep.write(self._send_buffer)
            self._send_buffer = self._send_buffer[written:]
    
    def get_name(self):
        """
        Return the human-readable name and version reported by the device (as a
        string).
        """
        self._send(b"FG\x03")
        self.flush()
        return self._receive().rstrip(b" \x03").decode("utf-8")
    
    def get_state(self):
        """
        Get the current state of the device returning a
        :py:class:`DeviceState`.
        """
        self._send(b"\x1b\x05")
        self.flush()
        value = self._receive()
        try:
            return DeviceState(value[:1])
        except ValueError:
            print(value)
            return DeviceState.unknown
    
    def move_home(self):
        """
        Move the carriage to the home position (or to the top-left registration
        mark if zeroed) with the tool disengaged.
        
        The plotter expects this to be the final command received at the end of
        a sequence of :py:meth:`move_to` calls.
        
        .. note::
            
            If this command is not used at the end of a series of
            :py:meth:`move_to` calls, the final command sent will be delayed
            for a short while since the device likes to always have a
            look-ahead of at least one command (probably to support tool
            diameter compensation -- see :py:meth:`set_tool_diameter`).
        
        Call :py:meth:`flush` to ensure this command has arrived at the device.
        """
        self._send(b"H\x03")
    
    
    def move_to(self, x, y, use_tool):
        """
        Move the plotter, optionally with the tool engaged.
        
        Facing the plotter, the X axis runs from left to right with strictly
        positive coordinates. The Y axis runs from top to bottom with strictly
        positive coordinates.
        
        Call :py:meth:`flush` to ensure this command has arrived at the device.
        
        After completing a sequence of move_to commands, always use
        :py:meth:`move_home` to return the plotter to the home position and
        notify the device that plotting has finished.
        
        Parameters
        ----------
        x, y: float
            Absolute page position in mm.
            
            These values will be clamped between 0 and the  maximum page width
            and height however this may not always be enough to prevent the
            machine hitting the end of the carrage (e.g. when zeroed on a
            registration mark). It is the caller's responsibility to sensibly
            clip the input to prevent crashes.
            
            If :py:meth:`zero_on_registration_mark` has been used since the
            last paper load, coordinates will be relative to the top-left
            corner of the registration mark and should not go beyond the width
            and height of the registered area. If
            :py:meth:`zero_on_registration_mark` has not been used, coordinates
            start from the device's home position.
        use_tool: bool
            If True, the tool will be applied during the movement. If False,
            the tool will be lifted.
        """
        self._send(b"%s%d,%d\x03"%(
            b"D" if use_tool else b"M",
            mm2mu(clamp(y, 0, self.params.area_height_max)),
            mm2mu(clamp(x, 0, self.params.area_width_max)),
        ))
    
    def set_tool_diameter(self, diameter):
        r"""
        Inform the plotter of the diameter of a swivelling tool's working
        point to allow it to adjust tool paths accordingly.
        
        Tool diameters for the standard tools supplied with the current device
        can be obtained from :py:attr:`SilhouetteDevice.params`\
        :py:attr:`.tool_diameters <DeviceParameters.tool_diameters>`.
        
        .. note::
        
            Cutting blade cartridges contain a blade on a swivelling
            attachment, a little like the casters on an office chair.
            
            .. image:: _static/tool_diameter.svg
                :alt: A story-board showing a corner being cut in four steps.
                      Step 1-2: The knife reaches the corner. Step 2-3: The
                      plotter moves the knife such that the point stays
                      stationary but is now pointing along the next edge. Step
                      3-4: The next edge is cut.
            
            As such, the point of the blade's position will lag behind the
            plotter's position. Setting this parameter causes the device's
            firmware to compensate for this automatically when turning corners
            by moving the plotter in an arc pattern towards the new line.
            During this move, the blade turns to face the new cut direction but
            does not actually cut.
            
            When using a tool with a swivelling cutting implement (such as the
            included knife cartridge), setting this parameter correctly is
            strongly recommended for good results. If using a fixed implement
            (e.g. a pen), this setting should usually be set to 0.0 since the
            pen tip is fixed.
        
        Parameters
        ----------
        diameter : float
            Tool swivel mounting diameter.
            
            This parameter will be automatically clamped to the range specified
            in the :py:class:`SilhouetteDevice.params`\
            :py:attr:`.tool_diameter_min
            <DeviceParameters.tool_diameter_min>` and  :py:class:`SilhouetteDevice.params`\
            :py:attr:`.tool_diameter_max
            <DeviceParameters.tool_diameter_max>`.
        """
        self._send(b"FC%d\x03"%(mm2mu(clamp(
            diameter,
            self.params.tool_diameter_min,
            self.params.tool_diameter_max,
        ))))
    
    def set_force(self, force):
        """
        Set the amount of force to be applied (in grams (yes.)) when the tool
        is used.
        
        This parameter will be automatically clamped to the range specified in
        the :py:class:`SilhouetteDevice.params`\ :py:attr:`.tool_force_min
        <DeviceParameters.tool_force_min>` and
        :py:class:`SilhouetteDevice.params`\ :py:attr:`.tool_force_max
        <DeviceParameters.tool_force_max>`.
        """
        self._send(b"FX%d,0\x03"%grams2mu(clamp(
            force,
            self.params.tool_force_min,
            self.params.tool_force_max,
        )))
    
    def set_speed(self, speed):
        """
        Set the movement speed of the device in mm/sec.
        
        This parameter will be automatically clamped to the range specified in
        the :py:class:`SilhouetteDevice.params`\ :py:attr:`.tool_speed_min
        <DeviceParameters.tool_speed_min>` and
        :py:class:`SilhouetteDevice.params`\ :py:attr:`.tool_speed_max
        <DeviceParameters.tool_speed_max>`.
        """
        self._send(b"!%d,0\x03"%mmsec2mu(clamp(
            speed,
            self.params.tool_speed_min,
            self.params.tool_speed_max,
        )))
    
    def zero_on_registration_mark(self, width, height,
                                  box_size=5.0,
                                  line_thickness=0.5, line_length=20.0,
                                  search=True):
        """
        Zero coordinate system and compensate for small page misalignments
        using registration marks printed on the page.
        
        If the registration marks are not found,
        :py:exc:`RegistrationMarkNotFoundError` is raised.
        
        This command will block until the registration marks have been found or
        not.
        
        The registration settings will be retained until the current page is
        ejected from the machine.
        
        .. warning::
            
            As a side effect of calling this command, the tool speed will be
            set to its maximum.
        
        .. note::
        
            Registration marks should look as follows (without the red
            construction/dimension lines...):
            
            .. image:: _static/regmarks.svg
                :alt: The registration marks consist of a 5x5mm square at the top
                      left of the page, a 20mm 'L' bracket at the bottom left and
                      corresponding bracket at the top right.
            
            * The registration marks must be oriented as shown and white space must
              be left around all three marks to ensure they are found by the
              plotter.
            
            * The entire path to be plotted/cut must be within the bounds of the
              registration marks.
            
            * The top-left mark should be near the top-left of the page so
              that the plotter can find.
            
            * The width and height are measured from the *outside* of the
              corner bracket lines.
            
            Most Silhouette plotters also support a second type of registration
            mark where the top-left square is replaced with another corner
            bracket. Use of this type of registration mark is not supported by
            this library.
        
        Parameters
        ----------
        width, height: float
            The size of the area the registration mark covers in mm.
            
            .. warning::
                
                Take care that the right-most registration mark is not too
                close to the right-hand extreme of the machine. The
                registration sensor is mounted at the very left side of the
                carriage so it will need to move further than it would when
                plotting on that corner of the page. The plotter does not have
                a 'right' end-stop and may hit the end of its axis.
        
        box_size : float
            The size of the black square in the top-left registration mark
            (mm). Currently must be set to 5mm (the default).
        line_thickness : float
            The thickness of the registration lines (mm). Default of 0.5 mm
            is known to work well.
        line_length : float
            The length the registration lines (mm). Default of 20 mm
            is known to work well.
        search : bool
            If true, the device will start searching for the registration mark
            automatically, starting at the device home position. If False the
            device should first be positioned with the tool over the black
            square. In practice this is very difficult to achieve so most users
            will want to leave this setting in its default mode (True).
        """
        if box_size != 5.0:
            raise NotImplementedError(
                "Registration mark box size must always be 5mm.")
        
        self.set_speed(self.params.tool_speed_max)
        
        # Set the zero position to the place we're about to home in on
        self._send(b"TB99\x03")
        
        # Set registration mark line thickness
        self._send(b"TB51,%d\x03"%mm2mu(line_thickness))
        
        # Use Silhouette Portrait-style regmarks (which look as described
        # above).
        self._send(b"TB52,2\x03")
        
        # Set registration mark line length
        self._send(b"TB53,%d\x03"%mm2mu(line_length))
        
        # The offset of the black square from the correct location
        self._send(b"TB54,0,0\x03")
        
        # Use registration marks to calibrate scale and rotation
        self._send(b"TB55,1\x03")#
        
        # Scan for registration marks
        self._send(b"TB%s23,%d,%d,117,75\x03"%(
            b"1" if search else b"",
            mm2mu(clamp(
                height,
                self.params.area_height_min,
                self.params.area_height_max,
            )),
            mm2mu(clamp(
                width,
                self.params.area_width_min,
                self.params.area_width_max,
            )),
        ))
        
        self.flush()
        
        # Wait for a response (this may take some time!)
        if self._receive() != b"    0\x03":
            raise RegistrationMarkNotFoundError()
