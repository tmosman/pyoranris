import torch
from ultralytics import YOLO
import cv2
import numpy as np
from collections import defaultdict
import socket
import json
import pyzed.sl as sl
from datetime import datetime, timezone
import cv2
import sys
import time


class ZED2_Obj:
    def __init__(self, fs_rate):
        self.dectector_obj = RobotTracker()
        self.zed = sl.Camera() # Create a Camera object
        self.init_params = sl.InitParameters() # Create a InitParameters object and set configuration parameters
        self.init_zed(fs_rate)
        self.image_buffer = sl.Mat()
        self.runtime_parameters = sl.RuntimeParameters()
        
        
    def init_zed(self,frame_rate):
        self.init_params.camera_resolution = sl.RESOLUTION.HD1080  # Use HD1080 video mode
        self.init_params.camera_fps = frame_rate  # Set fps at 30
        # Open the camera
        self.zed_err = self.zed.open(self.init_params)
        if self.zed_err != sl.ERROR_CODE.SUCCESS:
            sys.exit(1)
            
    def capture_image_bbox(self,iteration):
        for qq in range(iteration):
            tt = time.time()
            # Grab an image, a RuntimeParameters object must be given to grab()
            if self.zed.grab(self.runtime_parameters) == sl.ERROR_CODE.SUCCESS:
                self.zed.retrieve_image(self.image_buffer, sl.VIEW.LEFT)
                #print(f'Time Capture: {(time.time()-end1)*1000} ms' )
                # Get the timestamp at the time the image was captured
                timestamp = self.zed.get_timestamp(sl.TIME_REFERENCE.CURRENT)  
                pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H-%M-%S-%f_%Z_%Y")
                
                # print(f"Image resolution: {self.image_buffer.get_width()} x {self.image_buffer.get_height()} || "
                #       f"Image timestamp: {timestamp.get_milliseconds()}")
                #cv2.imwrite(fname + '.jpg', image.get_data())
                
            processed_frame,bbox_cord = self.dectector_obj.process_frame(self.image_buffer.get_data())
            #print(f'{(time.time()-tt)*1000} ms')
            if len(bbox_cord)>0:
                #print(f'x-center: {bbox_cord[0]/self.image_buffer.get_width()}, y-center: {bbox_cord[1]/self.image_buffer.get_height()}')
                dict_value = {'x':int(bbox_cord[0]), 'y':int(bbox_cord[1])}
            else:
                dict_value = {'x':int(0), 'y':int(0)}
            
        return dict_value
            
            
            

class RobotTracker:
    def __init__(self, confidence_threshold=0.4, max_disappeared=30*10):
        # Initialize YOLO model with GPU support
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
       
        # Load YOLO model
        self.model = YOLO('yolov9s.pt')  # or 'yolov8n.pt' for less accuracy but faster inference
        #self.model = YOLO('./ISTB4_inlab/best.pt')  # or 'yolov8n.pt' for less accuracy but faster inference
        self.model.to(self.device)
        
        # Tracking parameters
        self.confidence_threshold = confidence_threshold
        self.max_disappeared = max_disappeared
        self.next_vehicle_id = 0
        self.vehicles = {}
        self.vehicle_history = defaultdict(list)
        
        # Valid vehicle classes in YOLO v8
        self.vehicle_classes = [0, 1, 2, 5, 7]  # car, bus, truck in YOLOv8
        
    def process_frame(self, frame, target_fps=10):
        # Convert frame to RGB for YOLO
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #ii = time.time()
        # Run inference
        results = self.model(frame_rgb, verbose=False)
        #print(results)
        #print(f'Results: {(time.time()-ii)*1000} ms')
        # Process detections
        current_vehicles = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                if conf > self.confidence_threshold and cls in self.vehicle_classes:
                    # Get coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    w = x2 - x1
                    h = y2 - y1
                    #current_vehicles.append((int(x1), int(y1), int(w), int(h)))
                    x_center, y_center, w,h = box.xywh[0].cpu().numpy()
                    current_vehicles.append([x_center, y_center, w,h])
                    #print(box)
        
        if len(current_vehicles)>0:
            bbox_cord = current_vehicles[-1]
        else:
            bbox_cord = current_vehicles
        return frame,bbox_cord
        
    def send_dict_over_socket(self,dictionary, host, port):
        """
        Attempts to connect to a server and send a dictionary. Skips if the server is not active.
        """
        try:
            # Create a socket with a timeout
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)  # Set a timeout for the connection
                try:
                    # Attempt to connect to the server
                    s.connect((host, port))
                    print("Connected to the server.")
    
                    # Serialize the dictionary to a JSON string
                    serialized_dict = json.dumps(dictionary)
                    # Send the serialized data
                    s.sendall(serialized_dict.encode('utf-8'))
                    print("Data sent successfully.")
                except (socket.timeout, ConnectionRefusedError) as e:
                    # Handle connection failure
                    print(f"Server not active or connection failed: {e}")
                    # Skip sending data and continue execution
        except Exception as e:
            print(f"Unexpected error: {e}")


def test_model(frame_rgb):
    
    tracker = RobotTracker()
    process_f,coord =  tracker.process_frame(frame_rgb)
    #print(dir(tracker.model.))
    #results = tracker.model(frame_rgb, verbose=False)
    print(coord)
    
def test_script():
    camera = ZED2_Obj(fs_rate=10)
    while True:
        
        tt=time.time()
        camera.capture_image_bbox()
        print(f'{(time.time()-tt)*1000} ms')
        
    return 1

    
if __name__ == "__main__":

    # Load image
    #image_bgr = cv2.imread("test.jpg")
    #test_model(image_bgr)
    test_script()
    
   
    
