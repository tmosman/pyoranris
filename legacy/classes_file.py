#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 16:03:31 2025

@author: Tawfik Osman
"""
import dearpygui.dearpygui as dpg
import socket
import threading
import time
import random
import numpy as np
from scipy.signal import savgol_filter
import rpyc
import struct
from marvelmind import MarvelmindHedge
import sys
import os
import itertools
from datetime import datetime, timezone
import json
import subprocess
import redis
''''''

import socket
import threading
import time
import struct
import queue
import json

from datetime import datetime, timezone
from marvelmind import MarvelmindHedge
import sys
import os
import numpy as np
import itertools


class CONSTANTS:
    def __init__(self):
        self.cap_len = 1
        self.update_window = 1001   # Window to show plots on graph
        self.counter = -1
        self.check_begin = None
        self.data_counter = -1
        self.run_term = 1
        self.window_len = 5 # 10 outdoors
        self.current_rsrp = 0
        self.detect_rsrp = 0
        self.max_ris_beam_index = 182
        self.beam_interval = 1
        self.latency = 0
        self.rx_angle = [-27,-21,-15,-9,-3,0,3,9,15,21,27]

def create_folder_if_not_exists(directory):
    if not os.path.exists(directory):  # Check if the directory exists
        os.makedirs(directory)  # Create the directory and any necessary parent directories
        print(f"Directory '{directory}' created.")
    else:
        print(f"Directory '{directory}' already exists.")

class BeamIndexOptimizer:
    def __init__(self, max_ris_index, max_rx_index, current_ris_index, current_rx_index, num_index_interval):
        self.max_ris_index = max_ris_index
        self.max_rx_index = max_rx_index
        self.current_ris_index = current_ris_index
        self.current_rx_index = current_rx_index
        self.num_index_interval = num_index_interval

    def get_ris_beam_index_range(self):
        if (self.current_ris_index -  self.num_index_interval > 0  and 
            self.current_ris_index + self.num_index_interval < self.max_ris_index or self.current_ris_index - 2*self.num_index_interval > 0):
            # ris_beam_index_range = np.arange(self.current_ris_index - self.num_index_interval, 
            #                                  self.current_ris_index + self.num_index_interval + 1)
            # ris_beam_index_range = np.array([self.current_ris_index, 
            #                                  self.current_ris_index + self.num_index_interval,self.current_ris_index - self.num_index_interval])
            #(2* self.num_index_interval)
            # ris_beam_index_range = np.array([self.current_ris_index, 
            #                                  self.current_ris_index + self.num_index_interval,self.current_ris_index-(2* self.num_index_interval)])  
            
            ris_beam_index_range = np.array([self.current_ris_index, 
                                             self.current_ris_index - 2*self.num_index_interval,self.current_ris_index+(2* self.num_index_interval)]) 
            
            
        
        elif (self.current_ris_index - self.num_index_interval < 0) or (self.current_ris_index - (2*self.num_index_interval) < 0):
            #self.num_index_interval = 0
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index + self.num_index_interval, self.current_ris_index + self.num_index_interval+1])
        
        elif (self.current_ris_index + self.num_index_interval >= self.max_ris_index):
            #self.num_index_interval = 0
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index - self.num_index_interval])
           
        else:
            ris_beam_index_range = np.array([self.current_ris_index])

        return ris_beam_index_range

    def get_rx_beam_index_range(self):
        if self.current_rx_index > 0 and self.current_rx_index < self.max_rx_index:
            #rx_beam_index_range = np.arange(self.current_rx_index - 1, self.current_rx_index + 2)
            rx_beam_index_range = np.array([self.current_rx_index - 1,self.current_rx_index,  self.current_rx_index + 1])
        elif self.current_rx_index == 10 :
            rx_beam_index_range = np.array([self.current_rx_index -2,self.current_rx_index -1, self.current_rx_index,])
        elif self.current_rx_index ==  0:
            rx_beam_index_range = np.array([  self.current_rx_index,self.current_rx_index+1])
        else:
            rx_beam_index_range = np.array([self.current_rx_index, self.current_rx_index-1])
            print(f'------------------ELSE---------------{rx_beam_index_range}')
            

        return rx_beam_index_range

    def display_ranges(self):
        ris_range = self.get_ris_beam_index_range()
        rx_range = self.get_rx_beam_index_range()

        print(ris_range)
        print(rx_range)

class BeamIndexOptimizer1:
    def __init__(self, max_ris_index, max_rx_index, current_ris_index, current_rx_index, num_index_interval):
        self.max_ris_index = max_ris_index
        self.max_rx_index = max_rx_index
        self.current_ris_index = current_ris_index
        self.current_rx_index = current_rx_index
        self.num_index_interval = num_index_interval

    def get_ris_beam_index_range(self):
        if (self.current_ris_index -  self.num_index_interval > 182  and 
            self.current_ris_index + self.num_index_interval < self.max_ris_index or self.current_ris_index - 2*self.num_index_interval > 182):
            # ris_beam_index_range = np.arange(self.current_ris_index - self.num_index_interval, 
            #                                  self.current_ris_index + self.num_index_interval + 1)
            # ris_beam_index_range = np.array([self.current_ris_index, 
            #                                  self.current_ris_index + self.num_index_interval,self.current_ris_index - self.num_index_interval])
            #(2* self.num_index_interval)
            # ris_beam_index_range = np.array([self.current_ris_index, 
            #                                  self.current_ris_index + self.num_index_interval,self.current_ris_index-(2* self.num_index_interval)])  
            
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index - (2*self.num_index_interval),self.current_ris_index+(2* self.num_index_interval)]) 
            
            
        
        elif (self.current_ris_index - self.num_index_interval < 182) or (self.current_ris_index - (2*self.num_index_interval) < 182):
            #self.num_index_interval = 0
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index + self.num_index_interval, self.current_ris_index + self.num_index_interval+1])
        
        elif (self.current_ris_index + self.num_index_interval >= self.max_ris_index):
            #self.num_index_interval = 0
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index - self.num_index_interval])
            ris_beam_index_range = np.array([self.current_ris_index, 
                                             self.current_ris_index - (2*self.num_index_interval),self.current_ris_index+(2* self.num_index_interval)]) 
           
        else:
            ris_beam_index_range = np.array([self.current_ris_index])

        return ris_beam_index_range

    def get_rx_beam_index_range(self):
        if self.current_rx_index > 0 and self.current_rx_index < self.max_rx_index:
            #rx_beam_index_range = np.arange(self.current_rx_index - 1, self.current_rx_index + 2)
            rx_beam_index_range = np.array([self.current_rx_index - 1,self.current_rx_index,  self.current_rx_index + 1])
        elif self.current_rx_index == self.max_rx_index :
            rx_beam_index_range = np.array([self.current_rx_index -2,self.current_rx_index -1, self.current_rx_index,])
        elif self.current_rx_index ==  0:
            rx_beam_index_range = np.array([  self.current_rx_index,self.current_rx_index+1])
        # else:
        #     rx_beam_index_range = np.array([self.current_rx_index, self.current_rx_index-1])
        #     print(f'------------------ELSE---------------{rx_beam_index_range}')
            

        return rx_beam_index_range
    def get_rx_beam_index_range1(self):
        if self.current_rx_index > 3 and self.current_rx_index < self.max_rx_index:
            #rx_beam_index_range = np.arange(self.current_rx_index - 1, self.current_rx_index + 2)
            rx_beam_index_range = np.array([self.current_rx_index-1, self.current_rx_index,  self.current_rx_index + 1])
        elif self.current_rx_index == self.max_rx_index :
            rx_beam_index_range = np.array([ self.current_rx_index,])
        elif self.current_rx_index ==  3:
            rx_beam_index_range = np.array([  self.current_rx_index,self.current_rx_index+1])
        # else:
        #     rx_beam_index_range = np.array([self.current_rx_index, self.current_rx_index-1])
        #     print(f'------------------ELSE---------------{rx_beam_index_range}')
            

        return rx_beam_index_range
    def get_rx_beam_index_range2(self):
        if self.current_rx_index > 3 and self.current_rx_index < self.max_rx_index:
            #rx_beam_index_range = np.arange(self.current_rx_index - 1, self.current_rx_index + 2)
            rx_beam_index_range = np.array([self.current_rx_index - 1,self.current_rx_index,  self.current_rx_index + 1])
        elif self.current_rx_index == self.max_rx_index :
            rx_beam_index_range = np.array([self.current_rx_index -2,self.current_rx_index -1, self.current_rx_index,])
        elif self.current_rx_index ==  3:
            rx_beam_index_range = np.array([  self.current_rx_index,self.current_rx_index+1])
        # else:
        #     rx_beam_index_range = np.array([self.current_rx_index, self.current_rx_index-1])
        #     print(f'------------------ELSE---------------{rx_beam_index_range}')
            

        return rx_beam_index_range

    def display_ranges(self):
        ris_range = self.get_ris_beam_index_range()
        rx_range = self.get_rx_beam_index_range()

        print(ris_range)
        print(rx_range)

class BeamIndexOptimizer2:
    def __init__(self, max_ris_index, max_rx_index, current_ris_index, current_rx_index, num_index_interval):
        self.max_ris_index = max_ris_index
        self.max_rx_index = max_rx_index
        self.current_ris_index = current_ris_index
        self.current_rx_index = current_rx_index
        self.num_index_interval = num_index_interval

    def get_ris_beam_index_range(self):
        if (self.current_ris_index -  self.num_index_interval > 0  and 
            self.current_ris_index + self.num_index_interval < self.max_ris_index or self.current_ris_index - 2*self.num_index_interval > 0):
            # ris_beam_index_range = np.arange(self.current_ris_index - self.num_index_interval, 
            #                                  self.current_ris_index + self.num_index_interval + 1)
            # ris_beam_index_range = np.array([self.current_ris_index, 
            #                                  self.current_ris_index + self.num_index_interval,self.current_ris_index - self.num_index_interval])
            #(2* self.num_index_interval)
            # ris_beam_index_range = np.array([self.current_ris_index, 
            #                                  self.current_ris_index + self.num_index_interval,self.current_ris_index-(2* self.num_index_interval)])  
            
            ris_beam_index_range = np.array([self.current_ris_index, 
                                             self.current_ris_index - 2*self.num_index_interval,self.current_ris_index+(2* self.num_index_interval)]) 
            
            
        
        elif (self.current_ris_index - self.num_index_interval < 0) or (self.current_ris_index - (2*self.num_index_interval) < 0):
            #self.num_index_interval = 0
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index + self.num_index_interval, self.current_ris_index + self.num_index_interval+1])
        
        elif (self.current_ris_index + self.num_index_interval >= self.max_ris_index):
            #self.num_index_interval = 0
            ris_beam_index_range = np.array([self.current_ris_index, self.current_ris_index - self.num_index_interval])
           
        else:
            ris_beam_index_range = np.array([self.current_ris_index])

        return ris_beam_index_range

    def get_rx_beam_index_range(self):
        if self.current_rx_index > 3 and self.current_rx_index < self.max_rx_index:
            #rx_beam_index_range = np.arange(self.current_rx_index - 1, self.current_rx_index + 2)
            rx_beam_index_range = np.array([self.current_rx_index - 1,self.current_rx_index,  self.current_rx_index + 1])
        elif self.current_rx_index == 10 :
            rx_beam_index_range = np.array([self.current_rx_index -1, self.current_rx_index,])
        elif self.current_rx_index ==  3:
            rx_beam_index_range = np.array([  self.current_rx_index,self.current_rx_index+1])
        else:
            rx_beam_index_range = np.array([self.current_rx_index, self.current_rx_index-1])
            print(f'------------------ELSE---------------{rx_beam_index_range}')
            

        return rx_beam_index_range

    def display_ranges(self):
        ris_range = self.get_ris_beam_index_range()
        rx_range = self.get_rx_beam_index_range()

        print(ris_range)
        print(rx_range)

class TCP_Interface():
    def __init__(self, host_ip, port):
        self.active = False
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host_ip = host_ip
        self.port = port

    def send_ris_noACK(self,text,k):
        ## Creates connection, Send message to a server and close connection
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((self.host_ip,self.port))
            self.client.sendall(f'{text}{k}'.encode())        
        finally:
            self.client.close()
            
    def get_ris_beam(self,text):
        ## Creates connection, Send message to a server and close connection
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((self.host_ip,self.port))
            self.client.sendall(f'{text}'.encode())  
            
            recieved = self.client.recv(1024).decode()
            while 'ACK' not in recieved:
                time.sleep(0.1)
                recieved = self.client.recv(1024).decode()
                
        finally:
            self.client.close() 
        
        if  'ACK' in recieved:
            #print(f'Message received : {recieved}')
            return recieved[3:]
        else:
            return 0
        
    def send_ris_ACK(self,text,k):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recieved = ''
        try:
            self.client.connect((self.host_ip,self.port))
            if self.client:
                try:
                    self.client.sendall(f'{text}{k}'.encode())
                    recieved = self.client.recv(1024).decode()

                    while 'ACK' not in recieved:
                        time.sleep(0.0001)
                        recieved = self.client.recv(1024).decode()
                except OSError as e:
                    print(f"Error sending data: {e}")
            else:
                print("Socket is not connected")
            #self.client.sendall(f'{text}{k}'.encode()) 

           
        
        finally:
            self.client.close()
            
     

        if  'ACK' in recieved:
            #print(f'Message received : {recieved}')
            return recieved[3:]
        # elif 'RSRP' in recieved:
        #     received_dict = json.loads(recieved[3:])
        #     return received_dict
        elif 'IP' in recieved:
            received_dict = json.loads(recieved)
            return received_dict
        
        else:
            return recieved
        
        
    def send_gps_ACK(self,text,k):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recieved = ''
        try:
            self.client.connect((self.host_ip,self.port))
            if self.client:
                try:
                    self.client.sendall(f'{text}{k}'.encode())
                    recieved = self.client.recv(1024).decode()

                    while 'ACK' not in recieved:
                        time.sleep(0.0001)
                        recieved = self.client.recv(1024).decode()
                except OSError as e:
                    print(f"Error sending data: {e}")
            else:
                print("Socket is not connected")
            #self.client.sendall(f'{text}{k}'.encode()) 

           
        
        finally:
            self.client.close()
            
     

        if 'Longitude' in recieved:
            received_dict = json.loads(recieved)
            return received_dict
        
        else:
            return recieved
        
    def send_quectel_ACK(self,text,k):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recieved = ''
        try:
            self.client.connect((self.host_ip,self.port))
            self.client.sendall(f'{text}{k}'.encode()) 

            recieved = self.client.recv(1024).decode()

            while 'ACK' not in recieved:
                time.sleep(0.0001)
                recieved = self.client.recv(1024).decode()
        
        finally:
            self.client.close()

        if  'ACK' in recieved:
            #print(f'Message received : {recieved}')
            return recieved
        # elif 'RSRP' in recieved:
        #     received_dict = json.loads(recieved[3:])
        #     return received_dict
        elif 'IP' in recieved:
            received_dict = json.loads(recieved)
            return received_dict
        
        else:
            return recieved
        
    def send_jetson_ACK(self,text,k):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recieved = ''
        try:
            self.client.connect((self.host_ip,self.port))
            self.client.sendall(f'{text}{k}'.encode()) 

            recieved = self.client.recv(1024).decode()

            while 'ACK' not in recieved:
                time.sleep(0.0001)
                recieved = self.client.recv(1024).decode()
        
        finally:
            self.client.close()

        if  'ACK' in recieved:
            #print(f'Message received : {recieved}')
            return recieved
        # elif 'RSRP' in recieved:
        #     received_dict = json.loads(recieved[3:])
        #     return received_dict
        # elif 'IP' in recieved:
        #     received_dict = json.loads(recieved)
        #     return received_dict
        
        else:
            return recieved
    def send_oai_ue_ACK(self,text,k):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recieved = ''
        try:
            self.client.connect((self.host_ip,self.port))
            self.client.sendall(f'{text}{k}'.encode()) 

            recieved = self.client.recv(1024).decode()

            while 'ACK' not in recieved:
                time.sleep(0.0001)
                recieved = self.client.recv(1024).decode()
        
        finally:
            self.client.close()

        if  'ACK' in recieved:
            #print(f'Message received : {recieved}')
            return recieved
        # elif 'RSRP' in recieved:
        #     received_dict = json.loads(recieved[3:])
        #     return received_dict
        # elif 'IP' in recieved:
        #     received_dict = json.loads(recieved)
        #     return received_dict
        
        else:
            return recieved    
       
class xAppServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.server_socket = None
        self.clients = []
        self.server_thread = None
        self.running = False  # Flag to manage the server state
        self.KPIs = [None,None,None]
        #self.data_queue = queue.LifoQueue(maxsize=2)
        self.data_queue = queue.LifoQueue(maxsize=2)

    def start_server(self):
        if not self.running:
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            print(f"Server thread started at {self.ip}:{self.port}")
        else:
            print("Server is already running.")

    def run_server(self):
        try:
            # Create a TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind the socket to the provided IP and port
            self.server_socket.bind((self.ip, self.port))
            # Start listening for incoming connections
            self.server_socket.listen()
            print(f"Server started at {self.ip}:{self.port}")
            
            # Run the server to accept clients
            self.accept_clients()
        except Exception as e:
            print(f"Server start error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            #self.running = False
           # print("Server stopped")

    def accept_clients(self):
        try:
            while self.running and self.server_socket:  # Check that server is still running
                self.server_socket.settimeout(0.1)  # Short timeout to periodically check running status
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"Connection from {client_address}")
                    self.clients.append(client_socket)
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_thread.start()
                except socket.timeout:
                    continue
        except Exception as e:
            if self.running:
                print(f"Error accepting clients: {e}")
        finally:
            # Disconnect clients if server is stopped
            for client in self.clients:
                client.close()
            self.clients = []

    def handle_client(self, client_socket):
        try:
            while self.running:
                t1 = time.time()
                data = client_socket.recv(80)
                if len(data) > 0 and data != None:
                    unpacked_data = struct.unpack('iiii', data[:16])
                    RSRP = unpacked_data[1]
                    DLTHR = unpacked_data[3]/1000
                    ULTHR = unpacked_data[2]/1000
                    self.KPIs = [RSRP,DLTHR,ULTHR]
                    self.data_queue.put(self.KPIs)
                else:
                    self.KPIs = [0,0,0]
                    self.data_queue.put(self.KPIs)
                if self.data_queue.full():
                     self.data_queue.queue.clear()
                
                # if self.data_queue.full():
                #     self.data_queue.queue.clear()
                
                    
                    
                #print(f'xApp Update Latency: {(time.time()-t1)*1000} ms')
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
            print("Client disconnected")

    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        print("Server shutdown initiated")    

class BeaconServer:
    def __init__(self, dir_path, com_id):
        self.ip = com_id
        self.root_dir = dir_path
        #self.port = port
        self.server_socket = None
        #self.clients = []
        self.server_thread = None
        self.running = False  # Flag to manage the server state
        self.position = [None,None,None]
        self.data_queue = queue.LifoQueue()
        self.queue_buffer = 10
        self.num_iteration = 0
        self.data_counter = -1
        self.target_folder_pos = f'./{ self.root_dir}/Position_xyz/'
        
        self.hedge = MarvelmindHedge(tty = f'/dev/ttyACM{self.ip}',baud=115200, adr=None, debug=False) # create MarvelmindHedge thread
        self.position_initialize()
        self.last_position = None
        
        
    def position_initialize(self):
       pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H-%M-%S-%f_%Z_%Y")
       save = f'position_{self.data_counter}_{pc_utc_time}'
       self.save_path_pos = os.path.join(self.target_folder_pos,save)
       
       #########
       if not os.path.isdir(self.save_path_pos):
           os.makedirs(self.save_path_pos)

      
       if (len(sys.argv)>1):
           self.hedge.tty= sys.argv[1]
       
       self.hedge.start() # start thread
    
       
    def read_position(self):
        try:
            self.hedge.dataEvent.wait(10e-3)
            self.hedge.dataEvent.clear()

            if (self.hedge.positionUpdated):
                pos, tstamp = self.hedge.print_position_1()
                #self.display_xyz = f'Last position: {pos[1]},{pos[2]},{pos[3]}'
               
               
        except KeyboardInterrupt:
            self.hedge.stop()  # stop and close serial port
            sys.exit()
        #self.update_pos_cap(self.display_xyz) 
        return np.array([pos[1],pos[2],pos[3]])
    
    def read_position_v1(self):
        i =  0
        for num in itertools.count(start=0, step=1):
            ti = time.time()
            #self.update_status_cap('Capturing xyz !')
            if i>=1:
                #self.hedge.stop()  # stop and close serial port
                #self.update_status_cap('Capture done!')
                #sys.exit()
                break
            
            try:
                
                self.hedge.dataEvent.wait(10e-3)
                self.hedge.dataEvent.clear()
    
                if (self.hedge.positionUpdated): #True:#
                   pos, tstamp = self.hedge.print_position_1()
                   self.str_xyz = f'Last position: {pos[1]},{pos[2]},{pos[3]}'
                   ##t1 = time.time()
                   #self.update_pos_cap(self.str_xyz)
                   i+=1
            except KeyboardInterrupt:
                self.hedge.stop()  # stop and close serial port
                sys.exit()
            #print(f'Time elapse: {(time.time()-ti)*1000} ms') 
        return np.array([pos[1],pos[2],pos[3]]) 

    def start_server(self):
        if not self.running:
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            print(f"Server thread started at {self.ip}")
        else:
            print("Server is already running.")

    def run_server(self):
        try:
            # Create a TCP socket
            # self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # # Bind the socket to the provided IP and port
            # self.server_socket.bind((self.ip, self.port))
            # # Start listening for incoming connections
            # self.server_socket.listen()
            # print(f"Server started at {self.ip}:{self.port}")
            
            # Run the server to accept clients
            self.accept_clients()
        except Exception as e:
            print(f"Server start error: {e}")
        finally:
            # if self.server_socket:
            #     self.server_socket.close()
            #     self.server_socket = None
            self.running = False
            print("Server stopped")

    def accept_clients(self):
        try:
            while self.running :  # Check that server is still running
                #self.server_socket.settimeout(0.1)  # Short timeout to periodically check running status
                try:
                    #client_socket, client_address = self.server_socket.accept()
                    #print(f"Connection from {client_address}")
                    #self.clients.append(client_socket)
                    client_thread = threading.Thread(target=self.handle_client, args=())
                    client_thread.start()
                except socket.timeout:
                    continue
        except Exception as e:
            if self.running:
                print(f"Error accepting clients: {e}")
        # finally:
        #     # Disconnect clients if server is stopped
        #     for client in self.clients:
        #         client.close()
        #     self.clients = []

    def handle_client(self):
        #values = [10, 20, 30, 40, 50]
        #sample = np.random.choice(values, size=3, replace=True)
        
        try:
            while self.running:
                t1 = time.time()
                #data = client_socket.recv(80)
                #if self.position_obj:
                if self.hedge.serialPort.is_open:
                    self.pos_xyz = self.read_position_v1()
                
                    self.position = [self.pos_xyz[0] ,self.pos_xyz[1] ,self.pos_xyz[2] ]
                    #data_queue.put(self.KPIs)
                    self.data_queue.put(self.KPIs)
                    self.num_iteration +=1
                    if self.num_iteration > self.queue_buffer:
                        with self.data_queue.mutex:
                            self.data_queue.queue.clear()
                            self.num_iteration = 0
                    
                #print(f'xApp Update Latency: {(time.time()-t1)*1000} ms')
        except Exception as e:
            print(f"Error handling client: {e}")
        # finally:
        #     client_socket.close()
        #     print("Client disconnected")

    def stop_server(self):
        self.running = False
        print("Server shutdown initiated")    
             
class cameraTCPServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.server_socket = None
        self.clients = []
        self.server_thread = None
        self.running = False  # Flag to manage the server state
        self.data_queue = queue.LifoQueue()
        self.queue_buffer = 1000
        self.num_iteration = 0

    def start_server(self):
        if not self.running:
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            print(f"Server thread started at {self.ip}:{self.port}")
        else:
            print("Server is already running.")

    def run_server(self):
        try:
            # Create a TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind the socket to the provided IP and port
            self.server_socket.bind((self.ip, self.port))
            # Start listening for incoming connections
            self.server_socket.listen(5)
            print(f"Server started at {self.ip}:{self.port}")
            
            # Run the server to accept clients
            self.accept_clients()
        except Exception as e:
            print(f"Server start error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            #self.running = False
            #print("Server stopped")

    def accept_clients(self):
        try:
            while self.running and self.server_socket:  # Check that server is still running
                self.server_socket.settimeout(0.1)  # Short timeout to periodically check running status
                try:
                    client_socket, client_address = self.server_socket.accept()
                    #print(f"Connection from {client_address}")
                    self.clients.append(client_socket)
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_thread.start()
                except socket.timeout:
                    continue
        except Exception as e:
            if self.running:
                print(f"Error accepting clients: {e}")
        finally:
            # Disconnect clients if server is stopped
            for client in self.clients:
                client.close()
            self.clients = []

    def handle_client(self, client_socket):
     
        try:
            while self.running:
                t1 = time.time()
                data = client_socket.recv(1024)
                if data:
                    
                    # Deserialize the JSON string back into a dictionary
                    received_dict = json.loads(data.decode('utf-8'))
                    self.data_queue.put(received_dict)
                    self.num_iteration +=1
                    if self.num_iteration > self.queue_buffer:
                        with self.data_queue.mutex:
                            self.data_queue.queue.clear()
                            self.num_iteration = 0
                    
                #print(f'Camera Update Latency: {(time.time()-t1)*1000} ms')
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
            print("Client disconnected")

    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        print("Server shutdown initiated")    