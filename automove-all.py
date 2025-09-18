from picamera2 import Picamera2
import cv2
import numpy as np
from collections import deque
from brickpi3 import BrickPi3
import json
import os
import time

# ----- HSV CONFIG -----
CONFIG_FILE = "hsv_config.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        hsv_config = json.load(f)
else:
    hsv_config = {"LH": 35, "LS": 80, "LV": 60, "UH": 85, "US": 255, "UV": 255}

# ----- CAMERA SETUP -----
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (320, 320)})
picam2.configure(config)
picam2.start()

# ----- PATH TRAIL -----
pts = deque(maxlen=100)

# ----- TRACKBARS -----
cv2.namedWindow("Trackbars")
def nothing(x): pass
cv2.createTrackbar("LH","Trackbars",hsv_config["LH"],179,nothing)
cv2.createTrackbar("LS","Trackbars",hsv_config["LS"],255,nothing)
cv2.createTrackbar("LV","Trackbars",hsv_config["LV"],255,nothing)
cv2.createTrackbar("UH","Trackbars",hsv_config["UH"],179,nothing)
cv2.createTrackbar("US","Trackbars",hsv_config["US"],255,nothing)
cv2.createTrackbar("UV","Trackbars",hsv_config["UV"],255,nothing)

# ----- MOTOR SETUP -----
BP = BrickPi3()
A = BP.PORT_A
B = BP.PORT_C
C = BP.PORT_B
D = BP.PORT_D
DEFAULT_SPEED = 1000

def forward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, -speed)

def backward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, speed)

def rotate_clockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def rotate_anticlockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def stop_motors():
    BP.set_motor_power(A, 0)
    BP.set_motor_power(B, 0)
    BP.set_motor_power(C, 0)
    BP.set_motor_power(D, 0)

# ----- FRAME SETTINGS -----
FRAME_WIDTH = 320
CENTER_X = FRAME_WIDTH // 2
TOLERANCE = 30

# ----- DETECT RING -----
def detect_ring(frame, lower_green, upper_green):
    blurred = cv2.GaussianBlur(frame, (11,11),0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_green, upper_green)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5),np.uint8))
    
    contours,_ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center = None
    if contours:
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) > 500:
            ((x,y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            if M["m00"] > 0:
                center = (int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"]))
                if radius > 10:
                    cv2.circle(frame,(int(x),int(y)),int(radius),(0,255,255),2)
                    cv2.circle(frame,center,5,(0,0,255),-1)
    return center, mask

# ----- MAIN LOOP -----
try:
    while True:
        frame = picam2.capture_array()

        # Get HSV from trackbars
        lh = cv2.getTrackbarPos("LH","Trackbars")
        ls = cv2.getTrackbarPos("LS","Trackbars")
        lv = cv2.getTrackbarPos("LV","Trackbars")
        uh = cv2.getTrackbarPos("UH","Trackbars")
        us = cv2.getTrackbarPos("US","Trackbars")
        uv = cv2.getTrackbarPos("UV","Trackbars")
        lower_green = np.array([lh,ls,lv])
        upper_green = np.array([uh,us,uv])

        # Detect ring
        center, mask = detect_ring(frame, lower_green, upper_green)
        pts.appendleft(center)

        # Draw path
        for i in range(1,len(pts)):
            if pts[i-1] is None or pts[i] is None:
                continue
            thickness = int(np.sqrt(100/float(i+1))*2.5)
            cv2.line(frame, pts[i-1], pts[i], (0,0,255), thickness)

        # ----- AUTOMATIC MOTOR CONTROL -----
        if center:
            x, y = center
            if x < CENTER_X - TOLERANCE:
                rotate_anticlockwise()
            elif x > CENTER_X + TOLERANCE:
                rotate_clockwise()
            else:
                forward()
        else:
            stop_motors()

        # Show frames
        cv2.imshow("Frame", frame)
        cv2.imshow("Mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            hsv_config = {"LH": lh,"LS": ls,"LV": lv,"UH": uh,"US": us,"UV": uv}
            with open(CONFIG_FILE,"w") as f:
                json.dump(hsv_config,f,indent=4)
            break

except KeyboardInterrupt:
    print("Program stopped by user.")

finally:
    stop_motors()
    cv2.destroyAllWindows()
    picam2.stop()
    BP.reset_all()
