#!/usr/bin/env python

import os

import gtk

try:
	import cPickle as pickle
except ImportError:
	import pickle


class PresetsMixin(object):
	"""
	Logic for driving the presets UI.
	"""
	
	PRESET_FILE = os.path.expanduser("~/.plotter_presets")
	
	# Default presets to load when no file is available
	DEFAULT_PRESETS = {
		"Paper" : {
			"force"   : 28.0,
			"speed"   : 1000.0,
			"overcut" : 1.0,
			"tool"    : "Pen",
		}
	}
	
	def __init__(self):
		# The boilerplate for the list of presets to display in the GUI
		self.preset_list_store = gtk.ListStore(str,object)
		
		self.preset_combo = self.glade.get_widget("presetComboBox")
		self.preset_combo.set_text_column(0)
		self.preset_combo.set_model(self.preset_list_store)
		
		# Load the presets
		try:
			self.presets = pickle.load(open(PresetsMixin.PRESET_FILE, "r"))
		except:
			self.presets = PresetsMixin.DEFAULT_PRESETS
		self.update_presets()
	
	
	def update_presets(self):
		# Update the drop-down
		self.preset_list_store.clear()
		for name in sorted(self.presets.iterkeys()):
			settings = self.presets[name]
			self.preset_list_store.append((name, settings))
		
		# Select one if non already chosen
		if len(self.preset_list_store):
			if self.preset_combo.get_active_text() == "":
				self.preset_combo.set_active(0)
		
		# Save to file
		pickle.dump(self.presets, open(PresetsMixin.PRESET_FILE, "w"))
	
	def on_presetComboBox_changed(self, widget):
		if widget.get_active() != -1:
			settings = self.preset_list_store[widget.get_active()][1]
			
			self.speed_adjustment.set_value(settings.get("speed", 0))
			self.force_adjustment.set_value(settings.get("force", 0))
			self.over_cut_spin_button.set_value(settings.get("overcut", 0))
			
			# Set the tool to that specified (if available)
			tool_name = settings.get("tool", "Cutter")
			tool_num = -1
			for num, (name, tool) in enumerate(self.tool_list_store):
				if tool_name == name:
					tool_num = num
			self.tool_combo.set_active(tool_num)
	
	
	def on_saveCutPresetButton_clicked(self, widget):
		name = self.preset_combo.get_active_text()
		
		self.presets[name] = {
			"speed"   : self.speed_adjustment.get_value(),
			"force"   : self.force_adjustment.get_value(),
			"overcut" : self.over_cut_spin_button.get_value(),
			"tool"    : self.tool_combo.get_active_text(),
		}
		
		self.update_presets()

	
	def on_deleteCutPresetButton_clicked(self, widget):
		name = self.preset_combo.get_active_text()
		
		try:
			del self.presets[name]
		except KeyError:
			pass
		
		self.update_presets()
		if len(self.preset_list_store):
			self.preset_combo.set_active(0)
