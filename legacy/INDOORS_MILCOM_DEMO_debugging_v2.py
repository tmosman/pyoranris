# -*- coding: utf-8 -*-
"""
Created on Sat Oct 12 01:26:57 2024

@author: Tawfik Osman
"""
import time

from classes_file import *
#from robot_detector import *
from filterpy.kalman import KalmanFilter
import os
import csv
import warnings
# Suppress RankWarning only
warnings.simplefilter("ignore", np.RankWarning)





class TCPClientGUI:
    def __init__(self):
        self.root_dir ='Demo'
# %% DIRECTORIES
        self.data_collection = False
        self.ue_mobility_record = True
        
        self.data_coverage = f'./{ self.root_dir}/Coverage_Datasets/'
        self.dir_mobility =  f'./{ self.root_dir}/UE_Mobility/'
        self.pos_xy = f'./{self.root_dir}/root_position/'
        
        if self.data_collection and self.ue_mobility_record: 
            self.create_folder_if_not_exists([self.data_coverage,self.dir_mobility])
        else:
            self.create_folder_if_not_exists([self.dir_mobility])
        
        
        
        self.ue_mob_dir = f'./{self.dir_mobility}/Experiment_at_{datetime.now(timezone.utc).strftime("%a_%b_%d_%H_%M_%S_%f_%Z_%Y")}/'
        self.create_folder_if_not_exists([self.ue_mob_dir])
        
        self.raw_data_dir = f'{self.ue_mob_dir}/Raw_data/'
        self.create_folder_if_not_exists([self.ue_mob_dir])
        
        
        self.target_folder_pos = f'./{self.raw_data_dir }/Position_xyz/'
        self.target_folder_rsrp = f'./{self.raw_data_dir}/RIS_rsrp/'
        self.target_folder_throughput = f'./{self.raw_data_dir}/RIS_Throughput/'
        self.target_folder_lat = f'./{self.raw_data_dir}/latencies/'
        self.target_folder_index = f'./{self.raw_data_dir}/RIS_RX_index/'
        self.target_folder_time = f'./{self.raw_data_dir}/time_now/'
        
        
        self.csv_filename = f'./{self.ue_mob_dir}/data_log.csv'
      
        # Open CSV at the beginning
        self.csv_file = open(self.csv_filename, mode='w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["timestamp", "update_latency", "RSRP","RIS_index","RX_index", "RIS_Angle","RX_Angle"])  # CSV header
        self.csv_file.flush()

        
        
        
# %% INITIALIZATIONS & CONSTANTS
        self.create_folder_if_not_exists([self.target_folder_lat ,self.target_folder_pos,self.target_folder_rsrp ,self.target_folder_throughput,self.target_folder_index])
        
        #self.create_folder_if_not_exists([self.dir_coverage ])
       
        ### Constants
        self.constants = CONSTANTS()
        self.current_rsrp = self.constants.current_rsrp
        self.algorithm_latency = self.constants.latency
        self.update_latency  = 0
        self.actual_rx_beams_angles = []
        self.data_dict = {}
        
        
        
        
        self.found = False
        
        ### Servers
        self.xApp_run = True
        self.xApp_client = True
        self.RIS_client = False
        self.zed_server = False
        self.position_obj = False
        self.ue_status = False
        self.robot_server = False
        self.ZED2_obj = False
        self.ZED2_client = False
        #self.rx_udp_client = False
        self.gps_server = False
        
        self.position_xy_server = False
        self.quectel_module = False
        
        
        self.initialize_ue_beams  = False
        
        
        
        self.mycounter = 1
        ### IPs
        self.ue_evk_ip = '192.168.10.102'
        self.myhostIP = '127.0.0.1'
        self.camera_server_host = '192.168.1.128'#'192.168.1.114'
        self.ris_server_IP = '192.168.10.123'# '192.168.1.11'# ON RASPBERRY PI
        self.jetson_ip = '192.168.1.116'
        self.ue_laptop = '192.168.10.114'
        
        self.xApp_port = 8081
        self.camera_port = 9908
        self.ue_evk_port = 9999
        self.ris_server_port = 9999
        self.jetson_port = 9999
# %% START SERVERS
        

       #self.udp_server_address = (self.ue_evk_ip, 9999)
#        ris_rsrp
        ###Initis
        self.record = False
        self.connected_rsrp = False
        self.connected_beam = False
        self.connected_robot = False
        self.sock_rsrp = None
        self.sock_beam = None
        self.plot_data_rsrp = []
        self.plot_data_beam = []
        self.new_plot_data = []
        self.rx_plot_data = []
        self.stop_flag = False
        self.beam_index = None
        #self.buffer_array = np.zeros((self.update_window,))
        self.buffer_array  = []
        self.rsrp_update_buffer = []
        #self.buffer_array = np.zeros((self.update_window,))
        self.position_buffer = np.zeros((self.constants.update_window,3))
        #self.check_begin = None
        self.mobility = False
        self.xyz = None
        self.ris_beamsweep_status = False
        
        self.last_two_lines = [] # A global buffer to store the last two lines of output
        self.iperf_process = None # A global reference to the subprocess so we can stop it
    
        self.output = False
        self.current_ris_beam = None
        self.current_rx_index = None
        
        self.bestRSRP = None
        
        
       
        ### Initialize servers
        if self.xApp_run:
            self.tcp_server = xAppServer(self.myhostIP, self.xApp_port)
            
        if self.position_xy_server:
            self.tcp_server_pos = BeaconServer(self.pos_xy, '1')
            
        if self.xApp_client and self.xApp_run:
            self.xApp_monitoring = TCP_Interface(self.myhostIP, 5005)
            
        if self.zed_server:
            self.camera_server = cameraTCPServer(self.camera_server_host, self.camera_port)
        if not self.quectel_module:
            self.nr_oai_ue = TCP_Interface(self.ue_laptop, 5001)
            
        if self.ue_status:
            self.UE_client = TCP_Interface(self.ue_evk_ip, self.ue_evk_port)
            #self.send_command_ue(f'SET{10}')
        if self.ue_status and self.initialize_ue_beams:
            self.rx_conn1 = rpyc.connect(self.ue_evk_ip, 18814, config={"sync_request_timeout": 1,"compression": True,"keepalive": 1})
            self.rx_conn1._channel.stream.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tx_conn2 = rpyc.connect(self.ue_evk_ip, 18815)
            self.tx_conn2._channel.stream.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            self.rx_conn1.root.exposed_execute_beam(f'set{10}')
            self.tx_conn2.root.exposed_execute_beam(f'set{10}')
            
        # if self.rx_udp_client:
        #     self.ue_udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.gps_server:
            self.gps_client = TCP_Interface(self.ue_laptop, 9991)
            
        if self.RIS_client:
            self.gnb_rx_conn  = TCP_Interface(self.ris_server_IP, self.ris_server_port)  #
            self.initial_ris_beam = self.gnb_rx_conn.get_ris_beam('GET')
            print(f' Initial RIS Beam: {self.initial_ris_beam}')
            
            self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', 160)
            
            
            #self.current_ris_beam = self.initial_ris_beam
            self.new_plot_data = [int(self.current_ris_beam)]
            
        if self.position_obj:
            self.hedge = MarvelmindHedge(tty = '/dev/ttyACM0',baud=115200, adr=None, debug=False) # create MarvelmindHedge thread
            self.position_initialize()
            self.last_position = None
        else:
            self.hedge = None
            self.last_position = np.array([0,0,0])
       
        if self.robot_server:
            self.redis_client = redis.Redis(host=self.ue_evk_ip , port=6379)
        else:
            self.redis_client = None
        
        if self.ZED2_obj:
            self.camera_object = ZED2_Obj(fs_rate=10)
            self.camera_object.capture_image_bbox(iteration=5)
            
        if self.ZED2_client:
            self.zed_client = TCP_Interface(self.jetson_ip, self.jetson_port)
            
# %% GUI FRAMEWORK
        # Initialize DearPyGui context
        dpg.create_context()
        # Create a font registry
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        #font_path = "Roboto-Regular.ttf"
        if not os.path.exists(font_path):
            raise FileNotFoundError("Font file not found. Please update the path to a valid TTF font.")
        
        # Register the font
        with dpg.font_registry():
            large_font = dpg.add_font(font_path, 24)
        # Create theme for red plot line
        with dpg.theme() as red_line_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 0, 0, 255))  # 🔴 Red
                
                
        with dpg.theme() as custom_theme:
            with dpg.theme_component(dpg.mvPlot):
                # Adjust line thickness or other style variables as needed
                dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2.0)


        # Create the GUI elements for RSRP window
        with dpg.window(label="RSRP Plot", width=480 * 2, height=380 * 2, pos=(10, 10)):  # Positioned at (0, 0)
           
            with dpg.group(horizontal=True):
                self.connect_button = dpg.add_button(label="Plot RSRP", callback=self.connect_to_rsrp_server)
                # dpg.bind_item_font(self.connect_button, bold_font)  # Apply bold font
                dpg.bind_item_theme(dpg.last_item(), self.create_rounded_button_theme())  # Apply rounded corners theme
                self.stop_button = dpg.add_button(label="Stop RSRP Update", callback=self.stop_rsrp_plotting)
                # dpg.bind_item_font(dpg.last_item(), bold_font)  # Apply bold font
                dpg.bind_item_theme(dpg.last_item(), self.create_rounded_button_theme())  # Apply rounded corners theme

            # Add a display console for showing the current RSRP value in horizontal alignment
            with dpg.group(horizontal=True):
                dpg.add_text("Current RSRP:")
                self.rsrp_display = dpg.add_text("", color=[255, 0, 0])  # Display console with red color for visibility
                
                dpg.add_text("    Monitoring:")
                self.move_display = dpg.add_text("", color=[255, 0, 0])  # Display console with red color for visibility
                self.static_display = dpg.add_text("", color=[0, 128, 0])  # Display console with red color for visibility
                self.ue_display = dpg.add_text("", color=[255, 140, 0])
   
            # Plot for RSRP
            with dpg.plot(label="RSRP Real-time Plot", height=320 * 2, width=470 * 2):
                dpg.add_plot_legend()
                self.x_axis_rsrp = dpg.add_plot_axis(dpg.mvXAxis, label="Iteration")
                self.y_axis_rsrp = dpg.add_plot_axis(dpg.mvYAxis, label="RSRP Value (dBm)")

                # Set Y-axis limits between -140.0 and -40.0
                dpg.set_axis_limits(self.y_axis_rsrp, -120.0 , -60.0)
                self.line_series_rsrp = dpg.add_line_series([], [], label="RSRP", parent=self.y_axis_rsrp)
                #dpg.configure_item(self.line_series_rsrp , weight=3.0)
               
        # Create a new window for the random value plot
        with dpg.window(label="Beams Plot Window", width=430 * 2, height=380 * 2, pos=(985, 10)):
   
            # Add the button to clear all plotted values
            self.clear_button = dpg.add_button(label="Clear Beam Plot", callback=self.clear_plot_values)
            dpg.bind_item_theme(self.clear_button, self.create_rounded_button_theme())
            with dpg.group(horizontal=True):
                dpg.add_text("Current RIS Beam:")
                self.beam_display = dpg.add_text("", color=[255, 0, 0])
                
                dpg.add_text("   Current RX Beam:")
                self.rxbeam_display = dpg.add_text("", color=[255, 0, 0])
                
                
                
            # Plot for new random values
            with dpg.plot(label="Beam Index Plot", height=320 * 2, width=420 * 2):
                dpg.add_plot_legend()
                self.x_axis_random = dpg.add_plot_axis(dpg.mvXAxis, label="Iteration")
                self.x_axis_rx = dpg.add_plot_axis(dpg.mvXAxis, label="Iteration")
                self.y_axis_random = dpg.add_plot_axis(dpg.mvYAxis, label="RIS Beam (°)")
                self.y_axis_rx = dpg.add_plot_axis(dpg.mvYAxis2, label="RX Beam (°) ")
                # if self.max_ris_beam_index == 22:
                #     dpg.set_axis_limits(self.y_axis_random, -5, 25)
                # else:
                dpg.set_axis_limits(self.y_axis_random, -5, self.constants.max_ris_beam_index+2)
                dpg.set_axis_limits(self.y_axis_random,180, 365)
                dpg.set_axis_limits(self.y_axis_random,10,70)
                dpg.set_axis_limits(self.y_axis_rx, -30, 30)
                self.line_series_random = dpg.add_line_series([], [], label="RIS Beam ", parent=self.y_axis_random)
                self.line_series_rx = dpg.add_line_series([], [], label="RX Beam", parent=self.y_axis_rx)
                
                
                dpg.bind_item_theme(self.line_series_rx, red_line_theme)
                dpg.bind_item_theme(self.line_series_rx, custom_theme)
        #  # Register the font
        # with dpg.font_registry():
        #      large_font = dpg.add_font(font_path, 20)   
        with dpg.window(label="xApp Server", width=380, height=220, pos=(10,785)):
                #dpg.add_text("Socket server control")19
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start", callback=self.start_server_callback)
                dpg.add_button(label="Stop", callback=self.stop_server_callback)
                dpg.add_text(" (Status): ", tag="server_status_text")  # Display server status
            dpg.add_text("")
            #dpg.add_text("Experiment Status: ", tag="pos_status_text")
            dpg.add_text(" Monitoring KPIs: ", tag="xApp_status_text")   
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start ", callback=self.start_running_xApp)
                dpg.add_button(label="Stop ", callback=self.stop_running_xApp)
                dpg.add_button(label="EXIT", callback=self.terminate_xApp_server)
            #dpg.add_text("")
            # dpg.add_text("Robot's Position: ", tag="pos_values")
            with dpg.group(horizontal=True):
                dpg.add_text("Data Collection:")
                dpg.add_button(label="Capture Sample", callback=self.capture_data_sample)
        
        
        
        with dpg.window(label="Beam Sweeping", width=380, height=220, pos=(400,785)):
                #dpg.add_text("Socket server control")
            #dpg.add_text("Status: ", tag="camera_server_status_text")  # Display server status
            with dpg.group(horizontal=True):
                dpg.add_button(label="RIS Beam Sweeping", callback=self.start_beamsweeping)
                dpg.add_button(label="Terminate", callback=self.stop_beamsweeping)
            dpg.add_text("Experiment Status: ", tag="bs_status_text")
            dpg.add_text("")
            
            dpg.add_text("Mobility Test Status:",tag="mobility_status_text")
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Joint BS", callback=self.joint_beamsweeping)
                dpg.add_button(label="Activate Test", callback=self.set_mobility_enable)
                dpg.add_button(label="Deactivate", callback=self.set_mobility_disable)
                
            # dpg.add_text("")   
            # # dpg.add_text("Experiment Status: ", tag="camera_status_text")
            # dpg.add_text("Robot's Bounding Box: ", tag="BBox_values")
            
            
                
        
        with dpg.window(label="Robot Control ", width=350, height=220, pos=(790, 785)):
            dpg.add_text("Direction [1-> FWD  -1 -> BWD]")
            self.robot_input = dpg.add_input_int(label="Enter (-1/1)",width=150)
            dpg.add_text("Stop ROBOT [1]")
            self.robot_stop = dpg.add_input_int(label="Enter (1/0)",width=150)
            with dpg.group(horizontal=True):
                
                dpg.add_button(label="Move", callback=self.move_robot_command)
                dpg.add_button(label="Reset", callback=self.reset_to_zero, user_data=self.robot_stop)
                self.result_text_dir = dpg.add_text("Result displays here")
                

        with dpg.window(label="Set RIS/UE Index Values", width=350, height=220, pos=(1150, 785)):
            self.gnb_input = dpg.add_input_int(label="RIS Beam Index",width=150)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Set index", callback=self.set_ris_beam_and_display)
                self.result_text_gnb = dpg.add_text("Result displays here")
            dpg.add_text("")  
            self.ue_input = dpg.add_input_int(label="UE Beam Index",width=150)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Set beam", callback=self.set_ue_beam_and_display)
                self.result_text_ue = dpg.add_text("Result displays here")
                
            
            
            
        with dpg.window(label="OAI nrUE Control ", width=335, height=220, pos=(1510, 785)):
            #self.gnb_input = dpg.add_input_text(label="COMMAND")
            if self.quectel_module:
                
                self.command_text = dpg.add_input_text(
                        label="COMMAND",
                        tag="commad_text",
                        callback=self.to_upper_callback,
                        on_enter=False  # Change to True if you prefer conversion after pressing Enter
                    )
                #self.result_text_gnb = dpg.add_text("Result will be displayed here")
                dpg.add_button(label="Send Command", callback=self.send_command_modem)
                self.command_return = dpg.add_text("Result will be displayed here")
            else:
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Start nrUE", callback=self.start_ue_session)
                    dpg.add_button(label="Stop nrUE", callback=self.stop_ue_session)
                    dpg.add_button(label="Exit", callback=self.terminate_ue_server)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Get UE IP", callback=self.get_ue_ip)
                    dpg.add_button(label="Update UE IP", callback=self.update_ue_ip)
                dpg.add_text("Experiment Status: ", tag="oai_status_text")
                    #self.oai_text_ue = dpg.add_text("Result will be displayed here")
                #dpg.add_button(label="Set gain", callback=self.set_ue_gain_and_display)
            
            dpg.add_input_text(label="Target IP", default_value="10.0.0.x", tag="ip_input")
            with dpg.group(horizontal=True):
                # Button to start iperf
                dpg.add_button(label="Run Iperf", callback=self.start_iperf_callback)
                
                # Button to stop iperf
                dpg.add_button(label="Stop Iperf", callback=self.stop_iperf_callback)
        
            # Text widget that shows the last two lines of iperf output
            #dpg.add_text("", tag="iperf_output")
            
       
        dpg.bind_font(large_font)
        dpg.set_exit_callback(self.on_exit_callback)
        # Setup DearPyGui rendering
        dpg.create_viewport(title='Evaluation Console [RIS-ORAN] ', width=1600, height=900)
        
        dpg.setup_dearpygui()
        dpg.show_viewport()
