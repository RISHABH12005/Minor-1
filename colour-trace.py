from picamera2 import Picamera2
import cv2
import numpy as np
from collections import deque
import json
import os

# File to save HSV config
CONFIG_FILE = "hsv_config.json"

# Load saved HSV config if exists
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        hsv_config = json.load(f)
else:
    hsv_config = {
        "LH": 35, "LS": 80, "LV": 60,
        "UH": 85, "US": 255, "UV": 255
    }

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (320, 320)})
picam2.configure(config)
picam2.start()

# Store tracked points
pts = deque(maxlen=100)

# Create window for trackbars
cv2.namedWindow("Trackbars")

def nothing(x):
    pass

# Create 6 trackbars with loaded values
cv2.createTrackbar("LH", "Trackbars", hsv_config["LH"], 179, nothing)
cv2.createTrackbar("LS", "Trackbars", hsv_config["LS"], 255, nothing)
cv2.createTrackbar("LV", "Trackbars", hsv_config["LV"], 255, nothing)
cv2.createTrackbar("UH", "Trackbars", hsv_config["UH"], 179, nothing)
cv2.createTrackbar("US", "Trackbars", hsv_config["US"], 255, nothing)
cv2.createTrackbar("UV", "Trackbars", hsv_config["UV"], 255, nothing)

while True:
    frame = picam2.capture_array()

    # Blur + convert to HSV
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # Get current positions of trackbars
    lh = cv2.getTrackbarPos("LH", "Trackbars")
    ls = cv2.getTrackbarPos("LS", "Trackbars")
    lv = cv2.getTrackbarPos("LV", "Trackbars")
    uh = cv2.getTrackbarPos("UH", "Trackbars")
    us = cv2.getTrackbarPos("US", "Trackbars")
    uv = cv2.getTrackbarPos("UV", "Trackbars")

    # Define HSV range from trackbars
    lower_green = np.array([lh, ls, lv])
    upper_green = np.array([uh, us, uv])

    # Mask for green
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # Noise removal
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    # Find contours
    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center = None

    if len(contours) > 0:
        # Largest contour
        c = max(contours, key=cv2.contourArea)

        if cv2.contourArea(c) > 500:  # filter out noise
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            if M["m00"] > 0:
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                if radius > 10:
                    # Draw circle + center
                    cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                    cv2.circle(frame, center, 5, (0, 0, 255), -1)

    # Save center
    pts.appendleft(center)

    # Draw path trail
    for i in range(1, len(pts)):
        if pts[i - 1] is None or pts[i] is None:
            continue
        thickness = int(np.sqrt(100 / float(i + 1)) * 2.5)
        cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

    # Show frames
    cv2.imshow("Frame", frame)
    cv2.imshow("Mask", mask)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC to quit
        # Save HSV config on exit
        hsv_config = {"LH": lh, "LS": ls, "LV": lv,
                      "UH": uh, "US": us, "UV": uv}
        with open(CONFIG_FILE, "w") as f:
            json.dump(hsv_config, f, indent=4)
        break

cv2.destroyAllWindows()
picam2.stop()
