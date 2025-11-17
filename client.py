import cv2, asyncio, websockets, base64
from picamera2 import Picamera2



async def send_frames():
    uri = "ws://192.168.0.109:8765"
    
    # ----- CAMERA SETUP -----
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (320, 320)})
    picam2.configure(config)
    picam2.start()

    async with websockets.connect(uri) as ws:
        while True:
            frame = picam2.capture_array()
            
            # Encode frame as JPEG -> base64
            _, buf = cv2.imencode(".jpg", frame)
            b64 = base64.b64encode(buf).decode() # for websockets to be able to send text
            await ws.send(b64)
                    
                    
            # Receive coords back
            coords = await ws.recv()
            print("Received Corrds: ", coords)

asyncio.run(send_frames())