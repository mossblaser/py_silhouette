#!/usr/bin/env python

"""
Decorator which allows slow functions to run partially a background thread until
they're done and then get reinserted into the GTK main thread to make GUI
modifications.

This decorator can be applied to non-value-returning methods (and functions) to
trivially run parts of the function in another (background) thread and later
return to the GTK thread to update the GUI with the results of the background
task. If the function is called repeatedly, previous calls are allowed to finish
before the next one starts so no considerations for rentrancy need be made. To
prevent a backlog of function calls building up, the system can discard old
calls once a certain number of outstanding calls have built up.

Uncaught exceptions arising within a function call are displayed on stderr.

To cope with the fact that the main-loop may be killed while there are still
idle events waiting to occur, this system automatically kills all function calls
waiting to execute in the main loop when the main-loop is exited by injecting a
MainloopTerminated exception into them.

If a function continues to execute in the background when the rest of the
program has exited, the thread is NOT automatically killed. As a result,
functions should be designed to die (quickly) when the rest of the system does.

Example usage can be found in the developer guide.
"""

import sys

from   functools import wraps
from   threading import Thread, Lock, Event, active_count
import traceback

import gtk, gobject, glib


class MainloopTerminated(Exception):
	"""
	Thrown when a thread terminates because the main-loop ended.
	"""
	pass


