#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

from cgi import parse_header, parse_qs
from subprocess import Popen
from time import sleep
from multiprocessing import Queue
from threading import Thread
from shutil import move, copy
import urllib.parse, urllib.request
import os
import sys
import socket
from urllib.parse import urlparse, parse_qs
from html import escape

import re
import subprocess
import http.client

#get non-default modules
modules = {}
try:
	import pynvml
	modules['pynvml'] = True
except:
	modules['pynvml'] = False
try:
	import psutil
	modules['psutil'] = True
except:
	modules['psutil'] = False
try:
	import yaml
	modules['yaml'] = True
except:
	modules['yaml'] = False

myQueue = Queue()

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
	BaseHTTPRequestHandler.end_headers()
	BaseHTTPRequestHandler.wfile.write(bytes('\n', 'utf-8'))
	BaseHTTPRequestHandler.wfile.write(bytes('<html>\n', 'utf-8'))

def get_cpu_cores(url, port=8003, default=-1):

	#prevent dead lock by requesting own URL
	if myownsocket == url:
		return int(psutil.cpu_count())

	try:
		conn = http.client.HTTPConnection(url, port)
		conn.request('GET', '/cpuInfo')
		conn.timeout = 1
		r1 = conn.getresponse()
	except:
		return default
	if r1.status == 200:
		data1 = str(r1.read())
		if data1.find('{') < data1.find('}'):
			data1 = data1[data1.find('{'):data1.find('}') + 1]
			return json.loads(data1).get('CPU Cores')
	return default

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
			if modules['psutil']:
				for proc in psutil.process_iter():
					try:
						pinfo = proc.as_dict(attrs=['pid', 'name'])
					except psutil.NoSuchProcess:
						pass
					print(pinfo)
					self.wfile.write(bytes(str(pinfo), 'utf-8'))
			else:
				self.wfile.write('I am sorry but the Python module psutil is not installed. Therefore the running processes cannot be shown.', 'utf-8')
		#returns the CPU utilization and number of cores
		elif self.path == '/cpuInfo':
			send_header(self)
			#get CPU info
			cpuInfo = {}
			if modules['psutil']:
				cpuInfo['CPU Utilization'] = int(psutil.cpu_percent())
				cpuInfo['CPU Cores'] = int(psutil.cpu_count())
			else:
				cpuInfo['Missing Python module'] = 'I am sorry but the Python module psutil is not installed. Therefore the number of CPU cores cannot be shown.'
			json_dump = json.dumps(cpuInfo)
			self.wfile.write(bytes(json_dump, 'utf-8'))
			#get GPU info
			if modules['pynvml']:
				try:
					pynvml.nvmlInit()
					gpus = pynvml.nvmlDeviceGetCount()
				except:
					gpus = 0
					self.wfile.write(bytes('No NVIDIA GPU detected', 'utf-8'))
			else:
				gpus = 0
				self.wfile.write(bytes('I am sorry but the the Python module pynvml is not installed. Therefore info about NVIDIA GPUs cannot be shown.', 'utf-8'))
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
			send_header(self)
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(('google.com', 0))
			global myownsocket
			myownsocket = s.getsockname()[0]
			port = 8003
			available_computers = []
			for i in range(1, 256):
				host = '192.168.178.' + str(i) 
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.settimeout(0.2)
				try:
					alive = sock.connect_ex((host, port))
				except:
					alive = -1
				if alive == 0:
					print('available')
					
					available_computers.append(host)
				else:
					print('not available')
				print(host)
			self.wfile.write(bytes('<form action="submit_job">\n', 'utf-8'))
			cmd_txt = """@echo off

call &quot;C:\Program Files\Autodesk\Softimage 2015\Application\bin\setenv.bat&quot;

echo ##### start_rendering

xsibatch -render &quot;Z:\TAZ_RoterFaden\PROCESS\XSI\Scenes\SC_060\088_160523_SC_060_V007.scn&quot; -frames #1#-#2# -pass &quot;BEAUTY&quot; -skip on -verbose on

echo ##### rendering_done """
			self.wfile.write(bytes('Command: <textarea name="command">' + cmd_txt + '</textarea><br>\n', 'utf-8'))
			self.wfile.write(bytes('<table border="1">\n', 'utf-8'))
			self.wfile.write(bytes('<tr>\n', 'utf-8'))
			self.wfile.write(bytes('<th>Computer</th>\n', 'utf-8'))
			self.wfile.write(bytes('<th>CPU cores</th>\n', 'utf-8'))
			self.wfile.write(bytes('<th>Start Frame [%]</th>\n', 'utf-8'))
			self.wfile.write(bytes('<th>End Frame [%]</th>\n</tr>\n', 'utf-8'))

			available_cpus = {}
			for host in available_computers:
				available_cpus[host] = abs(get_cpu_cores(host))

			total_cpus = sum(available_cpus.values())

			frame_list = {}
			start_frame = 0
			for host in available_computers:
				start_frame += 1
				frame_list[host] = [start_frame]
				start_frame =  start_frame + int(100 * (available_cpus[host] / total_cpus))
				if start_frame > 100:
					start_frame = 100
				frame_list[host].append(start_frame)
			index = 0
			for host in available_computers:
				index += 1
				self.wfile.write(bytes('<tr>\n<td>\n<input type="checkbox" name="host' + str(index) + '" value="', 'utf-8'))
				self.wfile.write(bytes(host, 'utf-8'))
				self.wfile.write(bytes('">' + host + '</td>\n', 'utf-8'))
				self.wfile.write(bytes('<td>' + str(available_cpus[host]) + '</td>\n', 'utf-8'))
				self.wfile.write(bytes('<td><input type="text" name="start' + str(index) + '" value=" ' + str(frame_list[host][0]) + '"></td>\n', 'utf-8'))
				self.wfile.write(bytes('<td><input type="text" name="end' + str(index) + '" value=" ' + str(frame_list[host][1]) + '"></td>\n', 'utf-8'))
				self.wfile.write(bytes('</tr>', 'utf-8'))
			index = 2
			self.wfile.write(bytes('<tr>\n<td>\n<input type="checkbox" name="host' + str(index) + '" value="', 'utf-8'))
			self.wfile.write(bytes(host, 'utf-8'))
			self.wfile.write(bytes('">' + host + '</td>\n', 'utf-8'))
			self.wfile.write(bytes('<td>' + str(available_cpus[host]) + '</td>\n', 'utf-8'))
			self.wfile.write(bytes('<td><input type="text" name="start' + str(index) + '" value=" ' + str(frame_list[host][0]) + '"></td>\n', 'utf-8'))
			self.wfile.write(bytes('<td><input type="text" name="end' + str(index) + '" value=" ' + str(frame_list[host][1]) + '"></td>\n', 'utf-8'))
			self.wfile.write(bytes('</tr>', 'utf-8'))
				
			self.wfile.write(bytes('</table>\n', 'utf-8'))
			self.wfile.write(bytes('<input type="submit" value="Submit Job">\n', 'utf-8'))
			self.wfile.write(bytes('</form>\n', 'utf-8'))
			self.wfile.write(bytes('</body>\n', 'utf-8'))
			self.wfile.write(bytes('</html>\n', 'utf-8'))
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
			parsed = urlparse(self.path)
			parameters = parse_qs(parsed.query)
			#print(parsed)
			print(parameters)
			self.wfile.write(bytes('<body>', 'utf-8'))
			for index in range(1, 100):
				if not parameters.get('host' + str(index)).strip():
					pass
				elif not parameters.get('start' + str(index)).strip():
					pass
				elif not parameters.get('end' + str(index)).strip():
					pass
				elif parameters.get('command'):
					cmd_txt = parameters['command'][0].replace('#1#', parameters['start' + str(index)][0].strip())
					cmd_txt = cmd_txt.replace('#2#', parameters['end' + str(index)][0].strip())
					self.wfile.write(bytes(escape(cmd_txt), 'utf-8'))
					self.wfile.write(bytes('<br>', 'utf-8'))
					print(cmd_txt)
			self.wfile.write(bytes('</body></html>', 'utf-8'))
		elif '/shutdown' in self.path:
			send_header(self)
			self.wfile.write(bytes(str(self.client_address), 'utf-8'))
			self.wfile.write(bytes("Server will be shut down now......", 'utf-8'))
			server.shutdown()
			sys.exit()

		else:
			send_header(self)
			self.wfile.write(bytes(str(self.client_address), 'utf-8'))
			self.wfile.write(bytes("<br>", 'utf-8'))
			self.wfile.write(bytes(self.path, 'utf-8'))
			print(self.path)

if __name__ == '__main__':
	#read config file
	#with open('server_configuration.ini', 'r') as yaml_file:
		#conf = yaml.load(yaml_file)
	#print(conf)
	#start server
	server = HTTPServer(('', 8003), MyRequestHandler)
	server.serve_forever()
