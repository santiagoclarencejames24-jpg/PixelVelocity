import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import Car
import random

class pixelvelocity():
    def __init__(self, car, track):
        self.car = car
        self.track = track

p1 = Car.car(2, "Player", Car.colors()[0], 1)
Ai = Car.car(2, "Ai", Car.colors()[1], 1)
print(p1)
print(Ai)