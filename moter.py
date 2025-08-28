import asyncio
from fastapi import FastAPI, WebSocket
from brickpi3 import BrickPi3

app = FastAPI()

# ---- Motor setup ----
BP = BrickPi3()
A, B, C, D = BP.PORT_A, BP.PORT_C, BP.PORT_B, BP.PORT_D
DEFAULT_SPEED = 300

def forward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def backward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def rotate_clockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def rotate_anticlockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def stop_motors():
    BP.set_motor_power(A, 0)
    BP.set_motor_power(B, 0)
    BP.set_motor_power(C, 0)
    BP.set_motor_power(D, 0)

# ---- WebSocket for robot control ----
@app.websocket("/ws_robot")
async def robot_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            print(f"Received command: {msg}")

            if msg == "forward":
                forward()
            elif msg == "backward":
                backward()
            elif msg == "left":
                rotate_anticlockwise()
            elif msg == "right":
                rotate_clockwise()
            elif msg == "stop":
                stop_motors()

    except Exception as e:
        print("Robot control connection closed:", e)
    finally:
        stop_motors()
        BP.reset_all()
