import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import random
import sys

#pygame design
pygame.init()


width = 1925
height = 1025
screen = pygame.display.set_mode((width, height))

clock = pygame.time.Clock()

pygame.display.set_caption("Pixel Velocity")

#Road and background images
image1= pygame.image.load("images/bg.png")
image2 = pygame.image.load("images/road.png")
image_continuity = pygame.image.load("images/road.png")

#Resizing the images to fit the screen
image1_1 = pygame.transform.smoothscale(image1, (1925, 1025))
image2_1 = pygame.transform.smoothscale(image2, (1925, 450))
image_continuity_1 = pygame.transform.smoothscale(image_continuity, (1925, 450))

#Car images
Car1 = pygame.image.load("images/Car_1.png").convert_alpha()
Car2 = pygame.image.load("images/Car_2.png").convert_alpha()
Car1_1 = pygame.transform.smoothscale(Car1, (150, 75))
Car2_1 = pygame.transform.smoothscale(Car2, (150, 65))

#car positions
car1_x = 70
car1_y = 700
car2_x = 60
car2_y = 900

#controlled speed of variables
road_x = 0
road_speed =-5

is_active = True

while is_active:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_active = False

    road_x += road_speed
    if road_x < -1925:
        road_x = 0

    screen.blit(image1_1, (0, 0))
    screen.blit(image2_1, (road_x, 600))
    screen.blit(image_continuity_1, (road_x + 1925, 600))
    screen.blit(Car1_1, (car1_x, car1_y))
    screen.blit(Car2_1, (car2_x, car2_y))


    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()