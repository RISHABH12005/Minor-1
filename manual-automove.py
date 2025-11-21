import cv2
import numpy as np
import time
import threading
from picamera2 import Picamera2
from brickpi3 import BrickPi3

# ==========================================================
#              GLOBAL MODE & TIMERS
# ==========================================================
manual_mode = False
manual_last_time = time.time()

# ==========================================================
#              SHARED VARIABLES (THREAD SAFE)
# ==========================================================
center_x = None
last_radius = 0
lock = threading.Lock()

# ==========================================================
#            CAMERA + CONTROL THRESHOLDS (TUNED)
# ==========================================================
FRAME_W = 320
CENTER = FRAME_W // 2

FORWARD_SPEED = 260
REVERSE_SPEED = 300
ROTATE_LIMIT = 320

KP = 0.32
KD = 0.18
last_error = 0

RADIUS_FULL = 130
RADIUS_NEAR = 95
RADIUS_FAR = 70

CENTER_TOL = 30

# ==========================================================
#                          MOTORS
# ==========================================================
BP = BrickPi3()
LEFT = BP.PORT_D
RIGHT = BP.PORT_C

def auto_set_motors(left, right):
    BP.set_motor_dps(LEFT, left)
    BP.set_motor_dps(RIGHT, right)

def auto_stop_motors():
    BP.set_motor_power(LEFT, 0)
    BP.set_motor_power(RIGHT, 0)

# Manual controls
C = RIGHT
D = LEFT
DEFAULT_SPEED = 400

def forward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def backward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def rotate_clockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, -speed)

def rotate_anticlockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, speed)

def stop_manual():
    BP.set_motor_power(C, 0)
    BP.set_motor_power(D, 0)


# ==========================================================
#                   CAMERA THREAD (DETECTION)
# ==========================================================
def camera_thread():
    global center_x, last_radius

    pic = Picamera2()
    pic.configure(picap_config := pic.create_preview_configuration(
        main={"format": "RGB888", "size": (320, 320)}
    ))
    pic.start()

    kernel = np.ones((5, 5), np.uint8)
    LOWER = np.array([35, 70, 60])
    UPPER = np.array([90, 255, 255])

    while True:
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

        with lock:
            center_x = cx
            last_radius = radius

        cv2.imshow("Frame", frame)
        cv2.imshow("Mask", mask)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    pic.stop()
    cv2.destroyAllWindows()


# ==========================================================
#               MOTOR THREAD (AUTONOMOUS MODE)
# ==========================================================
def motor_thread():
    global manual_mode, manual_last_time, last_error

    while True:

        # ---- MANUAL MODE ACTIVE → AUTONOMOUS PAUSED ----
        if manual_mode:
            if time.time() - manual_last_time > 30:
                manual_mode = False  # Auto return to autonomous
            else:
                time.sleep(0.01)
                continue

        # ---- AUTONOMOUS MODE BELOW ----
        with lock:
            cx = center_x
            radius = last_radius

        if cx is None:
            auto_stop_motors()
            time.sleep(0.01)
            continue

        if radius > RADIUS_FULL:
            auto_set_motors(-REVERSE_SPEED, -REVERSE_SPEED)
            time.sleep(0.01)
            continue

        if RADIUS_NEAR < radius <= RADIUS_FULL:
            auto_stop_motors()
            time.sleep(0.01)
            continue

        if radius < RADIUS_FAR:
            auto_set_motors(FORWARD_SPEED, FORWARD_SPEED)
            time.sleep(0.01)
            continue

        # PID rotation
        error = cx - CENTER
        derivative = error - last_error
        last_error = error

        rotation = KP * error + KD * derivative
        rotation = np.clip(rotation, -ROTATE_LIMIT, ROTATE_LIMIT)

        if abs(error) < CENTER_TOL:
            auto_set_motors(FORWARD_SPEED, FORWARD_SPEED)
            time.sleep(0.01)
            continue

        auto_set_motors(-rotation, rotation)
        time.sleep(0.01)


# ==========================================================
#                     KEYBOARD THREAD
# ==========================================================
def keyboard_thread():
    global manual_mode, manual_last_time

    print("\nManual Mode Keys: W/A/S/D/X")
    print("Auto returns to autonomous after 60 sec of no input.\n")

    while True:
        key = input().lower().strip()

        manual_mode = True
        manual_last_time = time.time()

        if key == 'w':
            forward()
        elif key == 's':
            backward()
        elif key == 'a':
            rotate_anticlockwise()
        elif key == 'd':
            rotate_clockwise()
        elif key == 'x':
            stop_manual()
        else:
            stop_manual()


# ==========================================================
#                           MAIN
# ==========================================================
try:
    t1 = threading.Thread(target=camera_thread, daemon=True)
    t2 = threading.Thread(target=motor_thread, daemon=True)
    t3 = threading.Thread(target=keyboard_thread, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    print("Robot Running... Press CTRL + C to stop.")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    auto_stop_motors()
    stop_manual()
    BP.reset_all()
    print("Robot Stopped Safely")
