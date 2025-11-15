from brickpi3 import BrickPi3

BP = BrickPi3()
PORT = BP.PORT_1

BP.set_sensor_type(PORT, BP.SENSOR_TYPE.EV3_ULTRASONIC_CM)

def get_distance():
    try:
        return BP.get_sensor(PORT)
    except:
        return None
