#!/usr/bin/env python

import math
import colorsys

from operator import sub, add

import gtk

from plotter.design      import get_loaders, load_file
from plotter.design.util import line_length

import plotter.design.sort
import plotter.design.filter

from background import RunInBackground


class LazyPipeline(object):
	"""
	A pipeline of functions to be applied to an input. Lazily re-evaluates as
	needed.
	"""
	
	def __init__(self, *stages):
		"""
		Takes a list of names of processing stage names.
		"""
		# The list of pipeline stages (adding an input stage)
		self.stages = ["__input__"] + list(stages)
		
		# A dict relating stage names to the function to use to process that stage.
		# If a function is None, the value of the element in that stage will not be
		# modified, even if the stages before it do. Default to the identity
		# function.
		self.stage_funcs = dict((stage, (lambda x:x)) for stage in self.stages)
		
		# The input function defaults to None, that is, it should only be changed by
		# set_value()
		self.stage_funcs["__input__"] = None
		
		# A dict relating stage names to the value at that stage. If the value is
		# None then it is invalid.
		self.stage_values = dict((stage, None) for stage in self.stages)
	
	
	def get_next_stage(self, stage):
		"""
		Raises an index error on unavailability of further stages.
		"""
		return self.stages[self.stages.index(stage)+1]
	
	
	def get_prev_stage(self, stage):
		"""
		Raises an index error on unavailability of further stages.
		"""
		stage_index = self.stages.index(stage) - 1
		if stage_index < 0:
			raise IndexError()
		return self.stages[stage_index]
	
	
	def invalidate_after(self, stage = None):
		"""
		Invalidate the stages after that named as argument (None = first stage) and
		all following stages.
		"""
		stage = stage or self.stages[0]
		
		try:
			next_stage = self.get_next_stage(stage)
		except IndexError:
			# No more stages to invalidate
			return
		
		# Invalidate the next pipeline stage, but only if it isn't a fixed value,
		# (i.e. the function isn't None)
		if self.stage_funcs[next_stage] is not None:
			self.stage_values[next_stage] = None
			self.invalidate_after(next_stage)
	
	
	def set_value(self, value, stage = None):
		"""
		Set the value in the pipeline, invalidating all elements afterwards. This is
		only allowed for stages with the function None, i.e. remain unchanged.
		"""
		stage = stage or self.stages[0]
		
		assert(self.stage_funcs[stage] is None)
		
		self.stage_values[stage] = value
		self.invalidate_after()
	
	
	def set_func(self, stage, func):
		"""
		Sets the function used to calculate a value for this stage.
		"""
		self.stage_funcs[stage] = func
		
		# If the function is not None (i.e. don't just leave the current value
		# unchanged at all times), invalidate this stage and all following stages.
		if func is not None:
			self.stage_values[stage] = None
			self.invalidate_after(stage)
	
	
	def is_valid(self, stage = None):
		"""
		Is the value at the given stage (or final stage if None) valid? If not there
		may be a delay while the value is calculated when get_value is used.
		"""
		stage = stage or self.stages[-1]
		return self.stage_values[stage] is not None
	
	
	def get_value(self, stage = None):
		"""
		Get the value of a given stage. If no stage is None, get the last stage's
		value (i.e. the output).
		"""
		stage = stage or self.stages[-1]
		
		# If the value has been invalidated, look it up
		if self.stage_values[stage] is None:
			func = self.stage_funcs[stage]
			if func is not None:
				self.stage_values[stage] = func(self.get_value(self.get_prev_stage(stage)))
		
		return self.stage_values[stage]



