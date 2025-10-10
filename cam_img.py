from fastapi import FastAPI, Response
import cv2
import asyncio
import time

app = FastAPI()

def generate_frames():
    """Generator function for the MJPEG stream."""
    print("Camera stream generator starting...")
    cap = cv2.VideoCapture(0) 
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame from camera.")
            time.sleep(1)
            continue
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_bytes = buffer.tobytes()

        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
               b'\r\n' + frame_bytes + b'\r\n')
        
      
        time.sleep(0.033) # ~30 FPS

    cap.release()
    print("Camera stream generator stopped.")

@app.get("/video_feed")
async def video_feed():
    """Endpoint for the MJPEG video stream."""
    # Use Response with media_type for streaming
    return Response(content=generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# To run this, use: uvicorn cam_img:app --host 0.0.0.0 --port 8001