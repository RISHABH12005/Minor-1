from picamera2 import Picamera2
import cv2
import time

picam2 = Picamera2()
max_resolution = picam2.sensor_resolution
video_config = picam2.create_preview_configuration(
    main={"size": max_resolution, "format": "RGB888"}
)
picam2.configure(video_config)
picam2.start()
time.sleep(2)

print(f"Streaming live at max resolution: {max_resolution}")

while True:
    frame = picam2.capture_array()
    cv2.imshow("IMG", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
picam2.stop()
