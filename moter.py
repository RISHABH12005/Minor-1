from fastapi import FastAPI, HTTPException
from brickpi3 import BrickPi3
import time

BP = BrickPi3()
A = BP.PORT_A
B = BP.PORT_C
C = BP.PORT_B
D = BP.PORT_D
DEFAULT_SPEED = 1000 

app = FastAPI()

def forward(speed=DEFAULT_SPEED):
    print("Moving forward")
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, -speed)

def backward(speed=DEFAULT_SPEED):
    print("Moving backward")
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, speed)

def rotate_clockwise(speed=DEFAULT_SPEED):
    print("Rotating clockwise")
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def rotate_anticlockwise(speed=DEFAULT_SPEED):
    print("Rotating anticlockwise")
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def stop_motors():
    print("Stopping motors")
    BP.set_motor_power(A, 0)
    BP.set_motor_power(B, 0)
    BP.set_motor_power(C, 0)
    BP.set_motor_power(D, 0)

@app.get("/motor/move/{command}")
def motor_command(command: str):
    """API endpoint to receive and execute motor commands."""
    
    # Stop motors first for instant response to new command
    stop_motors() 

    if command == "forward":
        forward()
    elif command == "backward":
        backward()
    elif command == "left": 
        rotate_anticlockwise()
    elif command == "right": 
        rotate_clockwise()
    elif command == "stop":
        stop_motors() 
    else:
        raise HTTPException(status_code=400, detail=f"Invalid command: {command}")

    return {"status": "success", "command": command, "message": f"Executed {command} command."}

@app.on_event("shutdown")
def shutdown_event():
    """Ensure motors are stopped when the API server shuts down."""
    stop_motors()
    BP.reset_all()

# To run this, use: uvicorn motor_api:app --host 0.0.0.0 --port 8000