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
import cv2

CAMERA_FEED_URL = f"https://49ecf63d00b1.ngrok-free.app/video_feed"
MOTOR_API_BASE = f"https://49ecf63d00b1.ngrok-free.app/manual"
ULTRASONIC_API = "https://49ecf63d00b1.ngrok-free.app/sensor"

class RatioFrame(ttk.Frame):
    def __init__(self, master, ratio, **kwargs):
        super().__init__(master, **kwargs)
        self.ratio = float(ratio)
        self.bind('<Configure>', self._on_resize)
        self.content = None

    def _on_resize(self, event):
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()

        if master_width <= 1 or master_height <= 1:
            return

        if (master_width / master_height) > self.ratio:
            new_height = master_height
            new_width = int(self.ratio * new_height)
        else:
            new_width = master_width
            new_height = int(new_width / self.ratio)

        self.place(x=master_width // 2, y=master_height // 2,
                   width=new_width, height=new_height,
                   anchor="center")

    def set_content(self, widget):
        for child in self.winfo_children():
            try:
                child.pack_forget()
            except Exception:
                pass
            try:
                child.grid_forget()
            except Exception:
                pass

        self.content = widget
        widget.master = self
        widget.pack(fill="both", expand=True)

class RobotDashboard:
    def __init__(self, root):
        self.root = root
        self.style = tb.Style("cosmo")
        self.root.title("IIMR Robot Dashboard")
        self.root.geometry("1100x750")

        self.showing = "image"
        self.camera_running = False
        self.stream_response = None
        self.camera_thread = None
        self.camera_update_lock = threading.Lock()
        self.battery_level = 100
        self.ultrasonic_job = None
        self.x_data = list(range(20))
        self.y_data = [random.randint(2, 20) for _ in range(20)]
        self.figure = None
        self.canvas = None

        self._create_header()
        self._create_main_content()
        self._create_bottom_panel()

        self.robot_image_path = "robot.png"

        self.root.after(100, self._show_robot_image)
        self.root.after(100, self._update_battery)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _color(self, name, default="#DDDDDD"):
        try:
            colors = getattr(self.style, "colors", None)
            if colors and hasattr(colors, "get"):
                c = colors.get(name)
                if c:
                    return c
        except Exception:
            pass
        return default

    def send_motor_command(self, command):
        url = f"{MOTOR_API_BASE}/{command}"
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code != 200:
                messagebox.showwarning("Motor API Warning",
                                       f"Motor server returned status {resp.status_code} for '{command}'")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Motor Control Error",
                                 f"Could not send '{command}' to motor server.\n\n{e}")

    def _create_header(self):
        header = ttk.Frame(self.root, bootstyle="primary")
        header.pack(side="top", fill="x", ipady=10)
        project_label = ttk.Label(header, text="IIMR Robot Dashboard",
                                  font=("Helvetica", 20, "bold"), bootstyle="inverse-primary")
        project_label.pack(side="left", padx=20)

    def _create_main_content(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side="top", fill="both", expand=True)

        self.sidebar = ttk.Frame(main_frame, width=250, bootstyle="light")
        self.sidebar.pack(side="left", fill="y", padx=(10, 0), pady=(10, 0))

        ttk.Label(self.sidebar, text="VIEWS", font=("Helvetica", 12, "bold"), anchor="center").pack(pady=(20, 5), fill="x")
        self.cam_btn = ttk.Button(self.sidebar, text="Camera Feed", command=self._on_camera_click, bootstyle="info-outline")
        self.cam_btn.pack(pady=5, padx=10, fill="x")
        self.ultra_btn = ttk.Button(self.sidebar, text="Ultrasonic Sensor Graph", command=self._on_ultrasonic_click, bootstyle="info-outline")
        self.ultra_btn.pack(pady=5, padx=10, fill="x")
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", pady=15, padx=10)
        ttk.Label(self.sidebar, text="CONTROL TOGGLE", font=("Helvetica", 12, "bold"), anchor="center").pack(pady=(0, 5), fill="x")
        self.camera_toggle_btn = ttk.Button(self.sidebar, text="Start Camera", command=self._toggle_camera_feed, bootstyle="success")
        self.camera_toggle_btn.pack(pady=10, padx=10, fill="x")
        ttk.Frame(self.sidebar).pack(expand=True)
        exit_btn = ttk.Button(self.sidebar, text="Exit Dashboard", command=self._on_closing, bootstyle="danger")
        exit_btn.pack(side="bottom", pady=20, padx=10, fill="x")

        self.display_container = ttk.Frame(main_frame, bootstyle="secondary")
        self.display_container.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.ratio_frame = RatioFrame(self.display_container, ratio=16/9)
        self.ratio_frame.pack(fill="both", expand=True)

        self._create_display_widgets()

    def _create_display_widgets(self):
        self.image_label = ttk.Label(self.ratio_frame, background="black")
        self.ultrasonic_frame = ttk.Frame(self.ratio_frame, padding=10)
        self.split_frame = ttk.Frame(self.ratio_frame)
        self.split_frame.grid_rowconfigure(0, weight=1)
        self.split_frame.grid_columnconfigure(0, weight=1, uniform="split")
        self.split_frame.grid_columnconfigure(1, weight=1, uniform="split")

        self.split_left_frame = ttk.Frame(self.split_frame, padding=5, bootstyle="light")
        self.split_left_frame.grid(row=0, column=0, sticky="nsew")
        self.split_right_frame = ttk.Frame(self.split_frame, padding=5, bootstyle="light")
        self.split_right_frame.grid(row=0, column=1, sticky="nsew")

        self.ultrasonic_canvas_frame = ttk.Frame(self.split_left_frame)
        self.ultrasonic_canvas_frame.pack(expand=True, fill="both")

        self.camera_label = ttk.Label(self.split_right_frame, background="black")
        self.camera_label.pack(expand=True, fill="both")

        self._hide_all_display_widgets()

    def _hide_all_display_widgets(self):
        pass

    def _create_bottom_panel(self):
        bottom = ttk.Frame(self.root, bootstyle="default")
        bottom.pack(side="bottom", fill="x", pady=5)
        bottom_inner = ttk.Frame(bottom)
        bottom_inner.pack(fill="x", padx=10, pady=10)
        bottom_inner.grid_columnconfigure(0, weight=1)
        bottom_inner.grid_columnconfigure(1, weight=1)
        bottom_inner.grid_columnconfigure(2, weight=1)

        prop_frame = ttk.LabelFrame(bottom_inner, text="Status", padding=10, bootstyle="info")
        prop_frame.grid(row=0, column=0, padx=10, sticky="nwe")
        self.battery_label = ttk.Label(prop_frame, text=f"Battery: {self.battery_level}%",
                                       font=("Helvetica", 11, "bold"), bootstyle="success")
        self.battery_label.pack(pady=(0, 5))
        self.battery_bar = ttk.Progressbar(prop_frame, length=150, bootstyle="success-striped", mode="determinate")
        self.battery_bar.pack(pady=5, fill="x")
        self.battery_bar["value"] = self.battery_level
        self.start_time = time.strftime("%H:%M:%S")
        start_label = ttk.Label(prop_frame, text=f"Started: {self.start_time}", bootstyle="secondary")
        start_label.pack(pady=5)
        prop_btn = ttk.Button(prop_frame, text="View Robot Specs", bootstyle="outline-primary")
        prop_btn.pack(pady=(10, 0), fill="x")

        control_frame = ttk.LabelFrame(bottom_inner, text="Manual Control", padding=10, bootstyle="primary")
        control_frame.grid(row=0, column=1, padx=10, sticky="nwe")
        controls_grid = ttk.Frame(control_frame)
        controls_grid.pack(expand=True)
        up_btn = ttk.Button(controls_grid, text="↑ Forward", bootstyle="primary-outline", command=lambda: self.send_motor_command("forward"))
        up_btn.grid(row=0, column=1, padx=5, pady=5)
        left_btn = ttk.Button(controls_grid, text="← Left", bootstyle="primary-outline", command=lambda: self.send_motor_command("left"))
        left_btn.grid(row=1, column=0, padx=5, pady=5)
        start_btn = ttk.Button(controls_grid, text="STOP", bootstyle="danger-outline", command=lambda: self.send_motor_command("stop"))
        start_btn.grid(row=1, column=1, padx=5, pady=5)
        right_btn = ttk.Button(controls_grid, text="Right →", bootstyle="primary-outline", command=lambda: self.send_motor_command("right"))
        right_btn.grid(row=1, column=2, padx=5, pady=5)
        down_btn = ttk.Button(controls_grid, text="↓ Backward", bootstyle="primary-outline", command=lambda: self.send_motor_command("backward"))
        down_btn.grid(row=2, column=1, padx=5, pady=5)

        action_frame = ttk.LabelFrame(bottom_inner, text="Quick Actions", padding=10, bootstyle="success")
        action_frame.grid(row=0, column=2, padx=10, sticky="nwe")
        action1 = ttk.Button(action_frame, text="Start Routine Patrol", bootstyle="success")
        action1.pack(pady=5, fill="x")
        action2 = ttk.Button(action_frame, text="Return to Base", bootstyle="warning")
        action2.pack(pady=5, fill="x")

    def _show_robot_image(self, path=None):
        image_path = path if path else self.robot_image_path

        self._stop_ultrasonic()
        self._stop_camera()
        self.showing = "image"

        self.ratio_frame.set_content(self.image_label)

        self.cam_btn.config(bootstyle="info-outline")
        self.ultra_btn.config(bootstyle="info-outline")
        self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success")

        self.image_label.unbind('<Configure>')
        self.image_label.bind('<Configure>',
                               lambda e: self._update_image_on_resize(e, image_path, self.image_label))

        self.root.after(100, lambda: self._update_image_on_resize(None, image_path, self.image_label))

    def _update_image_on_resize(self, event, path, label):
        try:
            self.root.update_idletasks()
        except Exception:
            pass

        w = label.winfo_width()
        h = label.winfo_height()
        target_w = max(50, w)
        target_h = max(50, h)

        pil = None
        try:
            pil = Image.open(path)
            pil = pil.convert("RGB")
            pil = pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
        except Exception:
            dummy_w = target_w
            dummy_h = target_h

            bg_color = self._color("secondary", default="#DDDDDD")
            pil = Image.new("RGB", (dummy_w, dummy_h), color=bg_color)
            draw = ImageDraw.Draw(pil)

            try:
                font = ImageFont.truetype("arial.ttf", 28)
            except Exception:
                font = ImageFont.load_default()

            text = "ROBOT OFFLINE\n(No 'robot.png' found)"

            try:
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            except Exception:
                text_width, text_height = draw.textsize(text, font=font)

            text_x = (dummy_w - text_width) // 2
            text_y = (dummy_h - text_height) // 2
            draw.multiline_text((text_x, text_y), text, fill="black", font=font, align="center")

        try:
            imgtk = ImageTk.PhotoImage(pil)
            label.imgtk = imgtk
            label.configure(image=imgtk, anchor="center")
        except Exception as e:
            try:
                label.configure(text="Unable to render image.", image="", anchor="center")
            except Exception:
                pass

    def _on_camera_click(self):
        self._stop_ultrasonic()
        self.showing = "camera"

        self.ratio_frame.set_content(self.image_label)
        self.image_label.unbind('<Configure>')

        self.cam_btn.config(bootstyle="info")
        self.ultra_btn.config(bootstyle="info-outline")
        self.camera_toggle_btn.configure(text="Stop Camera", bootstyle="danger")

        self._start_camera_feed()

    def _camera_loop(self):
        try:
            with self.camera_update_lock:
                self.stream_response = requests.get(CAMERA_FEED_URL, stream=True, timeout=5)
                self.stream_response.raise_for_status()

            bytes_buffer = b''
            for chunk in self.stream_response.iter_content(chunk_size=1024):
                if not self.camera_running:
                    break
                bytes_buffer += chunk

                a = bytes_buffer.find(b'\xff\xd8')
                b = bytes_buffer.find(b'\xff\xd9')

                if a != -1 and b != -1 and b > a:
                    frame_bytes = bytes_buffer[a:b+2]
                    bytes_buffer = bytes_buffer[b+2:]

                    try:
                        img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
                    except Exception:
                        continue

                    if self.showing == "split_view":
                        display_label = self.camera_label
                        target_w = self.split_right_frame.winfo_width()
                        target_h = self.split_right_frame.winfo_height()
                    else:
                        display_label = self.image_label
                        target_w = self.ratio_frame.winfo_width()
                        target_h = self.ratio_frame.winfo_height()

                    target_w = max(1, target_w)
                    target_h = max(1, target_h)

                    img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                    imgtk = ImageTk.PhotoImage(image=img)

                    def updater(imgtk=imgtk, display_label=display_label):
                        if self.camera_running:
                            display_label.imgtk = imgtk
                            display_label.configure(image=imgtk, anchor="center")

                    self.root.after(0, updater)

        except Exception:
            self.root.after(0, lambda: messagebox.showerror("Connection Error", f"Failed to connect to video stream."))
        finally:
            self._cleanup_camera()

    def _on_ultrasonic_click(self):
        self._stop_camera()
        self._stop_ultrasonic()
        self.showing = "ultrasonic"

        self.ratio_frame.set_content(self.ultrasonic_frame)

        self.cam_btn.config(bootstyle="info-outline")
        self.ultra_btn.config(bootstyle="info")
        self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success")

        self._show_ultrasonic_graph(self.ultrasonic_frame)

    def _show_ultrasonic_graph(self, parent_frame):
        for widget in parent_frame.winfo_children():
            widget.destroy()

        w = max(400, parent_frame.winfo_width())
        h = max(300, parent_frame.winfo_height())
        self.fig, self.ax = plt.subplots(figsize=(max(5, w / 100), max(4, h / 100)), facecolor=self._color("light", default="#FFFFFF"))

        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.15)
        self.ax.set_title("Ultrasonic Sensor Distance", fontsize=14, color=self._color("primary", default="#000000"))
        self.ax.set_xlabel("Time Step (s)", fontsize=10)
        self.ax.set_ylabel("Distance (cm)", fontsize=10)
        self.ax.set_ylim(0, 30)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.set_facecolor(self._color("secondary", default="#EEEEEE"))

        self.x_data = list(range(20))
        self.y_data = self.y_data if hasattr(self, "y_data") else [random.randint(2, 20) for _ in range(20)]
        line_color = self._color("success", default="#00AA00")
        self.line, = self.ax.plot(self.x_data, self.y_data,
                                  marker="o", markersize=5,
                                  color=line_color,
                                  linewidth=2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(expand=True, fill="both", padx=10, pady=10)
        self.canvas.draw()

        self.canvas_widget.bind('<Configure>', self._on_graph_resize)

        self._update_ultrasonic()

    def _on_graph_resize(self, event):
        if self.canvas and self.fig:
            w_pixels = self.canvas_widget.winfo_width()
            h_pixels = self.canvas_widget.winfo_height()
            w_inches = max(1.0, w_pixels / 100)
            h_inches = max(0.5, h_pixels / 100)
            self.fig.set_size_inches(w_inches, h_inches, forward=True)
            try:
                self.canvas.draw_idle()
            except Exception:
                pass

    def _update_ultrasonic(self):
        if self.showing not in ["ultrasonic", "split_view"]:
            return
        try:
            resp = requests.get(ULTRASONIC_API, timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                value = data.get("distance_cm", float(data.get("distance", random.randint(2, 20))))
            else:
                value = random.randint(2, 20)
        except Exception:
            value = random.randint(2, 20)

        self.y_data.pop(0)
        try:
            numeric_val = max(0.0, min(500.0, float(value)))
        except Exception:
            numeric_val = float(random.randint(2, 20))
        self.y_data.append(numeric_val)

        try:
            self.line.set_ydata(self.y_data)
            y_min = max(0, int(min(self.y_data) - 2))
            y_max = max(30, int(max(self.y_data) + 2))
            self.ax.set_ylim(y_min, y_max)
            self.canvas.draw_idle()
        except Exception:
            pass

        self.ultrasonic_job = self.root.after(1000, self._update_ultrasonic)

    def _stop_ultrasonic(self):
        if getattr(self, "ultrasonic_job", None):
            try:
                self.root.after_cancel(self.ultrasonic_job)
            except Exception:
                pass
            self.ultrasonic_job = None
        if getattr(self, "canvas", None):
            try:
                if hasattr(self, 'fig'):
                    plt.close(self.fig)
                self.canvas_widget.destroy()
            except Exception:
                pass
            self.canvas = None

    def _start_split_view(self):
        self._stop_ultrasonic()
        self._stop_camera()
        self.showing = "split_view"

        self.ratio_frame.set_content(self.split_frame)
        self.split_frame.pack(fill="both", expand=True)

        self.cam_btn.config(bootstyle="info")
        self.ultra_btn.config(bootstyle="info")
        self.camera_toggle_btn.configure(text="Stop Camera", bootstyle="danger")

        self._show_ultrasonic_graph(self.ultrasonic_canvas_frame)
        self._start_camera_feed()

    def _stop_split_view(self):
        self._stop_camera()
        self._stop_ultrasonic()
        self.showing = "ultrasonic"

        self.ratio_frame.set_content(self.ultrasonic_frame)

        self.cam_btn.config(bootstyle="info-outline")
        self.ultra_btn.config(bootstyle="info")
        self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success")

        self._show_ultrasonic_graph(self.ultrasonic_frame)

    def _start_camera_feed(self):
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
            elif self.showing == "camera":
                self._show_robot_image()
        else:
            if self.showing == "ultrasonic":
                self._start_split_view()
            else:
                self._on_camera_click()
            self.camera_toggle_btn.configure(text="Stop Camera", bootstyle="danger")

    def _stop_camera(self):
        self.camera_running = False
        if self.stream_response:
            try:
                self.stream_response.close()
            except Exception:
                pass
            self.stream_response = None
        if self.camera_thread and self.camera_thread.is_alive():
            try:
                self.camera_thread.join(timeout=0.5)
            except Exception:
                pass
            self.camera_thread = None

    def _cleanup_camera(self):
        try:
            self.root.after(0, lambda: self.camera_toggle_btn.configure(text="Start Camera", bootstyle="success"))
        except Exception:
            pass
        self.camera_running = False

        if self.showing == "camera":
            try:
                self.root.after(0, self._show_robot_image)
            except Exception:
                pass
        elif self.showing == "split_view":
            try:
                self.root.after(0, self._stop_split_view)
            except Exception:
                pass

    def _update_battery(self):
        if self.battery_level > 0:
            self.battery_level -= 1
        else:
            self.battery_level = 100
        try:
            self.battery_bar["value"] = self.battery_level
            self.battery_label.configure(text=f"Battery: {self.battery_level}%")
            style_name = "success" if self.battery_level > 60 else ("warning" if self.battery_level > 20 else "danger")
            self.battery_bar.configure(bootstyle=f"{style_name}-striped")
            self.battery_label.configure(bootstyle=style_name)
        except Exception:
            pass
        self.root.after(1000, self._update_battery)

    def _on_closing(self):
        print("Stopping all threads and exiting...")
        self._stop_camera()
        self._stop_ultrasonic()
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = RobotDashboard(root)
    root.mainloop()
