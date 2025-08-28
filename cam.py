import cv2
import asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI()

# ---- WebSocket for camera streaming ----
@app.websocket("/ws_cam")
async def camera_ws(websocket: WebSocket):
    await websocket.accept()
    cap = cv2.VideoCapture(0)  # Robot camera

    if not cap.isOpened():
        print("Camera not accessible")
        await websocket.close()
        return

    try:
        fps = 20
        delay = 1 / fps

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Resize + compress
            frame = cv2.resize(frame, (640, 360))
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret:
                continue

            # Send raw JPEG bytes (no Base64, more efficient)
            await websocket.send_bytes(buffer.tobytes())

            await asyncio.sleep(delay)  # frame rate control

    except Exception as e:
        print("Camera connection closed:", e)
    finally:
        cap.release()
       
