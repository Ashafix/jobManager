#!/usr/bin/env python

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import psutil
from cgi import parse_header, parse_qs
from subprocess import Popen
from time import sleep
from multiprocessing import Queue
from threading import Thread
from shutil import move, copy
import urllib.parse
import os
import sys
import socket
import yaml
import re
import subprocess
import pynvml


myQueue = Queue()
max_threads = psutil.cpu_count()
#dictionaries for stdit/stdout filenames and file objects
#primary key: worker_ID
worker_stdin = {}
worker_stdout = {}
tmp_file_in = {}
tmp_file_out = {}

#dictionary storing all the running processes
processes = {}
proc_items = {}


#dictionary storing all jobs
jobs = {}

def send_header(BaseHTTPRequestHandler):
	BaseHTTPRequestHandler.send_response(200)
	BaseHTTPRequestHandler.send_header('Content-type:', 'text/html')
	BaseHTTPRequestHandler.wfile.write(bytes('\n', 'utf-8'))
	BaseHTTPRequestHandler.wfile.write(bytes('<html>', 'utf-8'))
class MyRequestHandler (BaseHTTPRequestHandler) :

	def do_GET(self):
		#checks if the server is alive
		if self.path == '/test':
			send_header(self)
			self.wfile.write(bytes('passed<br>', 'utf-8'))
			self.wfile.write(bytes('server is responding', 'utf-8'))
		#returns the running processes
		if self.path == '/runningProcesses':
			send_header(self)
			#send response:
			for proc in psutil.process_iter():
				try:
					pinfo = proc.as_dict(attrs=['pid', 'name'])
				except psutil.NoSuchProcess:
					pass
				print(pinfo)
				self.wfile.write(bytes(str(pinfo), 'utf-8'))
		#returns the CPU utilization and number of cores
		elif self.path == '/cpuInfo':
			send_header(self)
			#get CPU info
			cpuInfo = {}
			cpuInfo['CPU Utilization'] = int(psutil.cpu_percent())
			cpuInfo['CPU Cores'] = int(psutil.cpu_count())
			json_dump = json.dumps(cpuInfo)
			self.wfile.write(bytes(json_dump, 'utf-8'))
			#get GPU info
			try:
				pynvml.nvmlInit()
				gpus = pynvml.nvmlDeviceGetCount()
			except:
				gpus = 0
				self.wfile.write(bytes('No NVIDIA GPU detected', 'utf-8'))
			for i in range(gpus):
				handle = pynvml.nvmlDeviceGetHandleByIndex(i)
				self.wfile.write(bytes("<br>GPU " + str(i + 1) + ": " + pynvml.nvmlDeviceGetName(handle).decode('utf-8'), 'utf-8'))
				try:
					self.wfile.write(bytes('<br>Temperature: ' + str(pynvml.nvmlDeviceGetTemperature(handle, 0)) + '&deg;C', 'utf-8'))
				except:
					self.wfile.write(bytes('<br>Could not retrieve temperature', 'utf-8'))
				try:
					gpu_mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
					self.wfile.write(bytes('<br>Total memory: %i Megabytes' % (gpu_mem.total / 10**6), 'utf-8'))
					self.wfile.write(bytes(str('<br>Free memory: %i' % (gpu_mem.free/gpu_mem.total*100)) + '%', 'utf-8'))
				except:
					self.wfile.write(bytes('<br>nCould not retrieve memory information', 'utf-8'))
			if gpus > 0:
				try:
					pynvml.nvmlShutdown()
				except:
					pass


		elif self.path == '/availableComputers':
			port = 8003
			send_header(self)

			for i in range(34, 35):
				host = 'http://192.168.178.' + str(i) 
				alive = ''
				
				alive = socket.socket().connect((host, port))
				
				if alive:
					print(host)
					self.wfile.write(bytes(host + '<br>', 'utf-8'))
		elif self.path == '/notepad':
			send_header(self)
			self.wfile.write(bytes("Notebook", 'utf-8'))
			try:
				subprocess.Popen('notepad.exe')
			except:
				self.wfile.write(bytes("failed", 'utf-8'))
		elif '/submit_job' in self.path:
			send_header(self)
			self.wfile.write(bytes(str(self.client_address), 'utf-8'))
			output = {}
			parsed = urlparse.urlparse(self.path)
			parameters = urlparse.parse_qs(parsed.query)
		else:
			send_header(self)
			self.wfile.write(bytes(str(self.client_address), 'utf-8'))
			self.wfile.write(bytes("<br>", 'utf-8'))
			self.wfile.write(bytes(self.path, 'utf-8'))
		

if __name__ == '__main__':
	#read config file
	#with open('server_configuration.ini', 'r') as yaml_file:
		#conf = yaml.load(yaml_file)
	#print(conf)
	#start server
	server = HTTPServer(('', 8003), MyRequestHandler)
	server.serve_forever()
