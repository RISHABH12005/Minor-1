from picamera2 import Picamera2
import time
import cv2

picam2 = Picamera2()
picam2.preview_configuration.main.size = (1080, 1080)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()

time.sleep(2)

frame = picam2.capture_array()
cv2.imwrite("img.jpg", frame)
print("Frame captured and saved as 'img.jpg'")
