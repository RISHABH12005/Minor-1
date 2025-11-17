# robot_controller.py
import cv2
import numpy as np
import threading
import time
from picamera2 import Picamera2
from brickpi3 import BrickPi3


class RobotController:

    def __init__(self, auto_timeout=30):

        # ---------------- GLOBAL STATES ----------------
        self.manual_mode = False
        self.manual_last_time = time.time()
        self.auto_timeout = auto_timeout

        # Shared detection state
        self.center_x = None
        self.last_radius = 0
        self.lock = threading.Lock()

        # Autonomous tuning
        self.FRAME_W = 320
        self.CENTER = self.FRAME_W // 2

        self.FORWARD_SPEED = 260
        self.REVERSE_SPEED = 300
        self.ROTATE_LIMIT = 320

        self.KP = 0.32
        self.KD = 0.18
        self.last_error = 0

        self.RADIUS_FULL = 130
        self.RADIUS_NEAR = 95
        self.RADIUS_FAR = 70

        self.CENTER_TOL = 30

        # ---------------- MOTORS ----------------
        self.BP = BrickPi3()
        self.LEFT = self.BP.PORT_D
        self.RIGHT = self.BP.PORT_C

        self.DEFAULT_SPEED = 400

        # Flags & Threads
        self.threads_running = False

    # =====================================================
    #                     MOTOR HELPERS
    # =====================================================
    def auto_set(self, left, right):
        self.BP.set_motor_dps(self.LEFT, left)
        self.BP.set_motor_dps(self.RIGHT, right)

    def auto_stop(self):
        self.BP.set_motor_power(self.LEFT, 0)
        self.BP.set_motor_power(self.RIGHT, 0)

    def forward(self, speed=None):
        if speed is None: speed = self.DEFAULT_SPEED
        self.BP.set_motor_dps(self.LEFT, speed)
        self.BP.set_motor_dps(self.RIGHT, speed)

    def backward(self, speed=None):
        if speed is None: speed = self.DEFAULT_SPEED
        self.BP.set_motor_dps(self.LEFT, -speed)
        self.BP.set_motor_dps(self.RIGHT, -speed)

    def rotate_left(self, speed=None):
        if speed is None: speed = self.DEFAULT_SPEED
        self.BP.set_motor_dps(self.LEFT, -speed)
        self.BP.set_motor_dps(self.RIGHT, speed)

    def rotate_right(self, speed=None):
        if speed is None: speed = self.DEFAULT_SPEED
        self.BP.set_motor_dps(self.LEFT, speed)
        self.BP.set_motor_dps(self.RIGHT, -speed)

    def stop_manual(self):
        self.BP.set_motor_power(self.LEFT, 0)
        self.BP.set_motor_power(self.RIGHT, 0)

    # =====================================================
    #                   CAMERA THREAD
    # =====================================================
    def camera_thread(self):
        pic = Picamera2()
        pic.configure(picap_config := pic.create_preview_configuration(
            main={"format": "RGB888", "size": (320, 320)}
        ))
        pic.start()

        kernel = np.ones((5, 5), np.uint8)
        LOWER = np.array([35, 70, 60])
        UPPER = np.array([90, 255, 255])

        while self.threads_running:
            frame = pic.capture_array()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            mask = cv2.inRange(hsv, LOWER, UPPER)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            cx, radius = None, 0

            if cnts:
                c = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(c) > 300:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                    (_, _), radius = cv2.minEnclosingCircle(c)

            with self.lock:
                self.center_x = cx
                self.last_radius = radius

            time.sleep(0.01)

        pic.stop()

    # =====================================================
    #              AUTONOMOUS CONTROL THREAD
    # =====================================================
    def motor_thread(self):
        while self.threads_running:

            # Manual override active
            if self.manual_mode:
                if time.time() - self.manual_last_time > self.auto_timeout:
                    self.manual_mode = False
                else:
                    time.sleep(0.01)
                    continue

            with self.lock:
                cx = self.center_x
                radius = self.last_radius

            if cx is None:
                self.auto_stop()
                continue

            if radius > self.RADIUS_FULL:
                self.auto_set(-self.REVERSE_SPEED, -self.REVERSE_SPEED)
                continue

            if self.RADIUS_NEAR < radius <= self.RADIUS_FULL:
                self.auto_stop()
                continue

            if radius < self.RADIUS_FAR:
                self.auto_set(self.FORWARD_SPEED, self.FORWARD_SPEED)
                continue

            # PID rotation
            error = cx - self.CENTER
            derivative = error - self.last_error
            self.last_error = error

            rotation = self.KP * error + self.KD * derivative
            rotation = np.clip(rotation, -self.ROTATE_LIMIT, self.ROTATE_LIMIT)

            if abs(error) < self.CENTER_TOL:
                self.auto_set(self.FORWARD_SPEED, self.FORWARD_SPEED)
                continue

            self.auto_set(-rotation, rotation)

    # =====================================================
    #               MODE MANAGEMENT
    # =====================================================
    def start_autonomous(self):
        self.manual_mode = False

    def start_manual(self):
        self.manual_mode = True
        self.manual_last_time = time.time()

    # =====================================================
    #               THREAD CONTROL
    # =====================================================
    def start(self):
        if self.threads_running:
            return

        self.threads_running = True

        self.t1 = threading.Thread(target=self.camera_thread, daemon=True)
        self.t2 = threading.Thread(target=self.motor_thread, daemon=True)

        self.t1.start()
        self.t2.start()

    def stop(self):
        self.threads_running = False
        self.auto_stop()
        self.stop_manual()
        self.BP.reset_all()
