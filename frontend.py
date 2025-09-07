import tkinter as tk
from tkinter import Label, Button
from PIL import Image, ImageTk
import asyncio
import websockets
import threading
import cv2
import numpy as np

# Change this IP to your robot's IP
ROBOT_IP = "192.168.1.50"
CAMERA_WS_URL = f"ws://{ROBOT_IP}:8000/ws_cam"
ROBOT_WS_URL = f"ws://{ROBOT_IP}:8000/ws_robot"

class RobotApp:
    def __init__(self, root):
        """Initializes the main application window and its components."""
        self.root = root
        self.root.title("Robot Control & Camera Viewer")
        
        # Keep track of the robot control WebSocket connection
        self.robot_ws = None
        self.running = True

        # ---- Main Layout ----
      
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


        self.camera_frame = tk.Frame(self.main_frame, bg="black", width=640, height=360)
        self.camera_frame.pack(pady=20)   
        self.camera_frame.pack_propagate(False)

        self.video_label = Label(self.camera_frame, bg="black")
        self.video_label.pack(expand=True)


        self.controls_frame = tk.Frame(self.main_frame)
        self.controls_frame.pack(pady=10)  

        # Buttons for robot control using a grid layout
        Button(self.controls_frame, text="Up", width=10, command=lambda: self.send_command("forward")).grid(row=0, column=1, pady=5)
        Button(self.controls_frame, text="Left", width=10, command=lambda: self.send_command("left")).grid(row=1, column=0, pady=5)
        Button(self.controls_frame, text="Stop", width=10, command=lambda: self.send_command("stop")).grid(row=1, column=1, pady=5)
        Button(self.controls_frame, text="Right", width=10, command=lambda: self.send_command("right")).grid(row=1, column=2, pady=5)
        Button(self.controls_frame, text="Down", width=10, command=lambda: self.send_command("backward")).grid(row=2, column=1, pady=5)

        # ---- Start WebSocket threads ----
        # Create a new asyncio event loop for the WebSocket connections
        self.loop = asyncio.new_event_loop()
        # Start the loop in a new thread so it doesn't block the Tkinter GUI
        threading.Thread(target=self.start_async_loop, daemon=True).start()

    def start_async_loop(self):
        """Sets up the asyncio event loop and runs both WebSocket handlers concurrently."""
        asyncio.set_event_loop(self.loop)
        # Use asyncio.gather to run both connections at the same time
        self.loop.run_until_complete(asyncio.gather(
            self.ws_camera_handler(),
            self.ws_robot_handler()
        ))

    async def ws_camera_handler(self):
        """Handles the camera WebSocket connection and updates the GUI with frames."""
        while self.running:
            try:
                # Connect to the camera server
                async with websockets.connect(CAMERA_WS_URL) as websocket:
                    print("Connected to camera server.")
                    while self.running:
                        try:
                            frame_data = await websocket.recv()
                            # Convert bytes to a numpy array for OpenCV
                            np_arr = np.frombuffer(frame_data, np.uint8)
                            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                            if frame is None:
                                continue

                            # Convert OpenCV image to Tkinter-compatible format
                            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            img = Image.fromarray(cv2image)
                            imgtk = ImageTk.PhotoImage(image=img)
                            
                            # Update the label with the new frame
                            self.video_label.imgtk = imgtk
                            self.video_label.config(image=imgtk)
                        except Exception as e:
                            print(f"Error receiving frame: {e}")
                            break
            except Exception as e:
                print(f"Camera connection failed, reconnecting: {e}")
                await asyncio.sleep(3)

    async def ws_robot_handler(self):
        """Handles the robot control WebSocket connection and keeps it alive."""
        while self.running:
            try:
                # Connect to the robot control server
                async with websockets.connect(ROBOT_WS_URL) as websocket:
                    self.robot_ws = websocket
                    print("Connected to robot control server.")
                    # Keep the connection open
                    while self.running:
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"Robot connection failed, reconnecting: {e}")
                self.robot_ws = None
                await asyncio.sleep(3)
    
    def send_command(self, cmd):
        """Sends a motor command to the robot."""
        # Use run_coroutine_threadsafe to send from the Tkinter thread
        if self.robot_ws:
            asyncio.run_coroutine_threadsafe(self.robot_ws.send(cmd), self.loop)
        else:
            print("Robot not connected.")

if __name__ == "__main__":
    root = tk.Tk()
    app = RobotApp(root)
    root.mainloop()