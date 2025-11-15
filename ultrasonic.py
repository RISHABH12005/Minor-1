import time
import brickpi3

BP = brickpi3.BrickPi3()

# Configure only PORT_1 for ultrasonic sensor
BP.set_sensor_type(BP.PORT_1, BP.SENSOR_TYPE.EV3_ULTRASONIC_CM)

time.sleep(1)

def sensor():
    try:
        while True:
            try:
                distance = BP.get_sensor(BP.PORT_1)  # Read sensor on PORT_1
                print(f"Sensor on PORT_1: {distance} cm")
            except brickpi3.SensorError as error:
                print(f"Sensor PORT_1 error: {error}")

            time.sleep(1)

    except KeyboardInterrupt:
        BP.reset_all()
        print("Stopping program.")

# Run the function
sensor()


