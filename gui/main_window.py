#!/usr/bin/env python

import inspect
import math
import os

import gtk
import gtk.glade

from device   import DeviceMixin
from presets  import PresetsMixin
from regmarks import RegmarksMixin
from design   import DesignMixin
from busy     import BusyMixin


class MainWindow(BusyMixin, DesignMixin, DeviceMixin, PresetsMixin, RegmarksMixin):
	"""
	The main window of the plotter
	"""

	def __init__(self):
		self._setup_gui()
		
		BusyMixin.__init__(self)
		DesignMixin.__init__(self)
		DeviceMixin.__init__(self)
		PresetsMixin.__init__(self)
		RegmarksMixin.__init__(self)
	
	
	def _setup_gui(self):
		# Load the window from the glade file
		gui_path = os.path.dirname(os.path.abspath(__file__))
		self.glade = gtk.glade.XML(os.path.join(gui_path,"gui.glade"))
		self.window = self.glade.get_widget("MainWindow")
		
		# Get the Main Window, and connect the "destroy" event
		if (self.window):
			self.window.connect("destroy", gtk.main_quit)
		
		# Automatically connect all signal handler callbacks
		for name in dir(self):
			if name.startswith("on_"):
				self.glade.signal_connect(name, getattr(self, name))
		
	
	
	def on_quitMenuItem_activate(self, widget):
		gtk.main_quit()
	
	def on_aboutMenuItem_activate(self, widget):
		about = self.glade.get_widget("AboutDialog")
		about.run()
		about.hide()
	
	
	def show(self):
		self.window.show()



if __name__ == "__main__":
	gtk.gdk.threads_init()
	mw = MainWindow()
	mw.show()
	gtk.main()
