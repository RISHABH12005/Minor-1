sudo apt update && sudo apt upgrade -y

sudo apt install -y git python3-venv python3-full python3-pip python3-picamera2 libcamera-apps

pip install spidev RPi.GPIO numpy

# If Error

pip install wheel

pip install RPi.GPIO

pip install --use-pep517 RPi.GPIO

sudo apt install python3-rpi.gpio

# -----

sudo apt install -y \
    git \
    python3-full \
    python3-venv \
    python3-pip \
    python3-rpi.gpio \
    python3-picamera2 \
    libcamera-apps \

git clone https://github.com/DexterInd/BrickPi3.git

# Verify

cd BrickPi3/Software/Python

python3 Examples/Read_Info.py

# -----

cd BrickPi3/Software/Python

pip install .

# active env

pip install opencv-contrib-python

# Verify

python -c "import cv2; print(cv2.__version__)"

# -----

sudo apt install -y python3-opencv

# If warning

sudo chmod 700 /run/user/1000

sudo apt install imagemagick

mogrify -strip *.png -y




