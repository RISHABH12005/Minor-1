# motor_control.py
from brickpi3 import BrickPi3

BP = BrickPi3()

C = BP.PORT_C
D = BP.PORT_D
DEFAULT_SPEED = 400

def forward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def backward(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def rotate_clockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, -speed)

def rotate_anticlockwise(speed=DEFAULT_SPEED):
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, speed)

def stop_motors():
    BP.set_motor_power(C, 0)
    BP.set_motor_power(D, 0)

def cleanup():
    stop_motors()
    BP.reset_all()
