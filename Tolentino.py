import pygame, sys, time, math, random

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
MAP_LENGTH = 20000
pygame.display.set_caption("Pixel Velocity")

WHITE, BLACK = (255,255,255),(0,0,0)
font = pygame.font.SysFont("Arial", 72)
small_font = pygame.font.SysFont("Arial", 28)

clock = pygame.time.Clock()
camera_x = 0
game_over = False
winner_text = ""
mode = None
player_name, enemy_name = "Player 1", "Enemy"

track_img = pygame.image.load("track.png").convert()
progress_bar_img = pygame.image.load("progress_bar.png").convert_alpha()
progress_bar_img = pygame.transform.scale(progress_bar_img, (800, 60))
boost_gauge_img = pygame.image.load("boost_circle.png").convert_alpha()
boost_gauge_img = pygame.transform.scale(boost_gauge_img, (80, 80))

player_frames = [
    pygame.transform.scale(pygame.image.load("car_red.png").convert_alpha(), (60, 120))
]
enemy_frames = [
    pygame.transform.scale(pygame.image.load("car_blue.png").convert_alpha(), (60, 120))
]

class Car:
    def __init__(self, x, y, frames, name, color):
        self.rect = pygame.Rect(x, y, frames[0].get_width(), frames[0].get_height())
        self.frames = frames
        self.frame_index = 0
        self.speed = 4
        self.energy = 100
        self.name = name
        self.color = color
        self.boosting = False

    def update_animation(self):
        self.frame_index = 0

    def draw(self, surface, camera_x):
        frame = self.frames[self.frame_index]
        surface.blit(frame, (self.rect.x - camera_x, self.rect.y))
        name_render = small_font.render(self.name, True, WHITE)
        surface.blit(name_render, (self.rect.x - camera_x, self.rect.y - 25))

