import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import Car
import random

class pixelvelocity():
    def __init__(self, car, track):
        self.car = car
        self.track = track

p1 = Car.car(2, "Player", Car.car.colors()[0], 1)
Ai = Car.car(2, "Ai", Car.car.colors()[1], 1)

#pygame design
pygame.init()


width = 1925
height = 1025
screen = pygame.display.set_mode((width, height))

clock = pygame.time.Clock()

pygame.display.set_caption("Pixel Velocity")

image1= pygame.image.load("images/background.jpg")
image2 = pygame.image.load("images/road.png")

image2_1 = pygame.transform.smoothscale(image2, (1925, 450))
is_active = True

while is_active:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_active = False

    screen.blit(image1, (0, 0))
    screen.blit(image2_1, (0, 500))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()