class RunInBackground(object):
	"""
	Decorator to wrap around a function which may take some time to execute but
	needs to interact with the GTK main thread when it has finished. Decorated
	functions must be called from the GTK main thread.
	
	This object, when instanciated, is a callable which can be used to decorate a
	single method/function. The function should be a generator which yields to
	request changes in the thread it is executing in.
	
	By default the generator starts execution in a background thread. It may yield
	(cur_step, num_steps) tuples which indicate the progress of some background
	process which can be accessed through a gtk.Adjustment object (see
	get_adjustment()).
	
	When the background process has completed, the function may yeild with no
	value (i.e. yield None) to indicate that it wishes to be placed in the GTK
	thread. This is done by inserting it into the mainloop's idle queue. The
	function should then run to completion in the GTK thread.
	
	If a wrapped method is called again before the previous call was not complete,
	the call is placed in a queue and will be executed when the previous call is
	complete. If max_queue_length is a positive, non-zero integer, the queue is
	limited to this many outstanding calls. Once full, older calls are removed in
	favour of newer calls.
	
	If start_in_gtk is True, the function wrapped starts executing in the GTK
	thread and, after yielding, is transferred to a background thread where
	execution should continue as-per-usual.
	"""
	
	def __init__(self, max_queue_length = 1, method = True, start_in_gtk = False):
		"""
		max_queue_length is the maximum number of calls which may be queued while a
		call is executing. If the queue is full, the oldest entry in the queue is
		discarded to make room for any new requests. Set to None to have an
		unlimited queue (not recommended incase calls are added at a faster rate
		than they're handled).
		
		method is a bool specifying whether this function is a method of an object
		(and thus each instance of the object should have its own call queue).
		
		start_in_gtk indicates if the thread should start in the GTK thread and then
		on the first yield enter the background thread and run as-usual. Note that
		if the call is queued the initial execution of the method in the GTK thread
		will be delayed until the presently running call has completed.
		"""
		
		self.method           = method
		self.max_queue_length = max_queue_length
		self.start_in_gtk     = start_in_gtk
		
		# A dictionary mapping objects to a tuple (lock, queue, adjustment) for each
		# object which a method call has occurred in. If method == False, only one
		# entry is present, None, which represents the single entry for this
		# function.
		#
		# Each queue is a list of tuples (args, kwargs) of calls to be made to the
		# function. A special case is when kwargs is None, in this case args is a
		# generator of a call which has already started execution.
		self.calls = {}
		
		# A lock on access to the calls dictionary
		self.calls_lock = Lock()
		
		# A list of (func, args, kwargs) to call when GTK exits
		self.on_gtk_quit = []
		self.on_gtk_quit_lock = Lock()
		
		# Flag indicating a quit has already occurred. Access holding
		# on_gtk_quit_lock.
		self.quit_occurred = False
		
		# Callback handler ID for callback when GTK quits
		self.gtk_quit_handler_id = None
	
	
	def gtk_quit_init(self):
		"""
		Adds the hooks required to detect when GTK has quit.
		"""
		# Add the hook if not already added
		if self.gtk_quit_handler_id is None:
			def on_quit():
				"""
				Callback on GTK quit.
				"""
				with self.on_gtk_quit_lock:
					self.quit_occurred = True
					for func, args, kwargs in self.on_gtk_quit:
						try:
							func(*args, **kwargs)
						except Exception, e:
							sys.stderr.write(traceback.format_exc())
			self.gtk_quit_handler_id = gtk.quit_add(0, on_quit)
	
	
	def gtk_quit_add(self, func, *args, **kwargs):
		"""
		Register the given function to be called when GTK's main-loop exits
		"""
		with self.on_gtk_quit_lock:
			self.on_gtk_quit.append((func, args, kwargs))
			
			# Call the function now if a quit already occurred
			if self.quit_occurred:
				func(*args, **kwargs)
	
	
	def gtk_quit_remove(self, func):
		"""
		Unregister the given function from being called when GTK's main-loop exits
		"""
		with self.on_gtk_quit_lock:
			for match in self.on_gtk_quit:
				if match[0] == func:
					break
			self.on_gtk_quit.remove(match)
	
	
	def update_adjustment(self, adjustment, value, max_value):
		"""
		Update the given adjustment
		"""
		adjustment.set_value(value)
		adjustment.set_upper(max_value)
	
	
	def generator_step(self, gen):
		"""
		Step a generator once. Returns (generator, gen_value) where generator is the
		generator given if there are more steps remaining and gen_value is the value
		returned upon calling next(). Exceptions are absorbed and written on stdout.
		"""
		try:
			gen_value = gen.next()
			return (gen, gen_value)
		except StopIteration:
			# Finished executing
			return (None, None)
		except Exception, e:
			# The function crashed, just dump its error and return
			sys.stderr.write("Error:\n" + traceback.format_exc())
			return (None, None)
	
	
	def start_function(self, args, kwargs):
		"""
		Runs the first step of the program given the argument and kwargs. Returns
		None if no steps remain or the function failed.
		"""
		gen = self.function(*args, **kwargs)
		return self.generator_step(gen)[0]
	
	
	def process_queue(self, lock, queue, adjustment):
		"""
		Call processing thread.
		
		Process calls in a queue until the queue is empty.
		"""
		# A trigger which is given to other threads which are being waited on.
		trigger = Event()
		
		def run_in_gtk(func, *args, **kwargs):
			"""
			Run func in the GTK idle thread and block until it completes. Rases an
			exception if the GTK mainloop is terminated.
			"""
			bailed_out = [False]
			def bailout():
				# Release the thread!
				bailed_out[0] = True
				trigger.set()
			
			# If the mainloop terminates, bail-out
			trigger.clear()
			self.gtk_quit_add(bailout)
			
			# Ensure the trigger fires even if the function call fails
			def trigger_on_fail(func, *args, **kwargs):
				try:
					func(*args, **kwargs)
				except Exception, e:
					sys.stderr.write("Error:\n" + traceback.format_exc())
				finally:
					trigger.set()
			
			glib.idle_add(trigger_on_fail, func, *args, **kwargs)
			from threading import current_thread
			trigger.wait()
			
			# Remove the bailout on mainloop quit, function returned
			self.gtk_quit_remove(bailout)
			
			if bailed_out[0]:
				raise MainloopTerminated("Thread aborted (GTK Mainloop Ended)!")
		
		
		def get_generator():
			"""
			Get the generator which is ready to start executing in the thread.
			"""
			# Get a call off the queue
			with lock:
				args, kwargs = queue[0]
			
			# Has the call already been started?
			if kwargs is None:
				# kwargs being non indicates that the function has already been
				# started and the generator is stored in args.
				return args
			
			# The call has not been started and should be started in the GTK thread
			elif self.start_in_gtk:
				# We must start the given function in the GTK thread and wait for it to
				# yield before we can continue in this thread.
				
				initial_step_return = [None]
				def initial_step(gen):
					initial_step_return[0] = self.start_function(args, kwargs)
				
				# Run the function until it completes
				run_in_gtk(initial_step, gen)
				
				# Return the generator
				return initial_step_return[0]
			
			# The call should be started in this thread
			else:
				# Get the generator
				return self.function(*args, **kwargs)
		
		
		def execute_to_gtk(gen):
			"""
			Execute the given generator until it requests to switch to the GTK thread.
			Returns a generator to be run from the GTK thread or None if not required.
			"""
			# Flag indicating if the adjustment value has been set (and thus the
			# adjustment will need setting on completion)
			adjustment_set = False
			
			while gen is not None:
				gen, progress = self.generator_step(gen)
				
				if progress is None:
					# Requested to continue in GTK thread or the function crashed
					break
				else:
					# Progress update
					value, max_value = progress
					adjustment_set = True
					glib.idle_add(self.update_adjustment, adjustment, value, max_value)
			
			# Clear/Reset the adjustment if it was set
			if adjustment_set:
				glib.idle_add(self.update_adjustment, adjustment, 0, 0)
			
			return gen
			
		
		def finish_off(gen):
			"""
			Execute the remaining steps of a generator
			"""
			while gen is not None:
				gen, gen_value = self.generator_step(gen)
		
		
		# Thread's main-loop processing calls
		try:
			queue_empty = False
			while not queue_empty:
				# Get a generator which is ready to run in this thread
				gen = get_generator()
				
				# Execute the function until it stops reporting progress and thus is ready
				# for insertion into the GTK thread.
				gen = execute_to_gtk(gen)
				
				# Resume in GTK thread and wait for it to finish
				run_in_gtk(finish_off, gen)
				
				# Remove the processed element from the queue
				with lock:
					queue.pop(0)
					queue_empty = len(queue) == 0
		
		except MainloopTerminated, e:
			# The mainloop caused this thread to end prematurely while executing
			# something in the GTK mainloop. As nothing critical should happen here
			# this is not a problem and since the application is going down and
			# critical work is not allowed in the GTK thread running under
			# RunInBackground, no cleanup is required.
			if gen is not None:
				# Inject the exception into the function to terminate it
				gen.throw(e)
			pass
	
	
	def get_lock_queue_adjustment(self, obj):
		"""
		Return the (lock, queue, adjustment) tuple for the given object. Creates
		them if they don't yet exist.
		"""
		# Create an empty queue, new lock and adjustment if needed
		with self.calls_lock:
			if obj not in self.calls:
				self.calls[obj] = (Lock(), [], gtk.Adjustment())
			
			return self.calls[obj]
	
	
	def __call__(self, function):
		"""
		Returns a wrapper around the given function which will be partially run in
		the background as per the decorator's purpose.
		"""
		self.function = function
		
		# The `wraps' decorator ensures that the wrapper is called within the
		# context of the object it wraps (rather than this object) meaning that
		# args[0] is the self refrence of the method being wrapped. It is assumed
		# that all calls to this function occur within a GTK thread
		@wraps(function)
		def wrapper(*args, **kwargs):
			# Ensure the quit handler is set up
			self.gtk_quit_init()
			
			# Get the object this method is being run in the context of (or None if this
			# is a function, not a method)
			obj = None
			if self.method:
				# Method's 'self' refrence is the first argument
				obj = args[0]
			
			# Get the queue and its lock
			lock, queue, adjustment = self.get_lock_queue_adjustment(obj)
			
			with lock:
				# If the queue is empty (i.e. execution should start ASAP, not after an
				# existing call finishes) and the function has to start in the GTK
				# thread, call it now. If we didn't, the function would be inserted into
				# the GTK idle queue and may occur after something has changed a value
				# in the widget about to be read. If a function is queued however, this
				# behaviour is OK.
				if len(queue) == 0 and self.start_in_gtk:
					# Start the first step of the function
					gen = self.start_function(args, kwargs)
					
					# If the function has no further steps (no generator), just stop
					# nothing is to be added to the queue.
					if gen is None: return
					queue.append((gen, None))
				else:
					# Add the arguments to pass to the function when its called to the
					# queue.
					queue.append((args, kwargs))
				
				# Start a new queue processor if the queue was empty
				if len(queue) == 1:
					# Start a new thread for the now newly populated queue (if the queue
					# already had stuff in, a thread exists to process it already)
					t = Thread(target = self.process_queue, args = (lock, queue, adjustment))
					t.start()
				
				# Remove excess queued items
				if self.max_queue_length is not None:
					# The first element is the one being processed, it will be removed
					# when complete. Remove all between that and the maximum length
					while len(queue) > self.max_queue_length + 1:
						queue.pop(1)
		
		return wrapper
	
	
	def get_adjustment(self, obj = None):
		"""
		Get the adjustment for progress updates during a function's execution. If
		the function is a method, takes the object whose method the adjustment is
		required for is.
		"""
		return self.get_lock_queue_adjustment(obj)[2]