# %% CALL-BACK FUNCTIONS
        
    def send_command_ue(self,message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect(("192.168.1.115", 5000))
            client_socket.sendall(message.encode())
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")

    def create_folder_if_not_exists(self, directory):
        for dir_path in directory:
            
            if not os.path.exists(dir_path):  # Check if the directory exists
                os.makedirs(dir_path)  # Create the directory and any necessary parent directories
                print(f"Directory '{dir_path}' created.")
            else:
                print(f"Directory '{dir_path}' already exists.")
            
            
    def set_mobility_enable(self):
        self.mobility = True
        dpg.set_value("mobility_status_text",f"Mobility Test Status: Active")
        return 1
    def set_mobility_disable(self):
        self.mobility = False
        dpg.set_value("mobility_status_text",f"Mobility Test Status: Not Active")
        # stop robot
        if self.robot_server:
            status_robot = dpg.get_value(self.robot_stop)
            self.current_dir = 1
            if status_robot == 0:
                tt_now = time.time()-self.check_time
                if tt_now> 1:
                    tt_now = 1.5
                else:
                    tt_now = tt_now
                data = {'status':False, "key": np.round((tt_now),5),'dir':str(self.current_dir)}
            else:
                data = {'status':False, "key": np.round((time.time()-self.check_time),5),'dir':str(self.current_dir)}
            self.redis_client.lpush("queue_name", json.dumps(data))
        return 1
    
    def start_beamsweeping(self):
        self.ris_beamsweep_status = True
        return 1 
    
    def stop_beamsweeping(self):
        self.ris_beamsweep_status = False
        return 1 

     # Callback function to reset the value to zero
    def reset_to_zero(self,sender, app_data, user_data):
        dpg.set_value(user_data, 0)  
        dpg.set_value(self.result_text_dir, f"Reset: {0}")
        #print('SET')
        data = {'status':True, "key": 0.1}
        
        if self.robot_server:
            self.redis_client.lpush("queue_name", json.dumps(data))
            _, recv_ = self.redis_client.brpop("queue_name")
        

    def run_iperf(self,ip_value):
        """
        Runs the iperf command in a background thread and continuously updates
        'last_two_lines' with the latest output lines.
        """
        #lobal iperf_process
    
        command = [
            "docker", "exec",
            "-it",
            "oai-ext-dn",
            "iperf",
            "-u",          # Use UDP
            "-t", "86400", # 24-hour duration (1 day)
            "-i", "1",     # Report interval
            "-fk",         # Format in kilo (Kbits/s)
            "-B", "192.168.70.135",  # Local bind IP
            "-b", "100M",            # Bandwidth
            "-c", ip_value           # Target IP (from user input)
        ]
    
        self.iperf_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
        # Continuously read lines from iperf output
        for line in self.iperf_process.stdout:
            # Keep only the last two lines
            if len(self.last_two_lines) >= 5:
                self.last_two_lines.pop(0)
            self.last_two_lines.append(line)
    
        # Clear out reference once iperf completes or is killed
        self.iperf_process.wait()
        self.iperf_process = None

    def start_iperf_callback(self):
        """
        Called when the user clicks the 'Run Iperf' button.
        Launches a background thread that runs the iperf command.
        """
        ip_val = dpg.get_value("ip_input")
        t = threading.Thread(target=self.run_iperf, args=(ip_val,), daemon=True)
        t.start()
    
    def stop_iperf_callback(self):
        """
        Called when the user clicks the 'Stop Iperf' button.
        Kills the subprocess running iperf (if it exists).
        """
        
        if self.iperf_process is not None:
            self.iperf_process.kill()
            self.iperf_process = None
            print("Iperf process has been killed.")
    
    def update_iperf_output(self):
        """Updates the Dear PyGui text widget with the last two lines of iperf output."""
        output_text = "".join(self.last_two_lines)
        dpg.set_value("iperf_output", output_text)   
    
    
    def send_command_modem(self,):
        command_value = dpg.get_value(self.command_text)
        kpis = self.UE_client.send_quectel_ACK(command_value,0)
        received_dict = json.loads(kpis)
        #print(f'_______HERE__________ {received_dict}')
        if 'RSRP' in received_dict:
            dpg.set_value(self.command_return, f"Output: RSRP: {received_dict['RSRP']}, RSRQ: {received_dict['RSRQ']}, SINR: {received_dict['SINR']}")
        elif 'IP' in received_dict:
            dpg.set_value(self.command_return, f"Output: IP: {received_dict['IP']}")
        else:
            dpg.set_value(self.command_return, f"Output: {received_dict}")
            
        return 1
    def start_ue_session(self):
        if not self.quectel_module:
            status = self.nr_oai_ue.send_oai_ue_ACK('START', 0)
            for ii in range(12):
                dpg.set_value("oai_status_text",f'Waiting {"."*int(ii)} ! ')
                time.sleep(.5)
                
            dpg.set_value("oai_status_text",f"Status: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def stop_ue_session(self):
        if not self.quectel_module:
            status = self.nr_oai_ue.send_oai_ue_ACK('STOP', 0)
            dpg.set_value("oai_status_text",f"Status: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def terminate_ue_server(self):
        if not self.quectel_module:
            status = self.nr_oai_ue.send_oai_ue_ACK('EXIT', 0)
            dpg.set_value("oai_status_text",f"Status: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def get_ue_ip(self):
        if not self.quectel_module:
            status = self.nr_oai_ue.send_oai_ue_ACK('IP', 0)
            dpg.set_value("oai_status_text",f"Status: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def update_ue_ip(self):
        if not self.quectel_module:
            status = self.nr_oai_ue.send_oai_ue_ACK('NET', 0)
            dpg.set_value("oai_status_text",f"Status: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def start_running_xApp(self):
        if self.xApp_run and self.xApp_client:
            status = self.xApp_monitoring.send_oai_ue_ACK('START', 0)
            for ii in range(6):
                dpg.set_value("xApp_status_text",f' Monitoring xApp: {"."*int(ii)}  ')
                time.sleep(0.5)
            dpg.set_value("xApp_status_text",f" Monitoring xApp: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def stop_running_xApp(self):
        if self.xApp_run and self.xApp_client:
            status = self.xApp_monitoring.send_oai_ue_ACK('STOP', 0)
            #time.sleep(5)
            dpg.set_value("xApp_status_text",f" Monitoring xApp: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    def terminate_xApp_server(self):
        if self.xApp_run and self.xApp_client:
            status = self.xApp_monitoring.send_oai_ue_ACK('EXIT', 0)
            #time.sleep(5)
            dpg.set_value("xApp_status_text",f" Monitoring xApp: {status[5:]}")
        else:
            print('-------- No Session -------- !!! ')
    
        
    def to_upper_callback(self,sender, app_data):
        """
        This callback is triggered whenever the text changes (or when Enter is pressed,
        depending on the `on_enter` flag). It converts the input to uppercase.
        """
        uppercase_text = app_data.upper()
        dpg.set_value(sender, uppercase_text)

    def create_rounded_button_theme(self):
        """Create a theme for buttons with rounded corners."""
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 10)  # Rounded corners with radius 10
        return theme
    
    
    def connect_to_robot_server(self):
        ip_address = dpg.get_value(self.ip_input_robot)
        port = int(dpg.get_value(self.port_input_robot))

        try:
            
            # Create a new socket connection
            self.sock_robot = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_robot.connect((ip_address, port))
            #self.sock_robot.settimeout(0.001)
            self.connected_robot = self.UE_client.send_ris_noACK('MOVE',self.current_dir)
            
            print(f"Connected to Robot server at {ip_address}:{port}")
        except Exception as e:
            print(f"Failed to connect to Robot server: {e}")
            self.connected_robot = False
            
    def send_robot_command(self):
        self.current_dir = dpg.get_value(self.robot_input)
        dpg.set_value(self.result_text_dir, f"Current dir.: {self.current_dir}")
        self.UE_client.send_ris_noACK('MOVE',self.current_dir)
        
        status_robot = dpg.get_value(self.robot_stop)
        
        if status_robot == 0:
            data = {'status':True, "key": np.round((0.2),5),'dir':str(self.current_dir)}
        else:
            data = {'status':False, "key": np.round((0.2),5),'dir':str(self.current_dir)}
        self.redis_client.lpush("queue_name", json.dumps(data))
        
        return 1
    def send_robot_command_v2(self):
        """Callback to send robot direction"""
        self.current_dir = dpg.get_value(self.robot_input)
        
        self.UE_client.send_ris_noACK('MOVE',self.current_dir)
     
        dpg.set_value(self.result_text_dir, f"Current dir.: {self.current_dir}")
        
        
    
    def set_robot_direction(self):
        """Callback to send robot direction"""
        self.current_dir = dpg.get_value(self.robot_input)
        if str(self.current_dir) == '-1':
            self.sock_robot.sendall('MOVE0'.encode())
        elif  str(self.current_dir) == '1':
            self.sock_robot.sendall('MOVE1'.encode())
        else:
            self.sock_robot.sendall('MOVE00'.encode())
       #self.sock_robot.sendall(f'{self.current_dir}'.encode())
        dpg.set_value(self.result_text_dir, f"Current dir.: {self.current_dir}")
        recieved = self.sock_robot.recv(1024).decode()
        while 'ACK' not in recieved:
            time.sleep(0.1)
            recieved = self.sock_robot.recv(1024).decode()
        print(recieved)
            

    def connect_to_rsrp_server(self):
        
        # If already connected, disconnect first
        if self.connected_rsrp:
            self.disconnect_from_rsrp_server()

        try:
            # Clear plot data and reset stop flag when reconnecting
            self.plot_data_rsrp.clear()
            self.plot_data_beam.clear()
            dpg.set_value(self.line_series_rsrp, [[], []])  # Clear the plot
            dpg.set_value(self.line_series_random, [[], []])
            self.stop_flag = False
            self.connected_rsrp = True
            #self.last_position = [0,0,0 ] #self.read_position_v1()

            # Start a new thread for receiving data from the server
            threading.Thread(target=self.receive_rsrp_data, daemon=True).start()
            # print(f"Connected to RSRP server at {ip_address}:{port}")
        except Exception as e:
            print(f"Failed to connect to RSRP server: {e}")
            self.connected_rsrp = False
    def read_position_v1(self):
        i =  0
        for num in itertools.count(start=0, step=1):
            ti = time.time()
            self.update_status_cap('Capturing xyz !')
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
                   self.update_pos_cap(self.str_xyz)
                   i+=1
            except KeyboardInterrupt:
                self.hedge.stop()  # stop and close serial port
                sys.exit()
            #print(f'Time elapse: {(time.time()-ti)*1000} ms') 
        return np.array([pos[1],pos[2],pos[3]]) 
    
    def update_rsrp_plot(self, value):
        self.plot_data_rsrp.append(value)
        if len(self.plot_data_rsrp) > self.constants.update_window * 2:
            self.plot_data_rsrp.pop(0)
        x_vals = list(range(len(self.plot_data_rsrp)))
        y_vals = self.plot_data_rsrp
        dpg.set_value(self.line_series_rsrp, [x_vals, y_vals])
        if len(x_vals) > self.constants.update_window:
            dpg.set_axis_limits(self.x_axis_rsrp, len(x_vals) - self.constants.update_window, len(x_vals))
        else:
            dpg.set_axis_limits(self.x_axis_rsrp, 0, len(x_vals))
            
    def update_beam_plot(self, value):
        if self.constants.max_ris_beam_index > 183:
            value = (20+((value-182)*0.25))
        else:
             value = 20+(value*0.25)
        self.new_plot_data.append(value)
        #self.plot_data_rsrp.append(value)
        if len(self.new_plot_data) > self.constants.update_window * 2:
            self.new_plot_data.pop(0)
        x_vals = list(range(len(self.new_plot_data)))
        y_vals = self.new_plot_data
        
        dpg.set_value(self.line_series_random, [x_vals, y_vals])
       
        #dpg.set_value(self.line_series_rsrp, [x_vals, y_vals])
        if len(x_vals) > self.constants.update_window:
            dpg.set_axis_limits(self.x_axis_random, len(x_vals) - self.constants.update_window, len(x_vals))
        else:
            dpg.set_axis_limits(self.x_axis_random, 0, len(x_vals))
        # if self.counter == 0:
        #     self.clear_plot_values()
    def update_rxbeam_plot(self, value):
        value = self.constants.rx_angle[value]
        self.rx_plot_data.append(value)
        #self.plot_data_rsrp.append(value)
        if len(self.rx_plot_data) > self.constants.update_window * 2:
            self.rx_plot_data.pop(0)
        x_vals = list(range(len(self.rx_plot_data)))
        y_vals = self.rx_plot_data
        
        dpg.set_value(self.line_series_rx, [x_vals, y_vals])
       
        #dpg.set_value(self.line_series_rsrp, [x_vals, y_vals])
        if len(x_vals) > self.constants.update_window:
            dpg.set_axis_limits(self.x_axis_rx, len(x_vals) - self.constants.update_window, len(x_vals))
        else:
            dpg.set_axis_limits(self.x_axis_rx, 0, len(x_vals))
            
    def covert_index_angle(self,ris_index,rx_index):
        if self.constants.max_ris_beam_index > 183:
            ris_angle = (20+((ris_index-182)*0.25))
        else:
             ris_angle = 20+(ris_index*0.25)
        
        rx_angle = self.constants.rx_angle[rx_index]
        return ris_angle, rx_angle
             
    def update_rsrp_display(self, value):
        
        dpg.set_value(self.rsrp_display, f"{value} dBm")
             
    def update_move_display(self, value):
        if 'Stable' in value:
            dpg.set_value(self.static_display, f"{value}")
            a = ' '
            dpg.set_value(self.move_display, f"{a}")
            dpg.set_value(self.ue_display, f"{a}")
        elif 'Not' in value:
            dpg.set_value(self.ue_display, f"{value}")
            
            a = ' '
            dpg.set_value(self.move_display, f"{a}")
            dpg.set_value(self.static_display, f"{a}")
        elif 'running' in value:
            dpg.set_value(self.ue_display, f"{value}")
            
            a = ' '
            dpg.set_value(self.move_display, f"{a}")
            dpg.set_value(self.static_display, f"{a}")
        elif 'Dropped' in value:
            dpg.set_value(self.move_display, f"{value}")
            a = ' '
            dpg.set_value(self.static_display, f"{a}")
            dpg.set_value(self.ue_display, f"{a}")
        else:
            a = ' '
            dpg.set_value(self.move_display, f"{a}")
            dpg.set_value(self.static_display, f"{a}")
            dpg.set_value(self.ue_display, f"{a}")

    
            

    def stop_rsrp_plotting(self):
        self.stop_flag = True
        if self.connected_rsrp:
            self.disconnect_from_rsrp_server()
        print("RSRP Plotting stopped")

    def disconnect_from_rsrp_server(self):
        # if self.sock_rsrp:
        #     self.sock_rsrp.close()
        self.connected_rsrp = False
        print("Disconnected from RSRP server")
        

    def clear_plot_values(self):
        self.new_plot_data.clear()
        self.rx_plot_data.clear()
        dpg.set_value(self.line_series_random, [[], []])
        dpg.set_axis_limits(self.x_axis_random, 0, 1)
        dpg.set_value(self.line_series_rsrp, [[], []])
        dpg.set_value(self.line_series_rx, [[], []])
        
        #dpg.set_axis_limits(self.line_series_rsrp, 0, 1)
        
        self.beam_index = None
        # # Close the connection
        # self.conn1.close()
        # self.conn2.close()
        self.rx_conn1.close()
        self.tx_conn2.close()
        print("Connection closed")
        print("Cleared all plotted values")
        
        
    def set_ue_beam_and_display(self):
        """Callback to add 1 to the input integer and display the result."""
        current_value = dpg.get_value(self.ue_input)
        self.current_rx_index = self.rx_conn1.root.exposed_execute_beam(f'set{current_value}')
        _ = self.tx_conn2.root.exposed_execute_beam(f'set{current_value}')  
        dpg.set_value(self.result_text_ue, f"Current Index: {self.current_rx_index}")
      
        
    def set_ris_beam_and_display(self):
        """Callback to add 1 to the input integer and display the result."""
        current_value = dpg.get_value(self.gnb_input)
        #incremented_value = self.gnb_rx_conn.root.exposed_execute_gain(f'set{current_value}')
        if self.RIS_client:
            self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('SET',current_value)
        else:
            self.current_ris_beam = int(current_value)
        #self.current_ris_beam = self.ZED2_client.send_ris_ACK('RIS',current_value)
        
        
        dpg.set_value(self.result_text_gnb, f"Current Index: {self.current_ris_beam}")
  
    def start_server_callback(self):
        self.tcp_server.start_server()
        self.update_status("xApp Started")

    def stop_server_callback(self):
        self.tcp_server.stop_server()
        self.update_status("xApp Stopped")      
        
    def start_cameraserver_callback(self):
        self.camera_server.start_server()
        self.update_cameraserver_status("Server Camera started")
        #self.read_camera()
    
    def stop_cameraserver_callback(self):
        self.camera_server.stop_server()
        self.update_cameraserver_status("Server Camera stopped")
        
    def update_status(self,status):
        dpg.set_value("server_status_text", f"{status}")  
        
    # Function to update the server status in the GUI
    def update_cameraserver_status(self,status):
        dpg.set_value("camera_server_status_text", f"{status}")
        
        
    def update_status_cap(self,status):
        dpg.set_value("bs_status_text", f"Status: {status}")
    def update_status_beamsweeping(self,status):
        dpg.set_value("bs_status_text",f"Status: {status}")
        
    def update_pos_cap(self,status):
        dpg.set_value("pos_values", f"{status}")
    def update_camera_cap(self,status):
        dpg.set_value("BBox_values", f"{status}")
    
    def update_beam_display(self, value_ind):
        if self.constants.max_ris_beam_index > 183:
            value = (20+((value_ind-182)*0.25))
        else:
             value = 20+(value_ind*0.25)
        dpg.set_value(self.beam_display, f"{value}°  ({value_ind})")
    def update_rxbeam_display(self, value_ind):
        value = self.constants.rx_angle[value_ind]
        dpg.set_value(self.rxbeam_display, f"{value}°  ({value_ind})")
   
    def position_initialize(self):
       pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H-%M-%S-%f_%Z_%Y")
       save = f'position_{self.constants.data_counter}_{pc_utc_time}'
       self.save_path_pos = os.path.join(self.target_folder_pos,save)
       
       #########
       if not os.path.isdir(self.save_path_pos):
           os.makedirs(self.save_path_pos)

      
       if (len(sys.argv)>1):
           self.hedge.tty= sys.argv[1]
       
       self.hedge.start() # start thread
    

    def read_camera(self):
        return self.camera_server.data_queue.get()
    
    def on_exit_callback(self):
        #global csv_file
        self.csv_file.close()
        
    def move_robot_command(self):
        self.current_dir = dpg.get_value(self.robot_input)
        
        self.UE_client.send_ris_noACK('MOVE',self.current_dir)
     
        dpg.set_value(self.result_text_dir, f"Current dir.: {self.current_dir}")
        
        while True:
            #self.check_time = 
            if self.robot_server:
                status_robot = dpg.get_value(self.robot_stop)
                self.current_dir = 1
                if status_robot == 0:
                    tt_now = 0.4
                    if tt_now> 1:
                        tt_now = 1.5
                    else:
                        tt_now = tt_now
                    data = {'status':True, "key": np.round((tt_now),5),'dir':str(self.current_dir)}
                else:
                    data = {'status':False, "key": np.round((time.time()-self.check_time),5),'dir':str(self.current_dir)}
                self.redis_client.lpush("queue_name", json.dumps(data))
        

# %% MAIN PROCESSING DATA FUNCTIONS
    def receive_rsrp_data(self):
        time1 = time.time()
        while self.connected_rsrp and not self.stop_flag:
            while dpg.is_dearpygui_running():
           
                if self.constants.counter+1 == self.constants.update_window:
                    self.constants.run_term+=1
                    self.buffer_array = []
                    self.rsrp_update_buffer = []
                    self.position_buffer = np.zeros((self.constants.update_window,3))
                    self.constants.counter = -1
                    self.constants.check_begin = None
                    #self.clear_plot_values()
                    
                try:
                    start_time = datetime.now().timestamp()
                    data = self.tcp_server.data_queue.get()
                    #self.current_rsrp = -80
                    self.current_rsrp = data[0]
                    
                    #pos_data = self.tcp_server_pos.data_queue.get()
                    #print(f'Robot Position: {pos_data}')
                    
                    
                    if self.current_ris_beam == None:
                        if self.RIS_client:
                            print('HERE')
                            self.current_ris_beam = self.gnb_rx_conn.get_ris_beam('GET')
                            #self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', 20)
                        else:
                            self.current_ris_beam = 0
                            
                            
                    if self.current_rx_index == None:
                        if self.ue_status:
                            # get the current beam from UE sivers
                            self.current_rx_index = int(self.rx_conn1.root.exposed_execute_get_beam())
                            
                            #self.current_rx_index =  10
                        else:
                            self.current_rx_index = 5
                    
                    # if self.position_obj:
                    #     #if self.hedge.serialPort.is_open:
                    #     self.pos_xyz = self.read_position_v1()
                    if self.zed_server:
                        dict_bbox = self.read_camera()
                    #tt = time.time()
                    if self.ZED2_obj:
                        dict_bbox = self.camera_object.capture_image_bbox(1)
                        #print(dict_bbox)
                    if self.ZED2_client:
                        coord = self.zed_client.send_jetson_ACK('CAP', 0)
                        dict_bbox = json.loads(coord)
                        
                        
                    #print(f'Time Difference: {(time.time() - tt) *1000} ms')
                    
                    if self.current_rsrp  is None:
                        #print(data)
                        continue
                    
                    elif self.current_rsrp == 0:
                        if self.constants.counter == -1:
                            self.constants.counter = 180
                        self.constants.counter+=1
                        if self.ris_beamsweep_status: #and self.ZED2_client:
                            send_index = (self.constants.counter+1)%self.constants.max_ris_beam_index
                            #send_index = (self.constants.counter+1)%182
                            #send_index+=182
                            #send_index = 20
                            if self.RIS_client:
                                self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', send_index)
                                # if send_index == 0:
                                #     time.sleep(2)
                                print(f'RIS Beam : {self.current_ris_beam} ..............')
                                
                                selected_rx_index = np.arange(5,7)
                                #selected_rx_index = np.arange(10)
                                buffer_rx_rsrp = np.zeros(selected_rx_index.shape)
                                # RX beam sweep
                                if self.ue_status:
                                    for rx_kk, rx_index in enumerate(selected_rx_index):
                                        self.current_rx_index = self.rx_conn1.root.exposed_execute_beam(f'set{rx_index}')
                                        _ = self.tx_conn2.root.exposed_execute_beam(f'set{rx_index}')
                                        rsrp = self.tcp_server.data_queue.get()[0]
                                        buffer_rx_rsrp[rx_kk] = rsrp

                                        self.update_rsrp_display(rsrp )
                                        self.update_rxbeam_display(int(self.current_rx_index))
                                        self.update_beam_display(int(self.current_ris_beam))

                                    self.current_rx_index = selected_rx_index[np.argmax(buffer_rx_rsrp)]
                                
                                # fix the optimal rx beams at UE
                                #self.current_rx_index = self.rx_conn1.root.exposed_execute_beam(f'set{self.current_rx_index}')
                                #_ = self.tx_conn2.root.exposed_execute_beam(f'set{self.current_rx_index}')
                                #self.current_rsrp = np.mean(self.record_nonzero_kpi_data(num_capture=2)[0])
                                self.current_rsrp = self.tcp_server.data_queue.get()[0]
                                #print('Done 1')
                                time.sleep(.1)
                                    
                            else:
                                self.current_ris_beam = int(send_index)
                                time.sleep(100e-3)
                            
                            self.update_rsrp_plot(self.current_rsrp )
                            self.update_rsrp_display(self.current_rsrp)
                            self.update_beam_display(int(self.current_ris_beam))
                            self.update_beam_plot(int(self.current_ris_beam))
                            self.update_rxbeam_display(int(self.current_rx_index))
                            self.update_rxbeam_plot(int(self.current_rx_index))
                            
                            
                            
                            
                            if send_index == self.constants.max_ris_beam_index - 1:
                                self.update_status_beamsweeping('Beam Search Done !')
                                time.sleep(1)
                            elif send_index == 0:
                                self.update_status_beamsweeping('Beam Started !')
                            else:
                                self.update_status_beamsweeping(f'Searching {"."*int(send_index)} !')
                            self.update_move_display(f'UE Not Connected, Performing RIS Beam Search{"."*int(send_index%7)} !')
                            
                            #time.sleep(1) 
                            
                        else:
                            if self.constants.counter-1 == -1:
                                self.update_move_display(' ')
                            else:
                                self.update_move_display('UE Not Connected')
                            continue
                            
    
                    else:
                        
            
                        if self.current_rsrp  != 0:
                            self.check_time = time.time()
                            
                            if self.constants.counter == -1:
                                if self.RIS_client:
                                    self.current_ris_beam = self.gnb_rx_conn.get_ris_beam('GET')
                                    
                                else:
                                    self.current_ris_beam = 0
                                #self.current_rx_index = int(self.rx_conn1.root.exposed_execute_get_beam())
                            self.ris_beamsweep_status = False # set false after UE connected
                            self.constants.counter+=1
                            self.update_rsrp_plot(self.current_rsrp )
                            self.update_rsrp_display(self.current_rsrp )
                            self.update_beam_display(int(self.current_ris_beam))
                            self.update_beam_plot(int(self.current_ris_beam))
                            self.update_rxbeam_display(int(self.current_rx_index))
                            self.update_rxbeam_plot(int(self.current_rx_index))
                            self.data_dict = {'RSRP':self.current_rsrp,'DLTH':np.mean(np.array(data[1])),'ULTH':np.mean(np.array(data[2])),'pos':{}, 'latency':self.algorithm_latency, 'RIS_index':self.current_ris_beam, 'RX_index':self.current_rx_index, 'time_now': datetime.now().timestamp(), 'update_latency':self.update_latency}
                            if not self.mobility:
                                self.update_move_display('UE is running')
                                
                            self.update_status_beamsweeping(' ')
                            # with data_lock:
                            #     value_kpi =latest_kpi 
                            #     print(f' Latest KPIs : {value_kpi} ')
                            
    
                            # ####
                            
                            #print(self.counter)
                            self.buffer_array.append(int(self.current_rsrp ))
                            
                            
                            
                                    
                            # if self.position_obj:
                            #     self.position_buffer[self.counter,:] = self.pos_xyz
                            
                            # if self.record == True:
                            #     self.save_kpi_data(self.counter)
                            if self.ue_mobility_record:
                                #self.save_kpi_data(self.constants.counter,self.data_dict)
                                #print(f'-------;;;------------ {type(self.data_dict["RIS_index"]) }, {self.data_dict["RIS_index"]}')
                                
                                ris_angle, rx_angle = self.covert_index_angle( int(self.data_dict['RIS_index']),self.data_dict['RX_index'])
                                # Write to CSV
                                self.csv_writer.writerow([self.data_dict['time_now'], self.data_dict['update_latency'], self.data_dict['RSRP'], self.data_dict['RIS_index'],self.data_dict['RX_index'], ris_angle, rx_angle])
                                self.csv_file.flush()
    
                            if self.mobility:
                                                                
                                status, _ = self.monitor_rsrp_hybrid_v1(THRESHOLD=1)
                                #status, _ = self.monitor_with_KFilter(THRESHOLD=3)
                                status = False
                                curr_time = time.time()
                                if status:
                                    #self.data_dict = self.ris_with_mobility_v4(int(self.current_ris_beam),int(self.current_rx_index))
                                    self.data_dict = self.joint_bs_ris_with_mobility(int(self.current_ris_beam),int(self.current_rx_index))
                                    #time.sleep(0.305)
                                    print('Algorithm Applied!')
                                    self.mycounter+=1
                                    #rint(f'Time Mobilitity Sweep: { self.latency*1000} ms')
                                else:
                                     time.sleep(0.405)
                                        
                                self.algorithm_latency = (time.time() - curr_time)
                                
                                if self.robot_server:
                                    status_robot = dpg.get_value(self.robot_stop)
                                    self.current_dir = 1
                                    if status_robot == 0:
                                        tt_now = time.time()-self.check_time
                                        if tt_now> 1:
                                            tt_now = 1.5
                                        else:
                                            tt_now = tt_now
                                        data = {'status':True, "key": np.round((tt_now),5),'dir':str(self.current_dir)}
                                    else:
                                        data = {'status':False, "key": np.round((time.time()-self.check_time),5),'dir':str(self.current_dir)}
                                    self.redis_client.lpush("queue_name", json.dumps(data))
                                    #print('ROBOT')
                                
                            # else:
                            #     time.sleep(0.05)
                            self.update_latency = datetime.now().timestamp() - start_time 
                            
                            #print(f'Check Beam{self.current_ris_beam} ------------------')
                            # if self.ue_mobility_record:
                            #     self.save_kpi_data(self.constants.counter,self.data_dict)
                           
                        else:
                            self.update_rsrp_display(self.current_rsrp )
                  
                    #time.sleep(1)
                    #print(f'Time: {(time.time()-time1)*1000} ms ---------------')
                    #print("Doone !")
                    #time.sleep(0.4)
                    time1 = time.time()
                    # Render only when needed
                    #dpg.render_dearpygui_frame()
                except socket.timeout:
                    continue
                except Exception as e:
                  
                    print(f"Error receiving RSRP data: {e} ---------ME-----")
                    #self.disconnect_from_rsrp_server()

    
    
                
# %% MOBILITY SUB-FUNCTIONS
    def monitor_rsrp_hybrid(self,THRESHOLD):
        ##
        if self.constants.check_begin == None:
            window_rsrp = self.buffer_array[0:self.constants.window_len]
            #window_rsrp = self.buffer_array[self.counter-self.window_len:self.counter+1]
            
            print('In None')
           
        else:
            
            window_rsrp = self.buffer_array[self.constants.check_begin:self.constants.counter+1]
            #print('')
            #window_rsrp = self.buffer_array[-(self.constants.window_len+1):-1]
        #print(f'Window size: {len(window_rsrp)}')
        if len(window_rsrp) >= self.constants.window_len:
            self.constants.check_begin = self.constants.counter 
            #print(window_rsrp[:-1])
            #window_rsrp_trunc = window_rsrp[-(self.constants.window_len):-1] 
            window_rsrp_trunc = window_rsrp
            #window_rsrp_trunc = window_rsrp
            #smoothen_rsrp = (window_rsrp[-(self.constants.window_len+5):-1])
            smoothen_rsrp = self.smooth_data(window_rsrp)
            #smoothen_rsrp = window_rsrp_trunc
            print(max(window_rsrp_trunc)-min(window_rsrp_trunc),window_rsrp_trunc )
            if self.is_descending(smoothen_rsrp,THRESHOLD)[0]:
                print(f"The curve is mostly descending.{self.is_descending(smoothen_rsrp,THRESHOLD)[0]}")
                self.update_move_display('RSRP Dropped')
                self.output = True, -1
            elif abs(max(window_rsrp_trunc)-min(window_rsrp_trunc)) >= THRESHOLD:
                self.update_move_display('RSRP Dropped')
                print(f"---- Min-Max RSRP greater than threshold ------ ")
                self.output = True, -1
                
                
            elif self.is_descending(smoothen_rsrp,THRESHOLD)[0] == False or abs(max(window_rsrp_trunc)-min(window_rsrp_trunc)) < THRESHOLD:
                self.update_move_display('RSRP Stable')
               # print("The curve is not mostly descending."
                #print(".......")
                self.output = False, -1
       
                
        else:
            self.update_move_display('RSRP Stable')
            self.output = False,0
            #print('Not UP')
                    
                
            
        return self.output
    
    
    def monitor_rsrp_hybrid_v1(self,THRESHOLD):
        ##
        if self.constants.check_begin == None:
            window_rsrp = self.buffer_array[0:self.constants.window_len]
            #window_rsrp = self.buffer_array[self.counter-self.window_len:self.counter+1]
            
            print('In None')
           
        else:
            
            window_rsrp = self.buffer_array[self.constants.check_begin:self.constants.check_begin+self.constants.window_len+1]
            print(f'LEN: {len(window_rsrp)}, {window_rsrp}, {len(self.buffer_array)}, {self.constants.check_begin}, {self.constants.window_len+1}')
            #window_rsrp = self.buffer_array[-(self.constants.window_len+1):-1]
        #print(f'Window size: {len(window_rsrp)}')
        if len(window_rsrp) >= self.constants.window_len:
            self.constants.check_begin = self.constants.counter - self.constants.window_len+1
            
            window_rsrp_trunc = window_rsrp
            smoothen_rsrp = self.smooth_data(window_rsrp)
            #smoothen_rsrp = window_rsrp_trunc
            print(max(window_rsrp_trunc)-min(window_rsrp_trunc),window_rsrp_trunc )
            if self.is_descending(smoothen_rsrp,THRESHOLD)[0]:
                print(f"The curve is mostly descending.{self.is_descending(smoothen_rsrp,THRESHOLD)[0]}")
                self.update_move_display('RSRP Dropped')
                self.output = True, -1
            elif abs(max(window_rsrp_trunc)-min(window_rsrp_trunc)) >= THRESHOLD:
                self.update_move_display('RSRP Dropped')
                print(f"---- Min-Max RSRP greater than threshold ------ ")
                self.output = True, -1
                
                
            elif self.is_descending(smoothen_rsrp,THRESHOLD)[0] == False or abs(max(window_rsrp_trunc)-min(window_rsrp_trunc)) < THRESHOLD:
                self.update_move_display('RSRP Stable')
               # print("The curve is not mostly descending."
                #print(".......")
                self.output = False, -1
       
                
        else:
            self.update_move_display('RSRP Stable')
            self.output = False,0
            #print('Not UP')
                    
                
            
        return self.output
    
    
    def monitor_with_KFilter(self, THRESHOLD):
        if self.constants.check_begin == None:
            window_rsrp = self.buffer_array[0:self.constants.window_len]
            #window_rsrp = self.buffer_array[self.counter-self.window_len:self.counter+1]
            
            print('In None')
           
        else:
            
            window_rsrp = self.buffer_array[self.constants.check_begin:self.constants.counter+1]
            #window_rsrp = self.buffer_array[-(self.constants.window_len+1):-1]
        if len(window_rsrp) >= self.constants.window_len:
            self.constants.check_begin = self.constants.counter+1 
            
            # Initialize Kalman Filter
            kf = KalmanFilter(dim_x=1, dim_z=1)
            kf.x = np.array([window_rsrp[0]])  # Initial state
            kf.F = np.array([[1]])  # State transition matrix
            kf.H = np.array([[1]])  # Observation matrix
            kf.P *= 1000  # Covariance matrix
            kf.R = 2  # Measurement noise
            kf.Q = 0.1  # Process noise
            
            filtered_rsrp = []
            
            
            
            # Apply Kalman Filter
            for measurement in window_rsrp:
                kf.predict()
                kf.update(measurement)
                filtered_rsrp.append(kf.x[0])
        
            filtered_rsrp = np.array(filtered_rsrp)  # Convert to NumPy array
            #print(window_rsrp)
            #print(filtered_rsrp)
            if (filtered_rsrp[0]-filtered_rsrp[-1]) > THRESHOLD:
                print("The curve is mostly descending.")
                self.update_move_display('RSRP Dropped')
                self.output = True, -1
                
                
                
            else:
                self.update_move_display('RSRP Stable')
                
               # print("The curve is not mostly descending."
                #print(".......")
                self.output = False, -1
            
        else:
            self.update_move_display('RSRP Stable')
            self.output = False, -1
                
        
        return self.output
    
    def is_descending(self, y, THRESHOLD):
        # Determine if the curve is mostly descending
        decreasing_samples = np.sum(np.diff(y) <= 0)
        #print(np.diff(y),np.sum(np.diff(y)) , len(y), decreasing_samples)
        if decreasing_samples / len(y) >= 0.6 and (abs(min(y)-max(y))>=THRESHOLD):
            output = True
        else:
            output = False
                
        return output,abs(min(y)-max(y))
    
    def smooth_data(self,y):
        polyorder=len(y)-1
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            print("Warning: RSRP data contains NaN or Inf values!")
            y = np.nan_to_num(y)  # Replace NaN with zero
        # Apply Savitzky-Golay filter to smooth the data
        value = (min(len(y) // 2, len(y))+1)
        # Ensure window length is odd
        window_length = value if value % 2 != 0 else value - 1
        polyorder = min(polyorder, window_length - 1)
        
        # Apply the filter
        y_smooth = savgol_filter(y, window_length=window_length, polyorder=polyorder)
        return y_smooth

        
    def record_nonzero_kpi_data(self, num_capture):
        rsrps = []
        dlthrup = []
        ulthrup = []
        check_count = 0
        #tt = time.time()
        while len(rsrps)<num_capture:
           
            try:
                check_count+=1
                #print('About to recieve from TCP')
                retrieved = self.tcp_server.data_queue.get(timeout=0.2)
                #print(retrieved)
                data,dl_througput,ul_througput = retrieved[0],retrieved[1],retrieved[2]
                #print('After recieve from TCP')
                
                
                if not data:
                    continue
                
                if check_count>3:
                    break

                else:
                    if data != 0 : #and  dl_througput != 0.0: #ul_througput != 0.0 and
                    
                        rsrps.append(data)
                        dlthrup.append(dl_througput)
                        ulthrup.append(ul_througput)
                    else:
                        rsrps.append(0.0)
                        dlthrup.append(0)
                        ulthrup.append(0)
                        
                    # except ValueError:
                    #     #continue
                    #     print(f"Error converting value {rsrp_value} to float:",last_str,rsrp_value)
                #time.sleep(0.01)
           
            except Exception as e:
                print('------------HERE--------------------')
                print(f"Error receiving RSRP data: {e}")
                self.disconnect_from_rsrp_server()
                break
        #print(f'Capture xApp: {(time.time()-tt)*1000} ms')
        return np.array(rsrps),np.array(dlthrup), np.array(ulthrup)
    
    def save_kpi_data(self, instance, data_dict):
        
        
        # Generate and save .npy files in the folder
        pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H_%M_%S_%f_%Z_%Y")
        file_path_rsrp = os.path.join(self.target_folder_rsrp, f"rsrp_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
        file_path_tru = os.path.join(self.target_folder_throughput, f"dl_ul_throughput_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
        file_path_pos = os.path.join(self.target_folder_pos,f"position_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
        file_path_lat = os.path.join(self.target_folder_lat,f"time_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
        #file_path_time = os.path.join(self.target_folder_time,f"time_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
        file_path_index = os.path.join(self.target_folder_index,f"ris_rx_index_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy") 
        rsrps,dl_tr, ul_tr,  indices = data_dict['RSRP'],  data_dict['DLTH'],  data_dict['ULTH'],  np.array((int(data_dict['RIS_index']), int(data_dict['RX_index'])))
        #rsrps = kpis
        #thru_put = np.array([np.mean(dl_tr),np.max(ul_tr)])
        
        algorithm_update, gui_update, instantaneous_time = data_dict['latency'],data_dict['update_latency'],data_dict['time_now']
        #print(algorithm_update, gui_update, instantaneous_time)
        
        # Save the data as a .npy file
        np.save(file_path_rsrp, rsrps)
        np.save(file_path_lat, np.array((algorithm_update,gui_update,instantaneous_time)))
        np.save(file_path_tru, np.array((dl_tr, ul_tr)))
        np.save(file_path_index, indices)
        if self.gps_server:
            np.save(file_path_pos, np.array((pos['gps_utc'], pos['Latitude'],pos['Longitude'])))
        return 1
    

    def joint_bs_ris(self):
        range_beams = np.arange(1,self.constants.max_ris_beam_index,self.constants.beam_interval)
        selected_rx_index = np.arange(3,7)                
        self.update_status_cap(' ')
        
       
        # Monitor RSRP:
        ris_rsrp = np.zeros((len(range_beams),))
        for kk, ris_index in enumerate(range_beams):
           #time_1 = time.time()
           self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', int(ris_index))
           #print(f'Time for one RIS beam : {(time.time()-time_1)*1000} ms')
           
           buffer_rx_rsrp = np.zeros(selected_rx_index.shape)
           tt = time.time()
           if self.ue_status:
               # RX beam sweep
               for rx_kk, rx_index in enumerate(selected_rx_index):
                   self.rx_conn1.root.exposed_execute_beam(f'set{rx_index}')
                   self.tx_conn2.root.exposed_execute_beam(f'set{rx_index}')

                   rsrp = np.mean(self.record_nonzero_kpi_data(num_capture=1)[0])

                   buffer_rx_rsrp[rx_kk] = rsrp
               self.current_rx_index = selected_rx_index[np.argmax(buffer_rx_rsrp)]
           
               # fix the optimal rx beams at UE
               self.rx_conn1.root.exposed_execute_beam(f'set{self.current_rx_index}')
               self.tx_conn2.root.exposed_execute_beam(f'set{self.current_rx_index}')
           #self.current_rsrp = np.mean(self.record_nonzero_kpi_data(num_capture=2)[0])
           #self.current_rsrp = self.tcp_server.data_queue.get()[0]
           print(f'Time for all RX beams : {(time.time()-tt)*1000} ms')
           
           
           rsrp = np.mean(self.record_nonzero_kpi_data(num_capture=1)[0])
           #rsrp = self.tcp_server.data_queue.get()[0]
           ris_rsrp[kk] = float(rsrp)
           #self.update_beam_plot(int(self.current_ris_beam))
           self.current_rsrp  = ris_rsrp[kk]
           self.update_rsrp_plot(self.current_rsrp )
           self.update_rsrp_display(self.current_rsrp ) 
           self.update_beam_display(int(self.current_ris_beam))
           self.update_beam_plot(int(self.current_ris_beam))
           self.update_rxbeam_display(int(self.current_rx_index))
           self.update_rxbeam_plot(int(self.current_rx_index))
           
           
           
           print(f'Time RIS beam {ris_index}: {(time.time()-time_1)*1000} ms')
           
           #time.sleep(.05)
           
           self.update_status_cap(f'{"."*int(kk%5)}')
           dpg.set_value(self.result_text_gnb, f"Current beam index: {self.current_ris_beam}")
        if self.gps_server8:
            pos = self.capture_position_gps()
        else:
            pos = {'Longitude':0.0,'Latitude':0.0}
        self.save_kpi_data(self.constants.counter,ris_rsrp,pos)

        # set the optimal beam
        optimal_index = range_beams[np.argmax(ris_rsrp)]
        self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('SET', optimal_index)
        self.update_rsrp_plot(self.current_rsrp )
        self.update_rsrp_display(self.current_rsrp ) 
        self.update_beam_display(int(self.current_ris_beam))
        self.update_beam_plot(int(self.current_ris_beam))
        self.update_rxbeam_display(int(self.current_rx_index))
        self.update_rxbeam_plot(int(self.current_rx_index))
        self.update_status8_beamsweeping('Beam Search Done!')
      
        return 1
    
    def get_rx_index_v1(self, matrix_rsrp):
        rx_index_list = []
        for arr_index in range(matrix_rsrp.shape[0]):
            rx_index_list.append(np.max(matrix_rsrp[arr_index,:])-np.min(matrix_rsrp[arr_index,:]))
        return np.argmax(np.array(rx_index_list))
    
    def joint_beamsweeping(self):
        range_beams = np.arange(0,int(self.constants.max_ris_beam_index)-2,int(self.constants.beam_interval))
        #range_beams = np.arange(1,44,int(self.constants.beam_interval))
        #selected_rx_index = np.arange(9,10)    
        #range_beams = np.arange(1,42,int(self.constants.beam_interval))
        #selected_rx = np.arange(3,11)    
        #selected_rx_index = np.array([8,9,10])    
        optimizer = BeamIndexOptimizer2(max_ris_index=self.constants.max_ris_beam_index, max_rx_index=6, current_ris_index=int(self.current_ris_beam), current_rx_index=int(self.current_rx_index), num_index_interval=2)
        selected_rx = optimizer.get_rx_beam_index_range()
        #selected_rx = np.arange(3,11)  
        selected_rx = np.array([5])
        self.update_status_cap(' ')
        
       
        # Monitor RSRP:
        rx_ris_rsrp = np.zeros((len(selected_rx),len(range_beams)))
        rx_ris_dl = np.zeros((len(selected_rx),len(range_beams)))
        rx_ris_ul = np.zeros((len(selected_rx),len(range_beams)))
        for rx_kk, rx_index in enumerate(selected_rx):
            if self.ue_status:
                rx_index_return = self.rx_conn1.root.exposed_execute_beam(f'set{rx_index}')
                self.tx_conn2.root.exposed_execute_beam(f'set{rx_index}')
            else:
                rx_index_return = self.current_rx_index
            time.sleep(1)
            for kk, ris_index in enumerate(range_beams):
               time_1 = time.time()
               if self.RIS_client:
                   self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', int(ris_index))
               else:
                   self.current_ris_beam = ris_index
               print(f'Time for one RIS beam : {(time.time()-time_1)*1000} ms')
               data_record_xApp = self.record_nonzero_kpi_data(num_capture=1)
               
               
               rx_ris_rsrp[rx_kk,kk] = np.mean(data_record_xApp[0])
               #print(data_record_xApp,  data_record_xApp[0].size, data_record_xApp[0])
               if np.mean(data_record_xApp[0]) != 0.0:
                   
                   rx_ris_dl[rx_kk,kk] = np.mean(data_record_xApp[1])
                   rx_ris_ul[rx_kk,kk] = np.mean(data_record_xApp[2])
                   self.current_rx_index  = int(rx_index_return) 
                   self.current_rsrp  = rx_ris_rsrp[rx_kk,kk]
                   self.update_rsrp_plot(self.current_rsrp )
                   self.update_rsrp_display(self.current_rsrp ) 
                   self.update_beam_display(int(self.current_ris_beam))
                   self.update_beam_plot(int(self.current_ris_beam))
                   self.update_rxbeam_display(int(self.current_rx_index))
                   self.update_rxbeam_plot(int(self.current_rx_index)) 
                   dpg.set_value(self.result_text_gnb, f"Current beam index: {self.current_ris_beam}")
                   
               if int(data_record_xApp[0].size) == 0 or int(data_record_xApp[0]) == 0: 
                   #print('HERE:',data_record_xApp[0])
                   self.found = True
                   break
               else:
                   self.current_rx_index  = int(rx_index_return) 
                   self.current_rsrp  = rx_ris_rsrp[rx_kk,kk]
                   self.update_rsrp_plot(self.current_rsrp )
                   self.update_rsrp_display(self.current_rsrp ) 
                   self.update_beam_display(int(self.current_ris_beam))
                   self.update_beam_plot(int(self.current_ris_beam))
                   self.update_rxbeam_display(int(self.current_rx_index))
                   self.update_rxbeam_plot(int(self.current_rx_index)) 
                   dpg.set_value(self.result_text_gnb, f"Current beam index: {self.current_ris_beam}")
                   
            if self.found:
                break
                           
        print(f'Time RIS beam {ris_index}: {(time.time()-time_1)*1000} ms')
     
        
            
        #self.save_kpi_data(self.counter,ris_rsrp,pos)
        rx_best_index,worse_rx_index = self.get_rx_index(rx_ris_rsrp)
        self.current_rx_index = selected_rx[rx_best_index]
        # fix the optimal rx beams at UE
        self.rx_conn1.root.exposed_execute_beam(f'set{self.current_rx_index}')
        self.tx_conn2.root.exposed_execute_beam(f'set{self.current_rx_index}')
        time.sleep(1)
        
       # np.argmax(rx_ris_rsrp[rx_best_index,:])

        # set the optimal beam
        optimal_index = range_beams[np.argmax(rx_ris_rsrp[rx_best_index,:])]
        non_optimal = range_beams[np.argmin(rx_ris_rsrp[worse_rx_index,:])]
        if self.RIS_client:
            self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('SET', optimal_index)
        self.update_rsrp_plot(self.current_rsrp )
        self.update_rsrp_display(self.current_rsrp ) 
        self.update_beam_display(int(self.current_ris_beam))
        self.update_beam_plot(int(self.current_ris_beam))
        self.update_rxbeam_display(int(self.current_rx_index))
        self.update_rxbeam_plot(int(self.current_rx_index))
        self.update_status_beamsweeping('Beam Search Done!')
        output_data =  {'optimal_ris_index':optimal_index,'optimal_rx_index':self.current_rx_index,'non_optimal_ris_index':non_optimal,'non_optimal_rx_index':selected_rx[worse_rx_index],'rx_beam_indices':selected_rx,'ris_beam_indices':range_beams,'RSRP':rx_ris_rsrp,'DL_TRU':rx_ris_dl,'UL_TRU':rx_ris_ul}
        self.bestRSRP = self.current_rsrp
        return output_data
    
    def get_rx_index(self, matrix_rsrp):
        rx_index_list = []
        rx_non_optimal = []
        for arr_index in range(matrix_rsrp.shape[0]):
            #rx_index_list.append(np.max(matrix_rsrp[arr_index,:])-np.min(matrix_rsrp[arr_index,:]))
            rx_index_list.append(np.max(matrix_rsrp[arr_index,:]))
            rx_non_optimal.append(np.min(matrix_rsrp[arr_index,:]))
        return np.argmax(np.array(rx_index_list)),np.argmin(np.array(rx_non_optimal))
# %% ALGORITHMS FUNCTIONS
    def joint_bs_ris_with_mobility(self, current_ris_index, current_rx_index):
      
        self.update_status_cap(' ')
        # at current RIS beam, perform RX beamsweep
        #selected_rx_index = np.array([4,6]) #Demo
        
        #selected_rx_index = np.array([current_rx_index])
        optimizer = BeamIndexOptimizer2(max_ris_index=self.constants.max_ris_beam_index, max_rx_index=10, current_ris_index=current_ris_index, current_rx_index=current_rx_index, num_index_interval=4)
        
        #selected_rx_index = np.array([9,10])
        range_beams = optimizer.get_ris_beam_index_range()
        selected_rx_index = optimizer.get_rx_beam_index_range()
        #selected_rx_index = np.array([10])
        
        rx_rsrp_current = self.current_rsrp
        print(':::::::::::::::')
     
        # Search neigboring RIS beams
        time_1 = time.time()
        ris_rsrp = np.zeros((1,len(range_beams)))
        ris_dl = np.zeros((1,len(range_beams)))
        ris_ul = np.zeros((1,len(range_beams)))
        for kk, ris_index in enumerate(range_beams):
           #
           if self.RIS_client:
               self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', int(ris_index))
           else:
              self.current_ris_beam = 0 
              time.sleep(0.015)
           xapp_record = self.record_nonzero_kpi_data(num_capture=1)
           #rsrp = self.tcp_server.data_queue.get()[0]
           ris_rsrp[0,kk] = float(np.mean(xapp_record[0]))
           ris_dl[0,kk] = float(np.mean(xapp_record[1]))
           ris_ul[0,kk] = float(np.mean(xapp_record[2]))
           
           #self.update_beam_plot(int(self.current_ris_beam))
           self.current_rsrp  = ris_rsrp[0,kk] 
        # set the optimal beam
        optimal_index = range_beams[np.argmax(ris_rsrp[0,:])]
        #optimal_index = 150
        #print(ris_rsrp)
        if self.RIS_client:
            self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('SET', optimal_index)
        else:
            time.sleep(0.015)
            
        #print('Here')  
        
            
           
               
            #    #self.update_status_cap(f'{"."*int(kk%5)}')
            #    dpg.set_value(self.result_text_gnb, f"Current beam index: {self.current_ris_beam}")
            # print(f'Time RIS beam sweep: {(time.time()-time_1)*1000} ms')
        
        
        self.latency = time.time()-time_1
        
        '''
        '''
        self.gps_server = False
        
        
        if self.gps_server:
            pos = self.capture_position_gps()
        else:
            pos = {'gps_utc':None, 'Longitude':0.0,'Latitude':0.0}
        
        
        #selected_rx_index = np.array([5,10])
        # selected_rx_index = np.array([current_rx_index-1])
        # xapp_record = self.record_nonzero_kpi_data(num_capture=1) 
        # myrsrp= float(np.mean(xapp_record[0]))
        print(f'RIS beam range: {range_beams} ----------')
        
        if self.mycounter%50 == 0:
            if self.robot_server:
                status_robot = dpg.get_value(self.robot_stop)
                self.current_dir = 1
                if status_robot == 0:
                    tt_now = time.time()-self.check_time
                    if tt_now> 1:
                        tt_now = 1.5
                    else:
                        tt_now = tt_now
                    data = {'status':False, "key": np.round((tt_now),5),'dir':str(self.current_dir)}
                else:
                    data = {'status':False, "key": np.round((time.time()-self.check_time),5),'dir':str(self.current_dir)}
                self.redis_client.lpush("queue_name", json.dumps(data))
            # time.sleep(3.5)
            
            rx_rsrp = np.zeros((1,len(selected_rx_index)))
            
            for rx_kk, rx_index in enumerate(selected_rx_index):
                #self.send_command_ue(f'SET{rx_index}')
                idx_rx = self.rx_conn1.root.exposed_execute_beam(f'set{rx_index}')
                idx_tx = self.tx_conn2.root.exposed_execute_beam(f'set{rx_index}')
                print(f'Index RX: {idx_rx}, {idx_tx}------------------------')
                time.sleep(1)
                
                xapp_record = self.record_nonzero_kpi_data(num_capture=1)
                #rsrp = self.tcp_server.data_queue.get()[0]
                rx_rsrp[0,rx_kk] = float(np.mean(xapp_record[0]))
            #rx_best_index = self.get_rx_index(rx_rsrp)
            
            
            rx_best_index = np.argmax(rx_rsrp[0,:])
            print(selected_rx_index)
            print('here 2',rx_best_index, rx_rsrp)
            self.current_rx_index = selected_rx_index[rx_best_index]
            
            #self.current_rx_index  = self.current_rx_index+1
            #self.send_command_ue(f'SET{self.current_rx_index}')
            # fix the optimal rx beams at UE
            _ = self.rx_conn1.root.exposed_execute_beam(f'set{self.current_rx_index}')
            _ = self.tx_conn2.root.exposed_execute_beam(f'set{self.current_rx_index}')  
            time.sleep(0.5)
        
        # self.current_rsrp  = float(np.mean(self.record_nonzero_kpi_data(num_capture=1)[0]))
        # self.update_rsrp_plot(self.current_rsrp )
        # self.update_rsrp_display(self.current_rsrp ) 
        # self.update_beam_display(int(self.current_ris_beam))
        # self.update_beam_plot(int(self.current_ris_beam))
        # self.update_rxbeam_display(int(self.current_rx_index))
        # self.update_rxbeam_plot(int(self.current_rx_index))
        # self.update_status_beamsweeping('Beam Search Done!')
        data_dict = {'RSRP':ris_rsrp,'DLTH':ris_dl,'ULTH':ris_ul,'pos':pos, 'latency':self.latency,'RIS_index':self.current_ris_beam, 'RX_index':self.current_rx_index}  
    
        return data_dict
    
    def mobility_beam_sweeping(self, current_ris_beam, current_rx_beam):
        optimizer = BeamIndexOptimizer(max_ris_index=22, max_rx_index=10, current_ris_index=current_ris_beam, current_rx_index=current_rx_beam, num_index_interval=1)
        range_rx = optimizer.get_rx_beam_index_range()
        range_ris = optimizer.get_ris_beam_index_range()
        #range_rx = np.arange(4,7 )
        #range_ris = np.arange(8,11)
        rsrp_buffer_temp = np.zeros((range_rx.shape[0],range_ris.shape[0]))
        for rx_kk, rx_index in enumerate(range_rx):
            self.rx_conn1.root.exposed_execute_beam(f'set{rx_index}')
            self.tx_conn2.root.exposed_execute_beam(f'set{rx_index}')
            # self.ue_udp_client.sendto(f'SET{rx_index}'.encode(),self.udp_server_address)
            # self.ue_udp_client.recvfrom(1024) # or sleep
            for ris_kk, ris_index in enumerate(range_ris):
                _ = self.gnb_rx_conn.send_ris_ACK('RIS', int(ris_index))
                rsrp = np.mean(self.record_nonzero_kpi_data(num_capture=1)[0])
                rsrp_buffer_temp[rx_kk,ris_kk] = rsrp
        optimal_rx_beam_index = self.get_optimal_rx_index(rsrp_buffer_temp)
        optimal_ris_beam_index = np.argmax(rsrp_buffer_temp[optimal_rx_beam_index,:])
        current_ris_beam, current_rx_beam= range_ris[optimal_ris_beam_index],range_rx[optimal_rx_beam_index]
        
        print(rsrp_buffer_temp.shape,rsrp_buffer_temp, current_rx_beam, current_ris_beam )
        
        self.rx_conn1.root.exposed_execute_beam(f'set{current_rx_beam}')
        self.tx_conn2.root.exposed_execute_beam(f'set{current_rx_beam}')
        
        self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', current_ris_beam)
        
        # self.ue_udp_client.sendto(f'SET{current_rx_index}'.encode(),self.udp_server_address)
        # self.ue_udp_client.recvfrom(1024) # or sleep
        self.current_rx_index = int(self.rx_conn1.root.exposed_execute_get_beam())
        
        return 1  
    def find_max_index(self, arr):
        max_index = np.unravel_index(np.argmax(arr, axis=None), arr.shape)
        return max_index
    
    def get_optimal_rx_index(self, arr):
        rx_list = []
        for rx in range(arr.shape[0]):
            rx_list.append(np.max(arr[rx,:]))
        return np.argmax(np.array(rx_list))
        
    def capture_position_gps(self):
        if self.gps_server:
            gps_values = self.gps_client.send_gps_ACK('GPS', 0)
            self.update_pos_cap(f'GPS Location {(gps_values["Longitude"]):.4f}, {(gps_values["Latitude"]):.4f}')
        return gps_values
       
# %% DATA COLLECTION
    def capture_data_sample(self):
        data_dict = self.joint_beamsweeping()
        if self.data_collection:
            # Record data
            instance_i = self.constants.run_term # change if you want to loop
            self.save_captured_ris_power('xApp','with_RIS',instance_i,data_dict)
            
            
            # set the current ris beam
            self.current_ris_beam = self.gnb_rx_conn.send_ris_ACK('RIS', int(data_dict['optimal_ris_index']))
            
            
            # # Record from Quectel
            # kpis = self.UE_client.send_quectel_ACK('KPI',0)
            # received_dict = json.loads(kpis)
            # self.save_captured_ris_power('quectel','with_RIS',instance_i,received_dict)
            
            # # Send codeword to turn off RIS elements
            # self.rx_conn1.root.exposed_execute_beam(f'set{int(data_dict["non_optimal_rx_index"])}')
            # self.tx_conn2.root.exposed_execute_beam(f'set{int(data_dict["non_optimal_rx_index"])}')
            # self.gnb_rx_conn.send_ris_ACK('RIS', int(data_dict['non_optimal_ris_index']))
            # kpis = self.UE_client.send_quectel_ACK('KPI',0)
            # received_dict = json.loads(kpis)
            # self.save_captured_ris_power('quectel','without_RIS',instance_i,received_dict)
            print('Quetel -----------------DONE---------------')
            
            
        return 1
    def save_captured_ris_power(self,type_mode,state_ris, instance,data):
        
        if 'quectel' in type_mode:
            self.quectel_coverage = f'./{self.data_coverage}/Quectel_Datasets/'
            if not os.path.exists(self.quectel_coverage):
                os.makedirs(self.quectel_coverage)
                
                
            self.folder_pos = f'./{self.quectel_coverage}/{state_ris}_Position_xyz/'
            self.folder_rsrp = f'./{self.quectel_coverage}/{state_ris}_rsrp/'
            self.folder_rsrq = f'./{self.quectel_coverage}/{state_ris}_rsrq/'
            self.folder_sinr = f'./{ self.quectel_coverage}/{state_ris}_sinr/'
            
            for dir_list in [self.folder_pos, self.folder_rsrp, self.folder_rsrq,self.folder_sinr]:
                if not os.path.exists(dir_list):
                    os.makedirs(dir_list)
            # Generate and save .npy files in the folder
            pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H-%M-%S-%f_%Z_%Y")
            file_path_rsrp = os.path.join(self.folder_rsrp, f"rsrp_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
            file_path_rsrq = os.path.join(self.folder_rsrq, f"rsrq_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
            file_path_sinr = os.path.join(self.folder_sinr, f"sinr_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
            file_path_pos = os.path.join(self.folder_pos,f"position_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
        
                
            #rsrps,dl_tr, ul_tr = data['RSRP'], data['DL_TRU'], data['UL_TRU']
            
            # Save the data as a .npy file
            np.save(file_path_rsrp, data['RSRP'])
            np.save(file_path_rsrq, data['RSRQ'])
            np.save(file_path_sinr, data['SINR'])
            
        else:
            self.xapp_coverage = f'./{self.data_coverage}/xApp_Datasets/'
            if not os.path.exists(self.xapp_coverage):
                os.makedirs(self.xapp_coverage)
                
            self.folder_pos = f'./{self.xapp_coverage}/{state_ris}_Position_xyz/'
            self.folder_rsrp = f'./{self.xapp_coverage}/{state_ris}_rsrp/'
            self.folder_tru = f'./{self.xapp_coverage}/{state_ris}_throughput/'
            
            
            for dir_list in [self.folder_pos, self.folder_rsrp,self.folder_tru]:
                if not os.path.exists(dir_list):
                    os.makedirs(dir_list)
            
        
            # Generate and save .npy files in the folder
            pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H-%M-%S-%f_%Z_%Y")
            file_path_rsrp = os.path.join(self.folder_rsrp, f"rsrp_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
            file_path_tru = os.path.join(self.folder_tru, f"dl_ul_throughput_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
            file_path_pos = os.path.join(self.folder_pos,f"position_run_{self.constants.run_term}_{instance}_{pc_utc_time}.npy")
            print(f'my data:{data}')
            # Save the data as a .npy file
            np.save(file_path_rsrp, data['RSRP'])
            np.save(file_path_tru, np.hstack((data['DL_TRU'], data['UL_TRU'])))
            
        if self.gps_server:
            pos = self.capture_position_gps()
            np.save(file_path_pos, np.array((pos['Longitude'],pos['Latitude'])))  
        elif self.position_obj:
            #pos = self.read_position()
            position_buffer = np.zeros((1,3))
            for jj in range(position_buffer.shape[0]):
                pos = self.read_position_v1()
                position_buffer[jj,:] = pos
            np.save(file_path_pos,position_buffer)  
        else:
            pos = {'Longitude':0.0,'Latitude':0.0}
            np.save(file_path_pos, np.array((pos['Longitude'],pos['Latitude']))) 
        return 1
    
    
    
    
    
    def run(self):
        dpg.maximize_viewport()
        dpg.start_dearpygui()
        # Turn off auto rendering
        dpg.configure_app(manual_callback_management=True)
        dpg.destroy_context()
    # def run(self, target_fps=30):
    #     dpg.configure_app(manual_callback_management=True)  # Disable auto frame rendering
    #     dpg.maximize_viewport()
        
    #     frame_interval = 1.0 / target_fps
    #     last_render = time.time()
    
    #     while dpg.is_dearpygui_running():
    #         now = time.time()
    #         if now - last_render >= frame_interval:
    #             dpg.render_dearpygui_frame()
    #             last_render = now

    #     # Optionally do any non-GUI processing here (e.g., data reading, logic)


# Run the GUI application
if __name__ == "__main__":
    app = TCPClientGUI()
    app.run()
