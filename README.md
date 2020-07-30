# MQTT Turret

## Requirements

### Hardware
1. Raspberry Pi - I used a Zero W.
2. MQTT
3. PCA9685 - and I2C device
4. 2 MG90S servos
5. 1 Laser Diode
6. Seperate Power for PCA9685 and servos.
7. Mounts & Case for above.

Pan/Tilt mounts are for a particular servo. SG90 and MG90 servos are
not the same size and that can vary by manufacturer. 

### Software
Python 3
Paho-Mqtt
AdaFruit Blinka
AdaFruit PCA9685 

## Install
### clone
### pip
### systemd

## Usage
### MQTT
### API 

## TODO
Calibate Servos to get full 180 degree movement.

## Future - V2
Shape movements - circle, diamond, ...
Better use of PCA9685 - Singleton class to init.

