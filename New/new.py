from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from motor import forward, backward, rotate_clockwise, rotate_anticlockwise, stop_motors

from cam import start_camera, generate_frames
from ultrasonic import get_distance

app = FastAPI()

start_camera()
# ---------- INDIVIDUAL MOTOR ROUTES ----------

@app.post("/motor/forward")
def forward_route(speed: int = 400):
    forward(speed)
    return {"status": "ok", "action": "forward", "speed": speed}


@app.post("/motor/backward")
def backward_route(speed: int = 400):
    backward(speed)
    return {"status": "ok", "action": "backward", "speed": speed}


@app.post("/motor/right")
def clockwise_route(speed: int = 400):
    rotate_clockwise(speed)
    return {"status": "ok", "action": "clockwise", "speed": speed}


@app.post("/motor/left")
def anticlockwise_route(speed: int = 400):
    rotate_anticlockwise(speed)
    return {"status": "ok", "action": "anticlockwise", "speed": speed}


@app.post("/motor/stop")
def stop_route():
    stop_motors()
    return {"status": "ok", "action": "stop"}


# ------------------ VIDEO FEED API ------------------

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ------------------ SENSOR API ------------------

@app.get("/sensor")
def sensor_route():
    return {"distance_cm": get_distance()}
