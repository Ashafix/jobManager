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


class MyRequestHandler (BaseHTTPRequestHandler) :

	def do_GET(self):
		#checks if the server is alive
		if self.path == '/test':
			self.send_response(200)
			self.send_header("Content-type:", "text/html")
			self.wfile.write(bytes("\n", 'utf-8'))
			self.wfile.write(bytes('passed\n', 'utf-8'))
			self.wfile.write(bytes('server is responding', 'utf-8'))
		#returns the running processes
		if self.path == '/runningProcesses':
			self.send_response(200)
			self.send_header("Content-type:", "text/html")
			self.wfile.write(bytes("\n", 'utf-8'))

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
			self.send_response(200)
			self.send_header("Content-type:", "text/html")
			self.wfile.write(bytes("\n", 'utf-8'))
			cpuInfo = {}
			cpuInfo['CPU Utilization'] = int(psutil.cpu_percent())
			cpuInfo['CPU Cores'] = int(psutil.cpu_count())
			json_dump = json.dumps(cpuInfo)
			self.wfile.write(bytes(json_dump, 'utf-8'))
		elif  self.path == '/availableComputers':
			port = 8003
			self.send_response(200)
			self.send_header("Content-type:", "text/html")
			self.wfile.write(bytes("\n", 'utf-8'))

			for i in range(34, 35):
				host = 'http://192.168.178.' + str(i) 
				alive = ''
				
				alive = socket.socket().connect((host, port))
				
				if alive:
					print(host)
					self.wfile.write(bytes(host + '\n', 'utf-8'))
		elif '/submit_job' in self.path:
			self.send_response(200)
			self.send_header("Content-type:", "text/html")
			self.wfile.write(bytes("\n", 'utf-8'))
			self.wfile.write(bytes(str(self.client_address), 'utf-8'))
			output = {}
			parsed = urlparse.urlparse(self.path)
			parameters = urlparse.parse_qs(parsed.query)
		else:
			self.send_response(200)
			self.send_header("Content-type:", "text/html")
			self.wfile.write(bytes("\n", 'utf-8'))
			self.wfile.write(bytes(str(self.client_address), 'utf-8'))
			self.wfile.write(bytes("\n", 'utf-8'))
			self.wfile.write(bytes(self.path, 'utf-8'))
		

if __name__ == '__main__':
	#read config file
	with open('server_configuration.ini', 'r') as yaml_file:
		conf = yaml.load(yaml_file)
	print(conf)
	#start server
	server = HTTPServer(('', 8003), MyRequestHandler)
	server.serve_forever()
