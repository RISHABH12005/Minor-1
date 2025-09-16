from brickpi3 import BrickPi3
import time

BP = BrickPi3()
DEFAULT_SPEED = 2000  # RPM
BP.set_motor_dps(BP.PORT_A, DEFAULT_SPEED)  # Convert RPM to degrees/sec
time.sleep(5)
BP.set_motor_power(BP.PORT_A, 0)
BP.reset_all()
