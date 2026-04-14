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

image = pygame.image.load("images/background.jpg")

is_active = True

while is_active:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_active = False

    screen.blit(image, (0, 0))
    pygame.draw.rect(screen, "grey", (0, 500, 1925, 300))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()