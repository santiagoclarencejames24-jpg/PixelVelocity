import pygame
import Car
import random

class pixelvelocity():
    def __init__(self, car, track):
        self.car = car
        self.track = track

p1 = Car.car(2, "Player", "Red", 1)
Ai = Car.car(2, "Ai", Car.colors()[1], 1)
print(Ai)