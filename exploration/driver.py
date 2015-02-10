#!/usr/bin/python

import usb.core
import usb.util

dev = usb.core.find(idVendor=0x0b4d, idProduct=0x1123)

interface = dev[0][(0,0)]

if dev.is_kernel_driver_active(interface.bInterfaceNumber):
	dev.detach_kernel_driver(interface.bInterfaceNumber)

dev.reset()

# Set default configuration to the 1st one
dev.set_configuration(1)

# Claim control interface
usb.util.claim_interface(dev, interface)

# XXX Set alternative interface (Does nothing, here for now...)
dev.set_interface_altsetting(interface, 0)

# endpointSend = interface[0x00]
# endpointRecv = interface[0x82]

ep_send = usb.util.find_descriptor(interface, bEndpointAddress=0x01)
ep_recv = usb.util.find_descriptor(interface, bEndpointAddress=0x82)

print ep_send.write("FG\x03")
print "".join(map(chr, ep_recv.read(100)))

def register():
	reg_line_length = 10
	reg_line_thickness = 10
	registered_area_width = 180
	registered_area_height = 260
	# Speed
	print ep_send.write("!10,0\x03")
	#print ep_send.write("FN0\x03")
	# Set home to where we end up
	print ep_send.write("TB99\x03") #
	print ep_send.write("TB51,%d\x03"%(reg_line_length*20))
	print ep_send.write("TB52,2\x03") # Fails without
	print ep_send.write("TB53,%d\x03"%(reg_line_thickness*20))
	print ep_send.write("TB54,0,0\x03")
	print ep_send.write("TB55,1\x03")#
	print ep_send.write("TB123,%d,%d,117,75\x03"%(registered_area_height*20
	                                             ,registered_area_width*20))
	
	response = "".join(map(chr, ep_recv.read(100, 0)))
	print repr(response)
	assert(response == "    0\x03")
	


def ____write(val):
	return ep_send.write(val)
def stepwrite(val):
	raw_input("Press to send: " + repr(val))
	return ep_send.write(val)

def plot():
	#print ____write("FN0\x03") # Rezero at hardware home
	#print ____write("TB99\x03") # Unknown...
	# Force
	print ____write("FX15,0\x03")
	#print ____write("FY1\x03\x03")
	#print ____write("FU5100,4000\x03")
	# Speed
	print ____write("!10,0\x03")
	# Cutter (not pen)
	print ____write("FC18\x03")
	#print ____write("FM1\x03")
	#print ____write("TB50,0\x03")
	#print ____write("FO5622,3840\x03")
	#print ____write("\\0,0\x03")
	# Calibrated area size
	print ____write("Z5200,3600\x03")
	#print ____write("L0\x03")
	
	# Move to y,x
	print ____write("M0,0\x03")
	print stepwrite("D0,3600\x03")
	print stepwrite("D5200,0\x03")
	print stepwrite("D0,0\x03")
	
	#print stepwrite("M%d,%d\x03"%(166.91*20, (180 - 62.96)*20))
	#print stepwrite("D%d,%d\x03"%(170.96*20, (180 - 58.89)*20))
	#print stepwrite("D%d,%d\x03"%(175.03*20, (180 - 62.96)*20))
	#print stepwrite("D%d,%d\x03"%(166.91*20, (180 - 62.96)*20))
	
	#print ____write("&1,1,1\x03")
	#print ____write("TB50,0\x03")
	#print ____write("FO0\x03")
	# Return to home
	print ____write("H\x03\x03")

register()
raw_input()
plot()
raw_input()
plot()

#ep_send.write("!10,0\x03")
#ep_send.write("\x1b\x00\x04")
#import time
#time.sleep(3)
#ep_send.write("\x1b\x00\x00")
