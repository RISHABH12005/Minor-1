import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from PIL import Image, ImageTk, ImageDraw, ImageFont
import threading
import time
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests 
import io 

# --- CONFIGURATION ---
# !!! IMPORTANT: REPLACE with your robot's IP address !!!
ROBOT_IP = "192.168.1.100"  

# Set the ports based on how you run your FastAPI services
MOTOR_PORT = 8000
CAMERA_PORT = 8001 # Assuming you run the camera on a separate port 

MOTOR_URL = f"http://{ROBOT_IP}:{MOTOR_PORT}/motor/move"
CAMERA_URL = f"http://{ROBOT_IP}:{CAMERA_PORT}/video_feed" 
# ---------------------

class RobotCommunicator:
    """
    Handles sending commands to the remote robot server via HTTP.
    
    This replaces direct hardware control from the dashboard PC.
    """
    def __init__(self, motor_url):
        self.MOTOR_URL = motor_url
        print(f"Robot Communicator initialized. Target: {self.MOTOR_URL}")

    def send_command(self, command):
        """Sends the movement command via HTTP GET request in a separate thread."""
        try:
            threading.Thread(target=self._request_command, args=(command,), daemon=True).start()
        except Exception as e:
            print(f"Error starting command thread for {command}: {e}")

    def _request_command(self, command):
        try:
            # Short timeout, as motor response should be near instantaneous
            response = requests.get(f"{self.MOTOR_URL}/{command}", timeout=0.5)
            if response.status_code != 200:
                print(f"Robot command failed: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to robot server for {command}: {e}")
        except Exception as e:
            print(f"Unexpected error during command: {e}")

class RobotDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Dashboard")
        self.style = tb.Style("flatly")

        # Initialize the Robot Communicator
        self.robot_comm = RobotCommunicator(MOTOR_URL)

        # State variables
        self.showing = "image"  # "image", "camera", "ultrasonic", "split_view"
        self.camera_running = False
        self.camera_thread = None
        self.camera_update_lock = threading.Lock()
        self.battery_level = 100
        self.ultrasonic_job = None
        self.x_data = list(range(20))
        self.y_data = [random.randint(2, 20) for _ in range(20)]
        self.figure = None
        self.canvas = None
        
        # Layout
        self._create_header()
        self._create_layout()
        self._create_bottom_panel()
        self._create_display_widgets()

        # Start battery drain simulation
        self._update_battery()

        # Schedule the initial image display
        self.root.after(100, self._show_robot_image)

    # ---------------- HEADER ---------------- #
    def _create_header(self):
        header = ttk.Frame(self.root, bootstyle="dark")
        header.pack(side="top", fill="x", ipadx=10, ipady=10)
        
        project_label = ttk.Label(header, text="IIMR", font=("Helvetica", 24, "bold"))
        project_label.pack(side="right", padx=20)
        
        try:
            logo_pil = Image.new("RGB", (60, 60), color="#800000") # Placeholder logo
            self.logo_tk = ImageTk.PhotoImage(logo_pil)
            logo = ttk.Label(header, image=self.logo_tk)
            logo.pack(side="right", padx=20)
        except Exception:
            logo = ttk.Label(header, text="[Logo]", font=("Helvetica", 14))
            logo.pack(side="right", padx=20)

    # ---------------- MAIN LAYOUT ---------------- #
    def _create_layout(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side="top", fill="both", expand=True)

        sidebar = ttk.Frame(main_frame, width=200, bootstyle="secondary")
        sidebar.pack(side="left", fill="y")
        
        self.cam_btn = ttk.Button(sidebar, text="Camera", command=self._on_camera_click)
        self.cam_btn.pack(pady=10, fill="x")

        self.ultra_btn = ttk.Button(sidebar, text="Ultrasonic Sensor", command=self._on_ultrasonic_click)
        self.ultra_btn.pack(pady=10, fill="x")

        ttk.Frame(sidebar).pack(expand=True)

        exit_btn = ttk.Button(sidebar, text="Exit", command=self.root.quit, bootstyle="danger")
        exit_btn.pack(side="bottom", pady=20, fill="x")

        self.display_frame = tk.Frame(main_frame, bg="black")
        self.display_frame.pack(side="left", fill="both", expand=True)
        self.display_frame.grid_rowconfigure(0, weight=1)
        self.display_frame.grid_columnconfigure(0, weight=1)

        self.camera_toggle_btn = ttk.Button(self.display_frame, text="Start Camera",
                                            command=self._toggle_camera_feed, bootstyle="success")
        self.camera_toggle_btn.grid(row=1, column=0, pady=10, columnspan=2)

    def _create_display_widgets(self):
        self.image_label = ttk.Label(self.display_frame)
        self.image_label.grid(row=0, column=0, sticky="nsew", columnspan=2)
        
        self.ultrasonic_frame = ttk.Frame(self.display_frame)
        self.ultrasonic_frame.grid(row=0, column=0, sticky="nsew", columnspan=2)
        
        self.split_left_frame = ttk.Frame(self.display_frame)
        self.split_left_frame.grid(row=0, column=0, sticky="nsew")
        self.split_right_frame = ttk.Frame(self.display_frame)
        self.split_right_frame.grid(row=0, column=1, sticky="nsew")

        self.ultrasonic_canvas_frame = ttk.Frame(self.split_left_frame)
        self.ultrasonic_canvas_frame.pack(expand=True, fill="both")
        self.camera_label = ttk.Label(self.split_right_frame, background="black")
        self.camera_label.pack(expand=True, fill="both")

        self.display_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        self.display_frame.grid_columnconfigure(1, weight=1, uniform="group1")
        
        self._hide_all_display_widgets()

    def _hide_all_display_widgets(self):
        self.image_label.grid_remove()
        self.ultrasonic_frame.grid_remove()
        self.split_left_frame.grid_remove()
        self.split_right_frame.grid_remove()
        self.camera_toggle_btn.grid_remove()
    
    # ---------------- BOTTOM PANEL (Control Integration) ---------------- #
    def _create_bottom_panel(self):
        bottom = ttk.Frame(self.root, bootstyle="light")
        bottom.pack(side="bottom", fill="x")
        bottom_inner = ttk.Frame(bottom)
        bottom_inner.pack(anchor="center", pady=10)
        
        prop_frame = ttk.Frame(bottom_inner)
        prop_frame.grid(row=0, column=0, padx=40)
        prop_btn = ttk.Button(prop_frame, text="Properties")
        prop_btn.pack(pady=5)
        self.battery_bar = ttk.Progressbar(prop_frame, length=120, bootstyle="success-striped")
        self.battery_bar.pack(pady=5)
        self.battery_bar["value"] = self.battery_level
        self.battery_label = ttk.Label(prop_frame, text=f"Battery: {self.battery_level}%")
        self.battery_label.pack()
        self.start_time = time.strftime("%H:%M:%S")
        start_label = ttk.Label(prop_frame, text=f"Started: {self.start_time}")
        start_label.pack()
        
        # --- Robot Control Buttons ---
        control_frame = ttk.Frame(bottom_inner)
        control_frame.grid(row=0, column=1, padx=40)
        
        # UP Button -> Forward
        up_btn = ttk.Button(control_frame, text="↑", command=lambda: self.robot_comm.send_command("forward"))
        up_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # LEFT Button -> Left/Anticlockwise
        left_btn = ttk.Button(control_frame, text="←", command=lambda: self.robot_comm.send_command("left"))
        left_btn.grid(row=1, column=0, padx=5, pady=5)
        
        # START/STOP Button
        stop_btn = ttk.Button(control_frame, text="STOP", command=lambda: self.robot_comm.send_command("stop"), bootstyle="danger")
        stop_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # RIGHT Button -> Right/Clockwise
        right_btn = ttk.Button(control_frame, text="→", command=lambda: self.robot_comm.send_command("right"))
        right_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # DOWN Button -> Backward
        down_btn = ttk.Button(control_frame, text="↓", command=lambda: self.robot_comm.send_command("backward"))
        down_btn.grid(row=2, column=1, padx=5, pady=5)
        
        action_frame = ttk.Frame(bottom_inner)
        action_frame.grid(row=0, column=2, padx=40)
        # Action buttons are placeholders for complex commands
        action1 = ttk.Button(action_frame, text="Action 1", command=lambda: self.robot_comm.send_command("action1"))
        action1.pack(pady=5, fill="x")
        action2 = ttk.Button(action_frame, text="Action 2", command=lambda: self.robot_comm.send_command("action2"))
        action2.pack(pady=5, fill="x")

    # ---------------- IMAGE ---------------- #
    def _show_robot_image(self, path="robot.jpg"):
        self._stop_ultrasonic()
        self._stop_camera()
        self.showing = "image"
        self._hide_all_display_widgets()
        self.image_label.grid()
        self.camera_toggle_btn.grid(columnspan=2)
        try:
            pil = Image.open(path)
        except Exception:
            pil = Image.new("RGB", (600, 400), color="gray")
            draw = ImageDraw.Draw(pil)
            font = ImageFont.load_default()
            draw.text((10, 10), "Robot Image Not Found", fill="white", font=font)
        
        self.root.update_idletasks()
        w = self.image_label.winfo_width()
        h = self.image_label.winfo_height()
        target_w = max(1, w - 20)
        target_h = max(1, h - 20)
        
        pil.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        imgtk = ImageTk.PhotoImage(pil)
        self.image_label.imgtk = imgtk
        self.image_label.configure(image=imgtk, anchor="center")

    # ---------------- CAMERA (Integrated to use API stream) ---------------- #
    def _on_camera_click(self):
        self._stop_ultrasonic()
        self.showing = "camera"
        self._hide_all_display_widgets()
        self.image_label.grid()
        self.camera_toggle_btn.grid(columnspan=2)
        self.camera_toggle_btn.configure(text="Stop Camera", bootstyle="danger")
        self._start_camera_feed(self.image_label)

    def _camera_loop(self):
        """Streams MJPEG frames from the FastAPI endpoint."""
        try:
            # Use requests to stream the MJPEG feed from the FastAPI endpoint
            response = requests.get(CAMERA_URL, stream=True, timeout=None)
            
            if response.status_code != 200:
                print(f"Failed to connect to camera stream: {response.status_code}")
                self.root.after(0, lambda: messagebox.showerror("Camera Error", f"Failed to get camera stream from {CAMERA_URL}"))
                self.camera_running = False
                return

            boundary = b'--frame'
            bytes_data = b''
            
            # Iterate over the raw stream chunks
            for chunk in response.iter_content(chunk_size=1024):
                if not self.camera_running: 
                    break 

                bytes_data += chunk
                
                # Find the start and end of a single frame
                a = bytes_data.find(boundary)
                b = bytes_data.find(boundary, a + len(boundary))
                
                if a != -1 and b != -1:
                    # Look for the header end (which precedes the JPEG data)
                    header_end = bytes_data.find(b'\r\n\r\n', a)
                    if header_end != -1:
                        frame_data = bytes_data[header_end + 4:b]
                        bytes_data = bytes_data[b:]

                        try:
                            # Convert raw bytes to PIL Image
                            pil_img = Image.open(io.BytesIO(frame_data))
                            
                            # Determine target label and size based on current view mode
                            if self.showing == "split_view":
                                display_label = self.camera_label
                                target_w = max(1, self.split_right_frame.winfo_width())
                                target_h = max(1, self.split_right_frame.winfo_height())
                            else:
                                display_label = self.image_label
                                target_w = max(1, self.image_label.winfo_width())
                                target_h = max(1, self.image_label.winfo_height())

                            # Resize image to fit the container
                            pil_img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                            imgtk = ImageTk.PhotoImage(image=pil_img)
                            
                            # Update the GUI on the main thread
                            def updater():
                                display_label.imgtk = imgtk # Keep a reference to prevent garbage collection
                                display_label.configure(image=imgtk, anchor="center")
                            
                            self.root.after(0, updater)
                            
                        except Exception as e:
                            # This can happen if a chunk is incomplete or corrupted, often safe to ignore
                            pass
                            
        except Exception as e:
            if self.camera_running: 
                 self.root.after(0, lambda: messagebox.showerror("Camera Error", f"Connection failed to {CAMERA_URL}: {e}"))

        finally:
            self.camera_running = False
            self.root.after(0, lambda: self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success"))


    def _start_camera_feed(self, display_widget):
        self._stop_camera()
        self.camera_running = True
        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.camera_thread.start()

    def _toggle_camera_feed(self):
        if self.camera_running:
            self._stop_camera()
            self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success")
            if self.showing == "split_view":
                self._stop_split_view()
            else:
                self._show_robot_image()
        else:
            if self.showing == "ultrasonic":
                self._start_split_view()
            else:
                self._on_camera_click()
            self.camera_toggle_btn.configure(text="Stop Camera", bootstyle="danger")

    def _stop_camera(self):
        self.camera_running = False 
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=0.2) 
            self.camera_thread = None

    # ---------------- ULTRASONIC ---------------- #
    def _on_ultrasonic_click(self):
        self._stop_camera()
        self._stop_ultrasonic()
        self.showing = "ultrasonic"
        self._hide_all_display_widgets()
        self.ultrasonic_frame.grid()
        self.camera_toggle_btn.grid(columnspan=2)
        self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success")
        self._show_ultrasonic_graph(self.ultrasonic_frame)

    def _show_ultrasonic_graph(self, parent_frame):
        for widget in parent_frame.winfo_children():
            widget.destroy()
        # Use tight layout to fit in small frames
        self.fig, self.ax = plt.subplots(figsize=(5, 4), tight_layout=True) 
        self.ax.set_title("Ultrasonic Sensor Data")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Distance (cm)")
        self.ax.set_ylim(0, 30)
        self.x_data = list(range(20))
        self.y_data = [random.randint(2, 20) for _ in range(20)]
        self.line, = self.ax.plot(self.x_data, self.y_data, marker="o")
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(expand=True, fill="both")
        self.canvas.draw()
        self._update_ultrasonic()

    def _update_ultrasonic(self):
        if self.showing not in ["ultrasonic", "split_view"]: return
        
        # Simulate new data
        self.y_data.pop(0)
        self.y_data.append(random.randint(2, 20)) 
        
        self.line.set_ydata(self.y_data)
        
        # Adjust Y-axis limits dynamically
        y_min = max(0, min(self.y_data) - 2)
        y_max = max(30, max(self.y_data) + 2)
        self.ax.set_ylim(y_min, y_max)
        
        self.canvas.draw()
        self.ultrasonic_job = self.root.after(1000, self._update_ultrasonic)

    def _stop_ultrasonic(self):
        if getattr(self, "ultrasonic_job", None):
            self.root.after_cancel(self.ultrasonic_job)
            self.ultrasonic_job = None
        if self.canvas:
            try:
                self.canvas_widget.destroy()
                plt.close(self.fig)
            except Exception: pass
            self.canvas = None
    
    # ---------------- SPLIT VIEW ---------------- #
    def _start_split_view(self):
        self._stop_ultrasonic()
        self._stop_camera()
        self.showing = "split_view"
        self._hide_all_display_widgets()
        self.split_left_frame.grid(row=0, column=0, sticky="nsew")
        self.split_right_frame.grid(row=0, column=1, sticky="nsew")
        self.camera_toggle_btn.grid(row=1, column=0, pady=10, columnspan=2)
        self._show_ultrasonic_graph(self.ultrasonic_canvas_frame)
        self._start_camera_feed(self.camera_label)
        
    def _stop_split_view(self):
        self._stop_ultrasonic()
        self._stop_camera()
        self.showing = "ultrasonic"
        self._hide_all_display_widgets()
        self.ultrasonic_frame.grid()
        self.camera_toggle_btn.grid(columnspan=2)
        self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success")
        self._show_ultrasonic_graph(self.ultrasonic_frame)

    # ---------------- BATTERY ---------------- #
    def _update_battery(self):
        if self.battery_level > 0:
            self.battery_level -= 1
        else:
            self.battery_level = 100
        self.battery_bar["value"] = self.battery_level
        
        # Change color based on level
        if self.battery_level > 50:
            style = "success-striped"
        elif self.battery_level > 20:
            style = "warning-striped"
        else:
            style = "danger-striped"
        self.battery_bar.configure(bootstyle=style)

        self.battery_label.configure(text=f"Battery: {self.battery_level}%")
        self.root.after(1000, self._update_battery)
    
# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    # Ensure you have 'requests', 'ttkbootstrap', 'Pillow', and 'matplotlib' installed
    # And remember to change ROBOT_IP above!
    root = tk.Tk()
    root.geometry("1100x700")
    app = RobotDashboard(root)
    root.mainloop()