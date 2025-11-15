from picamera2 import Picamera2
import cv2

picam2 = Picamera2()

def start_camera():
    cfg = picam2.create_preview_configuration(
        main={"size": (320, 320), "format": "RGB888"}
    )
    picam2.configure(cfg)
    picam2.start()

def generate_frames():
    """MJPEG generator for FastAPI video streaming."""
    while True:
        frame = picam2.capture_array()
        ok, jpeg = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               jpeg.tobytes() +
               b"\r\n")
