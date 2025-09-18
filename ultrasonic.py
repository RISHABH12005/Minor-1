import time
import brickpi3

BP = brickpi3.BrickPi3()

# Configure PORT_1 and PORT_2 for ultrasonic sensors
BP.set_sensor_type(BP.PORT_1, BP.SENSOR_TYPE.EV3_ULTRASONIC_CM)
BP.set_sensor_type(BP.PORT_2, BP.SENSOR_TYPE.EV3_ULTRASONIC_CM)

time.sleep(1)

def sensor():
    try:
        while True:  # Keep reading continuously
            try:
                distance_1 = BP.get_sensor(BP.PORT_1)  # Read sensor on PORT_1
                print(f"Sensor on PORT_1: {distance_1} cm")
            except brickpi3.SensorError as error:
                print(f"Sensor PORT_1 error: {error}")

            try:
                distance_2 = BP.get_sensor(BP.PORT_2)  # Read sensor on PORT_2
                print(f"Sensor on PORT_2: {distance_2} cm")
            except brickpi3.SensorError as error:
                print(f"Sensor PORT_2 error: {error}")

            time.sleep(1)

    except KeyboardInterrupt:
        BP.reset_all()
        print("Stopping program.")

# Run the function
sensor()
