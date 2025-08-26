from brickpi3 import BrickPi3
import time

BP = BrickPi3()
A = BP.PORT_A
B = BP.PORT_C
C = BP.PORT_B
D = BP.PORT_D

DEFAULT_SPEED = 300

def forward(speed=DEFAULT_SPEED):
    print("Moving forward")
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def backward(speed=DEFAULT_SPEED):
    print("Moving backward")
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def rotate_clockwise(speed=DEFAULT_SPEED):
    print("Rotating clockwise")
    BP.set_motor_dps(A, -speed)
    BP.set_motor_dps(B, -speed)
    BP.set_motor_dps(C, speed)
    BP.set_motor_dps(D, speed)

def rotate_anticlockwise(speed=DEFAULT_SPEED):
    print("Rotating anticlockwise")
    BP.set_motor_dps(A, speed)
    BP.set_motor_dps(B, speed)
    BP.set_motor_dps(C, -speed)
    BP.set_motor_dps(D, -speed)

def stop_motors():
    print("Stopping motors")
    BP.set_motor_power(A, 0)
    BP.set_motor_power(B, 0)
    BP.set_motor_power(C, 0)
    BP.set_motor_power(D, 0)

try:
    while True:
        cmd = input("Enter command (forward, backward, clockwise, anticlockwise, stop, exit): ").strip().lower()

        if cmd == "f":
            forward()
        elif cmd == "b":
            backward()
        elif cmd == "c":
            rotate_clockwise()
        elif cmd == "a":
            rotate_anticlockwise()
        elif cmd == "s":
            stop_motors()
        elif cmd == "e":
            stop_motors()
            print("Exiting program.")
            break
        else:
            print("Invalid command. Try again.")

except KeyboardInterrupt:
    print("Program interrupted by user.")

finally:
    stop_motors()
    BP.reset_all()