class DesignMixin(object):
	"""
	Logic for designs in the UI.
	"""
	
	VIEW_DEFAULT_MARGIN = 10.0
	
	PX_PER_MM = 3.5433071
	
	MENU_ZOOM_INCREMENT = 0.5
	MOUSE_ZOOM_INCREMENT = 0.5
	
	def __init__(self):
		self.design_drawing_area = self.glade.get_widget("designDrawingArea")
		
		# Get refs to ordering radio buttons
		self.order_original_radio_button  = self.glade.get_widget("orderOriginalRadioButton")
		self.order_optimised_radio_button = self.glade.get_widget("orderOptimisedRadioButton")
		self.order_inner_radio_button     = self.glade.get_widget("orderInnerRadioButton")
		self.order_custom_radio_button    = self.glade.get_widget("orderCustomRadioButton")
		
		# Ref for extract regmarks check
		self.extract_reg_check_button = self.glade.get_widget("extractRegCheckButton")
		self.use_reg_marks_check_button = self.glade.get_widget("useRegMarksCheckButton")
		
		# Ref for regmark settings spinboxes
		self.reg_mark_left_spin_button   = self.glade.get_widget("regMarkLeftSpinButton")
		self.reg_mark_top_spin_button    = self.glade.get_widget("regMarkTopSpinButton")
		self.reg_mark_width_spin_button  = self.glade.get_widget("regMarkWidthSpinButton")
		self.reg_mark_height_spin_button = self.glade.get_widget("regMarkHeightSpinButton")
		
		# Ref for overcut spin-button
		self.over_cut_spin_button = self.glade.get_widget("overCutSpinButton")
		
		self.recalibrate_count_spin_button = self.glade.get_widget("recalibrateCountSpinButton")
		
		self.design_filename = None
		
		# The processing pipeline for the design
		self.design_pipeline = LazyPipeline( "regmark_extraction"
		                                   , "sort"
		                                   , "overcut"
		                                   )
		
		self.design_pipeline.set_value([])
		self.design_width  = 0.0
		self.design_height = 0.0
		
		# Viewer properties
		self.view_zoom      = DesignMixin.PX_PER_MM
		self.view_translate = (0.0, 0.0)
		
		# Drag support
		self.mouse_pos = None
		
		# Set-up pipeline stages
		self.set_regmark_extraction_pipeline()
		self.set_sort_pipeline()
		self.set_overcut_pipeline()
	
	
	@property
	def design(self):
		"""
		The design to be cut.
		"""
		return self.design_pipeline.get_value()
	
	
	def on_openMenuItem_activate(self, widget):
		dlg = gtk.FileChooserDialog( title="Open Design"
		                           , parent=self.window
		                           , action=gtk.FILE_CHOOSER_ACTION_OPEN
		                           , buttons=( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL
		                                     , gtk.STOCK_OPEN,   gtk.RESPONSE_OK
		                                     )
		                           )
		dlg.set_default_response(gtk.RESPONSE_OK)
		
		all_supported_files_filter = gtk.FileFilter()
		all_supported_files_filter.set_name("All Supported Files")
		dlg.add_filter(all_supported_files_filter)
		
		# Set filename filters
		for loader, extension, human_name in get_loaders():
			all_supported_files_filter.add_pattern("*%s"%extension)
			
			file_filter = gtk.FileFilter()
			file_filter.set_name("%s (*%s)"%(human_name, extension))
			file_filter.add_pattern("*%s"%extension)
			dlg.add_filter(file_filter)
		
		all_files_filter = gtk.FileFilter()
		all_files_filter.set_name("All Files")
		all_files_filter.add_pattern("*")
		dlg.add_filter(all_files_filter)
		
		# Set default file as previous file
		if self.design_filename is not None:
			dlg.set_filename(self.design_filename)
		
		# Show it
		response = dlg.run()
		self.design_filename = dlg.get_filename()
		dlg.destroy()
		
		if response != gtk.RESPONSE_OK:
			return
		
		self.on_refreshMenuItem_activate(None)
	
	
	def on_refreshMenuItem_activate(self, widget):
		if self.design_filename is None:
			return
		
		try:
			(self.design_width, self.design_height), raw_design \
				= load_file(self.design_filename)
			
			# Place the new value in the design pipeline
			self.design_pipeline.set_value(raw_design)
			
			# Try and enable regmark detection if regmarks are enabled
			self.extract_reg_check_button.set_active(True)
			
			# TODO: Ensure that custom ordering is not selected
			
			# Zoom to fit new file
			self.on_zoomFitMenuItem_activate()
			
			# Update the display
			self.redraw_design()
			
		except Exception, e:
			print "Error loading file:", e
			d = gtk.MessageDialog( parent  = self.window
			                     , flags   = gtk.DIALOG_DESTROY_WITH_PARENT
			                     , type    = gtk.MESSAGE_ERROR
			                     , buttons = gtk.BUTTONS_CLOSE
			                     , message_format = "Error loading file."
			                     )
			d.run()
			d.destroy()
	
	
	def redraw_design(self):
		# XXX: Work-around various attempts to call this when things are not
		# defined yet or have been unloaded.
		if not hasattr(self, "design_drawing_area") \
		   or self.design_drawing_area.window is None:
			return
		
		# Force re-render
		w,h = self.design_drawing_area.window.get_size()
		self.design_drawing_area.window.invalidate_rect((0,0,w,h), True)
	
	
	@RunInBackground(max_queue_length = None, start_in_gtk = True)
	def on_designDrawingArea_expose_event(self, widget, event):
		"""
		Draws the currently loaded design
		"""
		
		if not self.design_pipeline.is_valid():
			# Show the busy dialog GTK thread
			self.busy_start()
			yield
			# Get design outside GTK thread incase it takes time...
			design = self.design
			yield
			self.busy_end()
		else:
			design = self.design
		
		# Display the design
		w,h = widget.window.get_size()
		
		def t(x,y, scale_only = False):
			x = x*self.view_zoom
			y = y*self.view_zoom
			
			if not scale_only:
				center_x = (w/2) - ((self.design_width*self.view_zoom)/2)
				center_y = DesignMixin.VIEW_DEFAULT_MARGIN
				
				x += self.view_translate[0] + center_x
				y += self.view_translate[1] + center_y
			
			return (x,y)
		
		cr = widget.window.cairo_create()
		
		# Draw Page
		rect = list(t(0,0)) + list(t(self.design_width,self.design_height, scale_only=True))
		cr.rectangle(*rect)
		
		cr.set_source_rgb(1.0,1.0,1.0)
		cr.fill_preserve()
		
		cr.set_line_width(2)
		cr.set_source_rgb(0.0,0.0,0.0)
		cr.stroke()
		
		# Draw design
		cr.set_line_width(1)
		
		total_length = sum(map(line_length, design))
		cur_length   = 0.0
		
		for num, (line_start, line_end) in enumerate(design):
			perc = cur_length / total_length
			cur_length += line_length((line_start, line_end))
			
			cr.set_source_rgb(*colorsys.hsv_to_rgb(perc*0.7, 1.0, 1.0))
			cr.move_to(*t(*line_start))
			cr.line_to(*t(*line_end))
			cr.stroke()
	
	
	def on_designDrawingArea_button_press_event(self, widget, event):
		self.mouse_pos = event.get_coords()
	
	def on_designDrawingArea_button_release_event(self, widget, event):
		pass
	
	def on_designDrawingArea_motion_notify_event(self, widget, event):
		new_pos = event.get_coords()
		
		delta = map(sub, new_pos, self.mouse_pos)
		self.view_translate = map(add, self.view_translate, delta)
		
		self.mouse_pos = new_pos
		
		self.redraw_design()
	
	
	def on_zoomFitMenuItem_activate(self, widget = None):
		"""
		Set the zoom such that the drawing fits on the display
		"""
		avail_w, avail_h = self.design_drawing_area.window.get_size()
		
		avail_w -= 2 * DesignMixin.VIEW_DEFAULT_MARGIN
		avail_h -= 2 * DesignMixin.VIEW_DEFAULT_MARGIN
		
		zoom_height = avail_h / self.design_height
		zoom_width  = avail_w / self.design_width
		
		self.view_zoom = min(zoom_height, zoom_width)
		self.view_translate = (0.0, 0.0)
		
		self.redraw_design()
	
	
	def on_zoomInMenuItem_activate(self, widget):
		self.view_zoom += DesignMixin.MENU_ZOOM_INCREMENT
		self.redraw_design()
	
	
	def on_zoomOutMenuItem_activate(self, widget):
		self.view_zoom -= DesignMixin.MENU_ZOOM_INCREMENT
		self.view_zoom = max(0.1, self.view_zoom)
		self.redraw_design()
	
	
	def on_designDrawingArea_scroll_event(self, widget, event):
		if event.direction == gtk.gdk.SCROLL_UP:
			self.view_zoom += DesignMixin.MOUSE_ZOOM_INCREMENT
		elif event.direction == gtk.gdk.SCROLL_DOWN:
			self.view_zoom -= DesignMixin.MOUSE_ZOOM_INCREMENT
			self.view_zoom = max(0.1, self.view_zoom)
		
		self.redraw_design()
	
	
	def on_order_group_changed(self, widget):
		self.set_sort_pipeline()
		
		self.redraw_design()
	
	
	def on_extractRegCheckButton_toggled(self, widget):
		self.update_spin_button_sensitivity()
		
		# Redraw now regmarks have been established
		self.set_regmark_extraction_pipeline()
		self.redraw_design()
	
	
	def on_useRegMarksCheckButton_toggled(self, widget):
		self.update_spin_button_sensitivity()
	
	
	def on_overCutSpinButton_value_changed(self, widget):
		self.set_overcut_pipeline()
		self.redraw_design()
	
	
	def update_spin_button_sensitivity(self):
		"""
		Make spin buttons sensitive only if regmarks in use and not extracted from
		design.
		"""
		use_regmarks     = self.use_reg_marks_check_button.get_active()
		extract_regmarks = self.extract_reg_check_button.get_active()
		
		enable_spins = use_regmarks and not extract_regmarks
		
		self.reg_mark_left_spin_button.set_sensitive(  enable_spins)
		self.reg_mark_top_spin_button.set_sensitive(   enable_spins)
		self.reg_mark_width_spin_button.set_sensitive( enable_spins)
		self.reg_mark_height_spin_button.set_sensitive(enable_spins)
		
		self.recalibrate_count_spin_button.set_sensitive(use_regmarks)
	
	
	def set_sort_pipeline(self):
		"""
		Set the sort pipeline function based on the current UI
		"""
		if self.order_original_radio_button.get_active():
			# Do nothing
			func =  (lambda d: d)
		elif self.order_optimised_radio_button.get_active():
			func = plotter.design.sort.naive
		elif self.order_inner_radio_button.get_active():
			func = plotter.design.sort.hierarchical
		elif self.order_custom_radio_button.get_active():
			func = None
		else:
			raise Exception("No cutting order selected!?")
		
		# Change the relevant pipeline stage
		self.design_pipeline.set_func("sort", func)
	
	
	def set_regmark_extraction_pipeline(self):
		"""
		Set-up the pipeline for reg-mark extraction based on the UI
		"""
		extract_regmarks = self.extract_reg_check_button.get_active()
		
		def wrapper(design):
			# Wrap extract_regmarks to make it a valid pipeline function and to
			# use the extracted regmarks.
			try:
				design, (r_l, r_t, r_w, r_h) = plotter.design.filter.extract_regmarks(design)
			except plotter.design.filter.NoRegMarksInDesign, e:
				# No regmarks, turn off extraction again
				print "Couldn't extract regmarks:", repr(e)
				self.extract_reg_check_button.set_active(False)
				self.use_reg_marks_check_button.set_active(False)
				return design
			
			# If regmark extraction succeeded, enable regmakrs
			self.use_reg_marks_check_button.set_active(True)
			
			# Set regmark spinboxes
			self.reg_mark_left_spin_button.set_value(  r_l)
			self.reg_mark_top_spin_button.set_value(   r_t)
			self.reg_mark_width_spin_button.set_value( r_w)
			self.reg_mark_height_spin_button.set_value(r_h)
			
			return design
		
		# Set the pipeline stage accordingly
		if extract_regmarks:
			self.design_pipeline.set_func("regmark_extraction", wrapper)
		else:
			self.design_pipeline.set_func("regmark_extraction", (lambda d:d))
	
	
	def set_overcut_pipeline(self):
		"""
		Set the overcut pipeline based on the current UI
		"""
		amt = self.over_cut_spin_button.get_value()
		
		self.design_pipeline.set_func("overcut",
			(lambda d:
			 plotter.design.filter.overcut_closed_paths(d, amt))
		)
