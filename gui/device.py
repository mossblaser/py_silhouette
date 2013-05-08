#!/usr/bin/env python

import gtk

from plotter.device import MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT
from plotter.device import RegistrationMarkNotFoundError

from plotter.device.silhouette import Portrait

import plotter.design.filter
import plotter.design.util

from background import RunInBackground


class DeviceMixin(object):
	"""
	Logic for driving device-specific elements.
	"""
	
	def __init__(self):
		# The device currently being used
		self.cur_device = None
		
		# The boilerplate for the list of devices to display in the GUI
		self.device_list_store = gtk.ListStore(str,object)
		
		cell = gtk.CellRendererText()
		self.device_combo = self.glade.get_widget("deviceComboBox")
		self.device_combo.pack_start(cell, True)
		self.device_combo.add_attribute(cell, 'text', 0)
		self.device_combo.set_model(self.device_list_store)
		
		# The boilerplate for the list of tools to display in the GUI
		self.tool_list_store = gtk.ListStore(str,object)
		
		cell = gtk.CellRendererText()
		self.tool_combo = self.glade.get_widget("toolComboBox")
		self.tool_combo.pack_start(cell, True)
		self.tool_combo.add_attribute(cell, 'text', 0)
		self.tool_combo.set_model(self.tool_list_store)
		
		# Boilerplate for sliders
		self.speed_adjustment = self.glade.get_widget("cuttingSpeedHScale").get_adjustment()
		self.force_adjustment = self.glade.get_widget("cuttingForceHScale").get_adjustment()
		
		# Fill up the combos
		self.refresh_device_list()
	
	
	def refresh_device_list(self):
		"""
		Update the list of devices.
		"""
		
		if self.cur_device is not None:
			self.cur_device.close()
			self.cur_device = None
		
		self.device_list_store.clear()
		
		# List of plotter.device.Device classes to look for
		devices = [
			Portrait
		]
		
		for Device in devices:
			d = Device()
			for dev_num in range(d.is_available()):
				try:
					# Try connecting to the device and getting its name
					d.open(dev_num)
					name = d.get_name()
					d.close()
					
					# Add the device and number to the list
					self.device_list_store.append((name, (d, dev_num)))
				except Exception, e:
					print "Couldn't get name for '%s' (%d): %s"%(
						d.__class__.__name__, dev_num, repr(e)
					)
		
		# Selet the first driver (if available)
		if len(self.device_list_store):
			self.device_combo.set_active(0)
	
	
	def refresh_tool_list(self):
		self.tool_list_store.clear()
		
		if self.cur_device is not None:
			for name in sorted(self.cur_device.get_tools().iterkeys()):
				tool = self.cur_device.get_tools()[name]
				self.tool_list_store.append((name, tool))
		
		if len(self.tool_list_store):
			self.tool_combo.set_active(0)
	
	
	def refresh_speed(self):
		lower, upper = self.cur_device.get_speed_range()
		self.speed_adjustment.set_lower(lower)
		self.speed_adjustment.set_upper(upper)
		self.speed_adjustment.set_value(self.speed_adjustment.get_value())
	
	
	def refresh_force(self):
		lower, upper = self.cur_device.get_force_range()
		self.force_adjustment.set_lower(lower)
		self.force_adjustment.set_upper(upper)
		self.force_adjustment.set_value(self.force_adjustment.get_value())
	
	
	def on_deviceComboBox_changed(self, widget):
		# Disconnect old device
		if self.cur_device is not None:
			self.cur_device.close()
			self.cur_device = None
		
		if widget.get_active() == -1:
			return
		
		name, (dev, num) = self.device_list_store[widget.get_active()]
		
		# Connect to new device
		dev.open(num)
		self.cur_device = dev

		self.refresh_speed()
		self.refresh_force()
		self.refresh_tool_list()
	
	
	def on_refreshDevicesButton_clicked(self, widget):
		self.refresh_device_list()
	
	
	def start_move(self, direction):
		if self.cur_device is not None:
			self.cur_device.move_continuous_start(direction)
	
	
	def stop_move(self, direction):
		if self.cur_device is not None:
			self.cur_device.move_continuous_stop()
	
	
	def on_moveUpButton_pressed(self, widget):  self.start_move(MOVE_UP)
	def on_moveUpButton_released(self, widget): self.stop_move( MOVE_UP)
	
	def on_moveDownButton_pressed(self, widget):  self.start_move(MOVE_DOWN)
	def on_moveDownButton_released(self, widget): self.stop_move( MOVE_DOWN)
	
	def on_moveLeftButton_pressed(self, widget):  self.start_move(MOVE_LEFT)
	def on_moveLeftButton_released(self, widget): self.stop_move( MOVE_LEFT)
	
	def on_moveRightButton_pressed(self, widget):  self.start_move(MOVE_RIGHT)
	def on_moveRightButton_released(self, widget): self.stop_move( MOVE_RIGHT)
	
	@RunInBackground(start_in_gtk = True)
	def on_cutButton_clicked(self, widget):
		"""
		Start cutting the design
		"""
		if self.cur_device is None:
			return
		
		# Get parameters
		use_reg_marks = self.use_reg_marks_check_button.get_active()
		
		reg_mark_left   = self.reg_mark_left_spin_button.get_value()
		reg_mark_top    = self.reg_mark_top_spin_button.get_value()
		reg_mark_width  = self.reg_mark_width_spin_button.get_value()
		reg_mark_height = self.reg_mark_height_spin_button.get_value()
		
		num_recalibrations = int(self.recalibrate_count_spin_button.get_value())
		
		if self.tool_combo.get_active() != -1:
			tool = self.tool_list_store[self.tool_combo.get_active()][1]
		else:
			tool = None
		
		speed = self.speed_adjustment.get_value()
		force = self.force_adjustment.get_value()
		
		# Show the busy dialog
		self.busy_start()
		
		yield
		# Cut in the BG thread
		
		error = None
		
		try:
			# Set up cutting params
			if tool is not None:
				self.cur_device.set_tool(tool)
			
			self.cur_device.set_speed(speed)
			self.cur_device.set_force(force)
			
			# Get the design
			design = self.design_pipeline.get_value()
			
			if use_reg_marks:
				# Shift the design according to the registration marks
				design = plotter.design.filter.offset(design, (reg_mark_left, reg_mark_top))
				
				self.cur_device.zero_on_registration_mark(reg_mark_width, reg_mark_height)
			else:
				self.cur_device.zero_on_home()
			
			# Split design into individual batches of paths to cut (if required)
			design_segments = []
			if num_recalibrations > 0 and use_reg_marks:
				paths = plotter.design.util.to_paths(design)
				seg_len = len(paths) / (num_recalibrations+1)
				for segment in (paths[seg_len*i:seg_len*(i+1)]
				                for i in range(num_recalibrations+1)):
					design_segments.append(sum(segment, []))
			else:
				design_segments = [design]
			
			# Cut each batch
			for seg_num, segment in enumerate(design_segments):
				# Recalibrate before each segment of paths (except the first)
				if seg_num != 0:
					self.cur_device.zero_on_registration_mark(reg_mark_width, reg_mark_height)
				
				self.cur_device.move_home()
				cur_pos = (0,0)
				
				# Cut the design
				for start, end in segment:
					if cur_pos != start:
						self.cur_device.move_to(start[0], start[1], False)
					self.cur_device.move_to(end[0], end[1], True)
					cur_pos = end
			
			self.cur_device.move_home()
			
			# Make sure everything is sent
			self.cur_device.flush()
		except RegistrationMarkNotFoundError, e:
			print "Error during cut: ", e
			error = "Could not find registration marks."
		
		yield
		
		self.busy_end()
		
		if error is not None:
			d = gtk.MessageDialog( parent  = self.window
			                     , flags   = gtk.DIALOG_DESTROY_WITH_PARENT
			                     , type    = gtk.MESSAGE_ERROR
			                     , buttons = gtk.BUTTONS_CLOSE
			                     , message_format = error
			                     )
			d.run()
			d.destroy()
		
		
