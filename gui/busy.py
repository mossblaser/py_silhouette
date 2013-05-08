#!/usr/bin/env python

import threading
import traceback

import gtk
import glib


class BusyMixin(object):
	"""
	Logic for busy dialog.
	"""
	
	THROB_DELAY = 100
	DELAY_BEFORE_DIALOG = 200
	
	def __init__(self):
		self.busy_dialog = self.glade.get_widget("busyDialog")
		self.busy_progress_bar = self.glade.get_widget("progressBar")
		self.busy_message_label = self.glade.get_widget("messageLabel")
		
		# Number of processes running in the background (use from GTK thread)
		self.background_processes = 0
		
		def throb():
			self.busy_progress_bar.pulse()
			return True
		glib.timeout_add(BusyMixin.THROB_DELAY, throb)
	
	
	
	def busy_start(self, message = "Please Wait..."):
		self.background_processes += 1
		self.busy_message_label.set_label(message)
		def later():
			if self.background_processes:
				self.busy_dialog.show()
		glib.timeout_add(BusyMixin.DELAY_BEFORE_DIALOG, later)
	
	
	def busy_end(self):
		self.background_processes -= 1
		
		if self.background_processes == 0:
			self.busy_dialog.hide()
	
	
	def on_busyDialog_delete_event(self, widget, event):
		# Prevent the window being closed
		return True