player_car = Car(200, HEIGHT//2-100, player_frames, "Player 1", (220,20,60))
enemy_car = Car(200, HEIGHT//2+100, enemy_frames, "Enemy", (30,144,255))

energy_max = 100
energy_recharge = 0.3
boost_drain = 0.8
ai_target_y = HEIGHT//2
ai_boost_timer = random.randint(60, 180)

def draw_progress_bar():
    screen.blit(progress_bar_img, (100, 20))
    player_pos = 100 + (player_car.rect.x / MAP_LENGTH) * 800
    pygame.draw.circle(screen, player_car.color, (int(player_pos), 50), 10)
    enemy_pos = 100 + (enemy_car.rect.x / MAP_LENGTH) * 800
    pygame.draw.circle(screen, enemy_car.color, (int(enemy_pos), 50), 10)

def draw_boost_gauge(car, y_offset):
    screen.blit(boost_gauge_img, (WIDTH-120, y_offset))
    rect = pygame.Rect(WIDTH-120, y_offset, 80, 80)
    angle = (car.energy / energy_max) * math.pi * 2
    pygame.draw.arc(screen, (255,215,0), rect, 0, angle, 4)

def draw_scene():
    track_y = HEIGHT // 2 - track_img.get_height() // 2
    for x in range(0, MAP_LENGTH, track_img.get_width()):
        screen.blit(track_img, (x - camera_x, track_y))
    player_car.draw(screen, camera_x)
    enemy_car.draw(screen, camera_x)
    draw_progress_bar()
    if player_car.boosting or player_car.energy < energy_max:
        draw_boost_gauge(player_car, HEIGHT//2 - 150)
    if enemy_car.boosting or enemy_car.energy < energy_max:
        draw_boost_gauge(enemy_car, HEIGHT//2 + 50)
    if game_over:
        text = font.render(winner_text, True, WHITE)
        rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(text, rect)

def update_game(keys):
    global camera_x, game_over, winner_text
    global ai_target_y, ai_boost_timer
    if not game_over:
        player_car.rect.x += player_car.speed
        if keys[pygame.K_UP]:
            player_car.rect.y -= 5
        if keys[pygame.K_DOWN]:
            player_car.rect.y += 5

        # Player boost logic (fixed)
        if keys[pygame.K_b] and player_car.energy > 0:
            player_car.speed = 8
            player_car.energy = max(0, player_car.energy - boost_drain)
            player_car.boosting = True
        else:
            player_car.speed = 4
            player_car.boosting = False

        enemy_car.rect.x += enemy_car.speed
        if mode == "AI":
            if enemy_car.rect.y < ai_target_y:
                enemy_car.rect.y += 2
            elif enemy_car.rect.y > ai_target_y:
                enemy_car.rect.y -= 2
            if random.random() < 0.01:
                ai_target_y = HEIGHT // 2 + random.randint(-80, 80)

            if enemy_car.energy > 0 and ai_boost_timer <= 0:
                enemy_car.speed = 8
                enemy_car.energy = max(0, enemy_car.energy - boost_drain)
                enemy_car.boosting = True
                ai_boost_timer = random.randint(60, 180)
            else:
                enemy_car.speed = 4
                enemy_car.boosting = False
                ai_boost_timer -= 1
        else:
            if keys[pygame.K_w]:
                enemy_car.rect.y -= 5
            if keys[pygame.K_s]:
                enemy_car.rect.y += 5

            # Player 2 boost logic (fixed)
            if keys[pygame.K_v] and enemy_car.energy > 0:
                enemy_car.speed = 8
                enemy_car.energy = max(0, enemy_car.energy - boost_drain)
                enemy_car.boosting = True
            else:
                enemy_car.speed = 4
                enemy_car.boosting = False

        # Recharge only when not boosting
        if not player_car.boosting:
            player_car.energy = min(energy_max, player_car.energy + energy_recharge)
        if not enemy_car.boosting:
            enemy_car.energy = min(energy_max, enemy_car.energy + energy_recharge)

        camera_x = max(0, min(player_car.rect.x - WIDTH // 2, MAP_LENGTH - WIDTH))
        if player_car.rect.x >= MAP_LENGTH - player_car.rect.width:
            game_over = True
            winner_text = f"{player_car.name} WINS"
        if enemy_car.rect.x >= MAP_LENGTH - enemy_car.rect.width:
            game_over = True
            winner_text = f"{enemy_car.name} WINS"

def countdown():
    for i in ["READY", "SET", "GO!"]:
        screen.fill(BLACK)
        text = font.render(i, True, WHITE)
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, rect)
        pygame.display.flip()
        time.sleep(1)

def text_input(prompt):
    text = ""
    entering = True
    while entering:
        screen.fill(BLACK)
        msg = font.render(prompt, True, WHITE)
        msg_rect = msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        screen.blit(msg, msg_rect)
        display_text = text[-25:]
        inp = font.render(display_text, True, (255, 215, 0))
        inp_rect = inp.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(inp, inp_rect)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    entering = False
                elif e.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    text += e.unicode
    return text if text.strip() != "" else prompt

def select_mode():
    global mode, player_name, enemy_name
    selecting = True
    while selecting:
        screen.fill(BLACK)
        text1 = font.render("Press 1: VS AI", True, WHITE)
        text2 = font.render("Press 2: VS Player", True, WHITE)
        screen.blit(text1, (WIDTH // 2 - 200, HEIGHT // 2 - 100))
        screen.blit(text2, (WIDTH // 2 - 200, HEIGHT // 2 + 50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    mode = "AI"
                    player_name = text_input("Enter Player 1 Name")
                    enemy_name = "AI"
                    player_car.name = player_name
                    enemy_car.name = enemy_name
                    selecting = False
                elif e.key == pygame.K_2:
                    def select_mode():
                        global mode, player_name, enemy_name
    selecting = True
    while selecting:
        screen.fill(BLACK)
        text1 = font.render("Press 1: VS AI", True, WHITE)
        text2 = font.render("Press 2: VS Player", True, WHITE)
        screen.blit(text1, (WIDTH // 2 - 200, HEIGHT // 2 - 100))
        screen.blit(text2, (WIDTH // 2 - 200, HEIGHT // 2 + 50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    mode = "AI"
                    player_name = text_input("Enter Player 1 Name")
                    enemy_name = "AI"
                    player_car.name = player_name
                    enemy_car.name = enemy_name
                    selecting = False
                elif e.key == pygame.K_2:
                    mode = "Player"
                    player_name = text_input("Enter Player 1 Name")
                    enemy_name = text_input("Enter Player 2 Name")
                    player_car.name = player_name
                    enemy_car.name = enemy_name
                    selecting = False

# Start game
select_mode()
countdown()

running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
    keys = pygame.key.get_pressed()
    update_game(keys)
    draw_scene()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
