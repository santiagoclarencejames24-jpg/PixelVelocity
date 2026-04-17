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

image1= pygame.image.load("images/bg.png")
image2 = pygame.image.load("images/road.png")
image_continuity = pygame.image.load("images/road.png")


image1_1 = pygame.transform.smoothscale(image1, (1925, 1025))
image2_1 = pygame.transform.smoothscale(image2, (1925, 450))
image_continuity_1 = pygame.transform.smoothscale(image_continuity, (1925, 450))


# Two car
#=======CAR 1=======
car1 = pygame.Surface((160, 70), pygame.SRCALPHA)
pygame.draw.rect(car1, (220, 30, 30), (0, 20, 160, 40), border_radius=12)
pygame.draw.rect(car1, (255, 255, 255), (20, 28, 50, 20), border_radius=5)
pygame.draw.rect(car1, (255, 255, 255), (90, 28, 40, 20), border_radius=5)
pygame.draw.rect(car1, (40, 40, 40), (5, 35, 150, 25), border_radius=10)
pygame.draw.circle(car1, (20, 20, 20), (35, 65), 12)
pygame.draw.circle(car1, (20, 20, 20), (125, 65), 12)
pygame.draw.circle(car1, (180, 180, 180), (35, 65), 6)
pygame.draw.circle(car1, (180, 180, 180), (125, 65), 6)
pygame.draw.rect(car1, (255, 215, 0), (145, 40, 10, 12), border_radius=4)

#=======CAR 2=======
car2 = pygame.Surface((150, 65), pygame.SRCALPHA)
pygame.draw.rect(car2, (40, 100, 220), (0, 18, 150, 38), border_radius=12)
pygame.draw.rect(car2, (255, 255, 255), (15, 25, 45, 18), border_radius=5)
pygame.draw.rect(car2, (255, 255, 255), (80, 25, 45, 18), border_radius=5)
pygame.draw.rect(car2, (35, 35, 35), (5, 30, 140, 24), border_radius=10)
pygame.draw.circle(car2, (20, 20, 20), (30, 60), 11)
pygame.draw.circle(car2, (20, 20, 20), (120, 60), 11)
pygame.draw.circle(car2, (190, 190, 190), (30, 60), 5)
pygame.draw.circle(car2, (190, 190, 190), (120, 60), 5)
pygame.draw.rect(car2, (0, 255, 255), (140, 35, 8, 10), border_radius=4)

car1_x = 90
car1_y = 675
car2_x = 60
car2_y = 760

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
    screen.blit(car1, (car1_x, car1_y))
    screen.blit(car2, (car2_x, car2_y))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()