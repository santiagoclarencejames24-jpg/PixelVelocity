# Pixel Velocity - Modified with AI difficulty and fixed mode selection
# Based on the uploaded script (minor rework to integrate difficulty and mode flow)
# Keep your assets (images, sounds) in the same folders as before.

import os, pygame, sys, time, math, random, logging
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
pygame.init()

# --- Logging setup (toggle diagnostics) ---
VERBOSE = False
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()
if not VERBOSE:
    logger.setLevel(logging.WARNING)

# --- Screen setup ---
W, H = 1000, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Pixel Velocity")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 72)
sfont = pygame.font.SysFont("Arial", 28)

# --- Globals ---
MAP_LEN, WHITE, BLACK = 20000, (255, 255, 255), (0, 0, 0)
camera_x, game_over, winner_text, mode = 0, False, "", None
game_state, money, new_race = "menu", 500, True

# New: AI difficulty global (default Normal)
ai_difficulty = "Normal"  # "Easy", "Normal", "Hard"

# --- Assets helpers ---
def load_img(path, size=None, alpha=True):
    try:
        img = pygame.image.load(path)
        img = img.convert_alpha() if alpha else img.convert()
        return pygame.transform.smoothscale(img, size) if size else img
    except Exception:
        # fallback surface
        surf = pygame.Surface(size if size else (60, 60))
        surf.fill((100, 100, 100))
        return surf

# Keep original asset loads but safe-guarded
progress_bar = load_img("progress_bar.png", (500, 40))
boost_gauge = load_img("boost_circle.png", (120, 120))
player_frames = [load_img("Car_1.png", (60, 120))]
enemy_frames = [load_img("Car_2.png", (60, 120))]

# --- Background files and display names ---
bg_files = [
    "images/bg.png",   # Default
    "images/bg2.png",
    "images/bg3.png",
    "images/bg4.png",
    "images/bg5.png",
    "images/bg6.png",
    "images/bg7.png",
    "images/bg8.png",
    "images/bg9.png",
]

bg_display_names = [
    "Default",
    "Universal",
    "End of the World",
    "Western",
    "Futuristic",
    "Snow",
    "Autumn",
    "Spring",
    "Volcanic",
]

# --- Robust background loading with diagnostics ---
bg_images = []
bg_thumbs = []
thumb_w, thumb_h = 200, 120

logger.info("[BG LOAD] Starting background load check...")
try:
    cwd = os.getcwd()
    logger.info(f"[BG LOAD] Current working directory: {cwd}")
    images_list = os.listdir(os.path.join(cwd, "images")) if os.path.isdir(os.path.join(cwd, "images")) else []
    logger.info(f"[BG LOAD] images/ contains: {images_list}")
except Exception as ex:
    logger.info(f"[BG LOAD] Could not list images folder: {ex}")

for f in bg_files:
    if not os.path.exists(f):
        logger.debug(f"[BG LOAD] File not found: {f}")
        surf = pygame.Surface((W, H))
        surf.fill((30, 30, 30))
        bg_images.append(surf)
        t = pygame.Surface((thumb_w, thumb_h))
        t.fill((60, 60, 60))
        bg_thumbs.append(t)
        continue

    try:
        full = pygame.image.load(f)
        try:
            full = full.convert()
        except Exception:
            full = full.convert_alpha()
        full = pygame.transform.smoothscale(full, (W, H))
        bg_images.append(full)

        thumb = pygame.image.load(f)
        try:
            thumb = thumb.convert()
        except Exception:
            thumb = thumb.convert_alpha()
        thumb = pygame.transform.smoothscale(thumb, (thumb_w, thumb_h))
        bg_thumbs.append(thumb)

        logger.info(f"[BG LOAD] Loaded {f} successfully.")
    except Exception as ex:
        logger.info(f"[BG LOAD] Failed to load {f}: {ex}")
        surf = pygame.Surface((W, H))
        surf.fill((30, 30, 30))
        bg_images.append(surf)
        t = pygame.Surface((thumb_w, thumb_h))
        t.fill((60, 60, 60))
        bg_thumbs.append(t)

# set current background
current_bg_idx = 0
current_bg = bg_images[current_bg_idx]

road = load_img("images/road.png", (W, 450), False)
road_x, road_speed = 0, -5

# --- Audio Setup ---
try:
    pygame.mixer.init()
    engine_sound_player = pygame.mixer.Sound("engine_player.wav")
    engine_sound_enemy = pygame.mixer.Sound("engine_enemy.wav")
    boost_sound_player = pygame.mixer.Sound("boost_player.wav")
    boost_sound_enemy = pygame.mixer.Sound("boost_enemy.wav")
except Exception:
    # If audio fails, create dummy objects with set_volume method
    class DummySound:
        def play(self, *a, **k): pass
        def stop(self): pass
        def set_volume(self, v): pass
    engine_sound_player = engine_sound_enemy = boost_sound_player = boost_sound_enemy = DummySound()

home_music = "home_music.mp3"
race_music = "race_music.mp3"
pause_music = "pause_music.mp3"

def play_music(track, loop=-1):
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(track)
        pygame.mixer.music.play(loop)
    except Exception:
        pass

# --- Car class ---
class Car:
    def __init__(self, x, y, frames, name, color, engine, boost):
        self.rect = pygame.Rect(x, y, *frames[0].get_size())
        self.frames, self.name, self.color = frames, name, color
        self.speed, self.energy, self.boosting = 4, 100, False
        self.engine, self.boost = engine, boost
        self.base_speed = 4
        self.boost_speed = 8
        self.boost_cooldown = 0.0  # seconds until next allowed boost (for AI)
        self.last_boost_time = 0.0

    def draw(self, surf, cx):
        surf.blit(self.frames[0], (self.rect.x - cx, self.rect.y))
        surf.blit(sfont.render(self.name, 1, WHITE), (self.rect.x - cx, self.rect.y - 25))

player = Car(200, H // 2 - 100, player_frames, "Player 1", (220, 20, 60), engine_sound_player, boost_sound_player)
enemy = Car(200, H // 2 + 100, enemy_frames, "Enemy", (30, 144, 255), engine_sound_enemy, boost_sound_enemy)

# --- Full car list (17 cars) ---
cars_list = [
    {"name": "Speedster", "img": "Car_1.png"},
    {"name": "Tank", "img": "Car_2.png"},
    {"name": "Racer X", "img": "Car_3.png"},
    {"name": "Phantom", "img": "Car_4.png"},
    {"name": "Blaze", "img": "Car_5.png"},
    {"name": "Comet", "img": "Car_6.png"},
    {"name": "Vortex", "img": "Car_7.png"},
    {"name": "Shadow", "img": "Car_8.png"},
    {"name": "Aurora", "img": "Car_9.png"},
    {"name": "Titan", "img": "Car_10.png"},
    {"name": "Nebula", "img": "Car_11.png"},
    {"name": "Cyclone", "img": "Car_12.png"},
    {"name": "Mirage", "img": "Car_13.png"},
    {"name": "Bolt", "img": "Car_14.png"},
    {"name": "Drift", "img": "Car_15.png"},
    {"name": "Specter", "img": "Car_16.png"},
    {"name": "Inferno", "img": "Car_17.png"},
]

# helper to load thumbnail for car menu (small)
def load_car_thumb(img_name, size=(120, 60)):
    path = img_name
    try:
        return load_img(path, size)
    except Exception:
        t = pygame.Surface(size)
        t.fill((80, 80, 80))
        return t

# --- Clamp cars to road ---
def clamp_to_road(car):
    top, bottom = H // 2, H // 2 + 450 - car.rect.height
    car.rect.y = max(top, min(car.rect.y, bottom))

# --- Pause button (text + clickable rect) ---
pause_surf = sfont.render("⏸ Pause", True, WHITE)
pause_rect = pause_surf.get_rect(topright=(W - 20, 20))
pause_bg_color = (40, 40, 40)
pause_bg_padding = 8
pause_bg_rect = pygame.Rect(
    pause_rect.left - pause_bg_padding,
    pause_rect.top - pause_bg_padding,
    pause_rect.width + pause_bg_padding * 2,
    pause_rect.height + pause_bg_padding * 2
)

# --- Reset Game State ---
def reset_game_state():
    global current_bg_idx, current_bg, MAP_LEN, mode, game_over, new_race, camera_x, ai_difficulty
    current_bg_idx = 0
    current_bg = bg_images[current_bg_idx]
    MAP_LEN = 20000
    mode = None
    ai_difficulty = "Normal"
    game_over = False
    new_race = True
    camera_x = 0
    player.rect.x, player.rect.y = 200, H // 2 - 100
    enemy.rect.x, enemy.rect.y = 200, H // 2 + 100
    player.energy, enemy.energy = 100, 100
    player.boosting = False
    enemy.boosting = False

# --- UI ---
def progress_bar_draw():
    bar_x = (W - progress_bar.get_width()) // 2
    bar_y = 20
    screen.blit(progress_bar, (bar_x, bar_y))
    start_text = sfont.render("START", True, WHITE)
    finish_text = sfont.render("FINISH", True, WHITE)
    screen.blit(start_text, (bar_x - start_text.get_width() - 10, bar_y))
    screen.blit(finish_text, (bar_x + progress_bar.get_width() + 10, bar_y))
    for c in (player, enemy):
        pos = bar_x + (c.rect.x / MAP_LEN) * progress_bar.get_width()
        pygame.draw.circle(screen, c.color, (int(pos), bar_y + progress_bar.get_height() // 2), 8)

def boost_draw(c, y):
    gx = W - boost_gauge.get_width() - 60
    screen.blit(boost_gauge, (gx, y))
    rect = pygame.Rect(gx, y, boost_gauge.get_width(), boost_gauge.get_height())
    ang = (c.energy / 100) * math.pi * 2
    color = (0, 255, 0) if c.energy > 70 else (255, 165, 0) if c.energy > 30 else (255, 0, 0)
    pygame.draw.arc(screen, color, rect, 0, ang, 6)

def scene_draw():
    global road_x, current_bg
    road_x = (road_x + road_speed) % (-W)
    screen.blit(current_bg, (0, 0))
    [screen.blit(road, (road_x + i, H // 2)) for i in (0, W)]
    [c.draw(screen, camera_x) for c in (player, enemy)]
    progress_bar_draw()
    pygame.draw.rect(screen, pause_bg_color, pause_bg_rect, border_radius=6)
    screen.blit(pause_surf, pause_rect)
    if player.boosting or player.energy < 100:
        boost_draw(player, H // 2 - 150)
    if enemy.boosting or enemy.energy < 100:
        boost_draw(enemy, H // 2 + 50)
    if game_over:
        txt = font.render(winner_text, 1, WHITE)
        screen.blit(txt, txt.get_rect(center=(W // 2, H // 2)))

# --- AI helper functions ---
def ai_settings_for_difficulty(diff):
    """
    Returns a dict of AI parameters for the given difficulty.
    Easy: slower, rare boosts, short boost duration
    Normal: baseline
    Hard: faster, frequent boosts, longer boost duration
    """
    if diff == "Easy":
        return {"speed_mult": 0.9, "boost_chance": 0.02, "boost_duration": 0.6, "reaction": 0.9}
    if diff == "Hard":
        return {"speed_mult": 1.15, "boost_chance": 0.12, "boost_duration": 1.6, "reaction": 0.6}
    # Normal
    return {"speed_mult": 1.0, "boost_chance": 0.06, "boost_duration": 1.0, "reaction": 0.75}

# --- Game update ---
def update(keys):
    global camera_x, game_over, winner_text, game_state, ai_difficulty
    if game_over:
        return

    # Player movement (human)
    def move(c, up, down, boost_key):
        # base movement
        c.rect.x += c.speed
        if keys[up]:
            c.rect.y -= 5
        if keys[down]:
            c.rect.y += 5

        # engine sound
        if not pygame.mixer.Channel(0).get_busy():
            try:
                pygame.mixer.Channel(0).play(c.engine, loops=-1)
            except Exception:
                pass

        # boost handling (human)
        if keys[boost_key] and c.energy > 0:
            c.speed, c.energy, c.boosting = c.boost_speed, max(0, c.energy - 0.8), True
            if not pygame.mixer.Channel(1).get_busy():
                try:
                    pygame.mixer.Channel(1).play(c.boost)
                except Exception:
                    pass
        else:
            c.speed, c.boosting = c.base_speed, False
            if pygame.mixer.Channel(1).get_busy():
                try:
                    pygame.mixer.Channel(1).stop()
                except Exception:
                    pass

        if not c.boosting:
            c.energy = min(100, c.energy + 0.3)
        clamp_to_road(c)

    # AI movement
    def ai_move(ai_car, target_car, diff):
        params = ai_settings_for_difficulty(diff)
        # speed scaling
        ai_car.base_speed = 4 * params["speed_mult"]
        ai_car.boost_speed = 8 * params["speed_mult"]

        # always advance
        ai_car.rect.x += ai_car.base_speed

        # simple vertical alignment: try to match player's y with some reaction delay
        if random.random() > params["reaction"]:
            if target_car.rect.y < ai_car.rect.y:
                ai_car.rect.y -= 3
            elif target_car.rect.y > ai_car.rect.y:
                ai_car.rect.y += 3

        # decide to boost: based on chance and distance to player
        dist = (target_car.rect.x - ai_car.rect.x)
        # if behind, more likely to boost
        behind_factor = 1.0 if dist > 0 else 0.6
        boost_prob = params["boost_chance"] * behind_factor

        # cooldown check
        now = time.time()
        if now - ai_car.last_boost_time < ai_car.boost_cooldown:
            # still cooling down
            pass
        else:
            if ai_car.energy > 10 and random.random() < boost_prob:
                # start boost
                ai_car.boosting = True
                ai_car.speed = ai_car.boost_speed
                ai_car.energy = max(0, ai_car.energy - 1.2 * params["boost_duration"] * 10)
                ai_car.last_boost_time = now
                ai_car.boost_cooldown = params["boost_duration"] + 0.8  # cooldown after boost
                # play boost sound
                try:
                    pygame.mixer.Channel(1).play(ai_car.boost)
                except Exception:
                    pass

        # if boosting, maintain boost for a short time then stop
        if ai_car.boosting:
            # reduce energy gradually
            ai_car.energy = max(0, ai_car.energy - 0.6)
            # small chance to stop boosting earlier
            if random.random() < 0.02:
                ai_car.boosting = False
                ai_car.speed = ai_car.base_speed
                try:
                    pygame.mixer.Channel(1).stop()
                except Exception:
                    pass
        else:
            ai_car.speed = ai_car.base_speed
            ai_car.energy = min(100, ai_car.energy + 0.3)

        clamp_to_road(ai_car)

    # apply movement
    move(player, pygame.K_UP, pygame.K_DOWN, pygame.K_b)

    if mode == "AI":
        # use ai_difficulty to control enemy
        ai_move(enemy, player, ai_difficulty)
    else:
        # Player 2 controls
        move(enemy, pygame.K_w, pygame.K_s, pygame.K_v)

    camera_x = max(0, min(player.rect.x - W // 2, MAP_LEN - W))

    # --- WIN CHECKS: set postrace state so menu always appears ---
    if player.rect.x >= MAP_LEN - player.rect.w:
        game_over = True
        winner_text = f"{player.name} WINS"
        game_state = "postrace"
        try:
            play_music(home_music)
        except Exception:
            pass

    if enemy.rect.x >= MAP_LEN - enemy.rect.w:
        game_over = True
        winner_text = f"{enemy.name} WINS"
        game_state = "postrace"
        try:
            play_music(home_music)
        except Exception:
            pass

# --- Countdown + mode selection ---
def countdown():
    for i in ["READY", "SET", "GO!"]:
        screen.fill(BLACK)
        txt = font.render(i, 1, WHITE)
        screen.blit(txt, txt.get_rect(center=(W // 2, H // 2)))
        pygame.display.flip()
        time.sleep(1)

def text_input(prompt):
    text = ""
    while True:
        screen.fill(BLACK)
        prompt_surf = font.render(prompt, 1, WHITE)
        screen.blit(prompt_surf, prompt_surf.get_rect(center=(W // 2, H // 2 - 100)))
        display_text = font.render(text[-25:], 1, (255, 215, 0))
        screen.blit(display_text, display_text.get_rect(center=(W // 2, H // 2)))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    return text.strip() or prompt
                elif e.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    text += e.unicode

def draw_options(options, start_x, start_y, spacing=50):
    rects = []
    for i, opt in enumerate(options):
        txt = sfont.render(opt, 1, WHITE)
        r = txt.get_rect(topleft=(start_x, start_y + i * spacing))
        screen.blit(txt, r)
        rects.append(r)
    return rects

def select_mode():
    """
    Presents mode selection and difficulty if AI chosen.
    Returns:
      (mode_str, ai_difficulty_str)
    mode_str: "AI" or "Player"
    ai_difficulty_str: "Easy"/"Normal"/"Hard" (only relevant if mode == "AI")
    """
    options = ["1. VS AI", "2. VS Player"]
    while True:
        screen.fill(BLACK)
        screen.blit(font.render("Choose Mode", 1, WHITE), (W // 2 - 200, H // 2 - 160))
        rects = draw_options(options, W // 2 - 100, H // 2 - 60, spacing=80)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    # AI chosen -> ask difficulty and names
                    diff = difficulty_menu()
                    if diff is None:
                        diff = "Normal"
                    name = text_input("Enter Player 1 Name")
                    return ("AI", diff, name, "AI")
                if e.key == pygame.K_2:
                    # Two player
                    name1 = text_input("Enter Player 1 Name")
                    name2 = text_input("Enter Player 2 Name")
                    return ("Player", "Normal", name1, name2)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if rects[0].collidepoint(mx, my):
                    diff = difficulty_menu()
                    if diff is None:
                        diff = "Normal"
                    name = text_input("Enter Player 1 Name")
                    return ("AI", diff, name, "AI")
                if rects[1].collidepoint(mx, my):
                    name1 = text_input("Enter Player 1 Name")
                    name2 = text_input("Enter Player 2 Name")
                    return ("Player", "Normal", name1, name2)

def difficulty_menu():
    """
    Simple difficulty selection menu.
    Returns "Easy", "Normal", or "Hard" or None if cancelled.
    """
    options = ["1. Easy", "2. Normal", "3. Hard", "4. Cancel"]
    while True:
        screen.fill(BLACK)
        screen.blit(font.render("Select AI Difficulty", 1, WHITE), (W // 2 - 300, 40))
        rects = draw_options(options, W // 2 - 150, 200)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    return "Easy"
                if e.key == pygame.K_2:
                    return "Normal"
                if e.key == pygame.K_3:
                    return "Hard"
                if e.key == pygame.K_4 or e.key == pygame.K_ESCAPE:
                    return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for i, r in enumerate(rects):
                    if r.collidepoint(mx, my):
                        if i == 0:
                            return "Easy"
                        if i == 1:
                            return "Normal"
                        if i == 2:
                            return "Hard"
                        if i == 3:
                            return None

# --- Map selection (single-click preview, double-click confirm) ---
def map_select_menu():
    """
    Returns:
      int -> chosen background index
      None -> user cancelled / wants to go back
    Single click previews; second click on same thumbnail within 0.6s confirms.
    """
    global current_bg_idx, current_bg
    thumb_start_x = W // 2 - 320
    thumb_start_y = 120
    gap = 20
    thumbs_per_row = 3

    last_click_idx = None
    last_click_time = 0.0
    confirm_timeout = 0.6  # seconds to allow second click to confirm

    while True:
        screen.fill(BLACK)
        screen.blit(font.render("CHOOSE MAP", 1, WHITE), (W // 2 - 200, 40))

        thumb_rects = []
        for i, thumb in enumerate(bg_thumbs):
            row = i // thumbs_per_row
            col = i % thumbs_per_row
            x = thumb_start_x + col * (thumb.get_width() + gap)
            y = thumb_start_y + row * (thumb.get_height() + 40)
            screen.blit(thumb, (x, y))
            label_num = sfont.render(str(i + 1), 1, WHITE)
            label_name = sfont.render(bg_display_names[i], 1, (200, 200, 200))
            screen.blit(label_num, (x + 4, y + thumb.get_height() + 4))
            screen.blit(label_name, (x + 28, y + thumb.get_height() + 4))
            r = pygame.Rect(x, y, thumb.get_width(), thumb.get_height())
            thumb_rects.append((r, i))

        # preview the currently selected background at the top-right
        preview = bg_images[current_bg_idx]
        preview_small = pygame.transform.smoothscale(preview, (300, 180))
        pygame.draw.rect(screen, (200, 200, 200), (W - 20 - 302, 18, 304, 184), 2)
        screen.blit(preview_small, (W - 20 - 300, 20))
        preview_label = sfont.render(f"Preview: {bg_display_names[current_bg_idx]}", 1, WHITE)
        screen.blit(preview_label, (W - 20 - 300, 20 + 180 + 8))

        instr = sfont.render("Click once to preview. Click again to confirm. ESC to cancel.", 1, (180, 180, 180))
        screen.blit(instr, (W // 2 - instr.get_width() // 2, H - 60))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return None
                if pygame.K_1 <= e.key <= pygame.K_9:
                    idx = e.key - pygame.K_1
                    if 0 <= idx < len(bg_images):
                        # keyboard selection behaves like double-click confirm
                        current_bg_idx = idx
                        current_bg = bg_images[current_bg_idx]
                        return idx
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                clicked_idx = None
                for r, idx in thumb_rects:
                    if r.collidepoint(mx, my):
                        clicked_idx = idx
                        break

                now = time.time()
                if clicked_idx is None:
                    # clicked outside thumbnails -> cancel / go back
                    return None

                # If clicked a thumbnail
                if clicked_idx != current_bg_idx:
                    # preview the newly clicked thumbnail
                    current_bg_idx = clicked_idx
                    current_bg = bg_images[current_bg_idx]
                    # reset last click tracking so user must click twice on same thumb to confirm
                    last_click_idx = clicked_idx
                    last_click_time = now
                    # continue loop to show preview
                    continue
                else:
                    # clicked the currently previewed thumbnail
                    # check if this is a quick second click to confirm
                    if last_click_idx == clicked_idx and (now - last_click_time) <= confirm_timeout:
                        # confirmed selection
                        logger.info(f"[BG SELECT] Confirmed background {clicked_idx + 1}: {bg_display_names[clicked_idx]}")
                        return clicked_idx
                    else:
                        # first click on this thumbnail (or timeout expired) -> set as preview and wait for second click
                        last_click_idx = clicked_idx
                        last_click_time = now
                        # keep preview visible; user must click again to confirm
                        continue

# --- Track length selection (lengths only) ---
def track_length_menu():
    """
    Returns:
      int -> chosen MAP_LEN in meters
      None -> user cancelled / wants to go back
    """
    maps = [
        "1. Short Track (5000m)",
        "2. Medium Track (20000m)",
        "3. Long Track (40000m)"
    ]
    map_lengths = [5000, 20000, 40000]

    while True:
        screen.fill(BLACK)
        screen.blit(font.render("CHOOSE TRACK LENGTH", 1, WHITE), (W // 2 - 300, 40))

        rects = draw_options(maps + ["4. Custom length (meters)", "5. Cancel"], W // 2 - 150, 160)

        instr = sfont.render("Choose length or press ESC to cancel. Click outside to go back.", 1, (180, 180, 180))
        screen.blit(instr, (W // 2 - instr.get_width() // 2, H - 60))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    return map_lengths[0]
                if e.key == pygame.K_2:
                    return map_lengths[1]
                if e.key == pygame.K_3:
                    return map_lengths[2]
                if e.key == pygame.K_4:
                    val = text_input("Enter track length in meters")
                    try:
                        m = int(val)
                        if m < 100:
                            m = 100
                        return m
                    except Exception:
                        pass
                if e.key == pygame.K_5 or e.key == pygame.K_ESCAPE:
                    return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for i, r in enumerate(rects[:3]):
                    if r.collidepoint(mx, my):
                        return map_lengths[i]
                if rects[3].collidepoint(mx, my):
                    val = text_input("Enter track length in meters")
                    try:
                        m = int(val)
                        if m < 100:
                            m = 100
                        return m
                    except Exception:
                        pass
                if rects[4].collidepoint(mx, my):
                    return None
                # clicking outside the options returns to previous menu
                if not any(r.collidepoint(mx, my) for r in rects):
                    return None

# --- Car selection menu ---
def car_select_menu(two_player=False):
    """
    Let the user pick cars before starting the race.
    Returns:
      (player_img, enemy_img) -> filenames chosen
      None -> cancelled
    """
    thumb_w, thumb_h = 160, 80
    cols = 4
    gap = 20
    start_x = (W - (cols * thumb_w + (cols - 1) * gap)) // 2
    start_y = 140

    # prebuild thumbs
    thumbs = [load_car_thumb(c["img"], (thumb_w, thumb_h)) for c in cars_list]
    selected_player = None
    selected_enemy = None
    selecting = "player"  # "player" or "enemy" or "done"

    while True:
        screen.fill(BLACK)
        screen.blit(font.render("CHOOSE CARS", 1, WHITE), (W // 2 - 200, 40))
        instr_text = "Select Player car, then select Opponent car. ESC to cancel."
        screen.blit(sfont.render(instr_text, 1, (200, 200, 200)), (W // 2 - 300, H - 60))

        rects = []
        for i, thumb in enumerate(thumbs):
            row = i // cols
            col = i % cols
            x = start_x + col * (thumb_w + gap)
            y = start_y + row * (thumb_h + 60)
            screen.blit(thumb, (x, y))
            label = sfont.render(cars_list[i]["name"], 1, WHITE)
            screen.blit(label, (x, y + thumb_h + 6))
            r = pygame.Rect(x, y, thumb_w, thumb_h)
            rects.append((r, i))

            # highlight selection
            if selected_player == i:
                pygame.draw.rect(screen, (0, 200, 0), (x-4, y-4, thumb_w+8, thumb_h+8), 3)
            if selected_enemy == i:
                pygame.draw.rect(screen, (200, 0, 0), (x-4, y-4, thumb_w+8, thumb_h+8), 3)

        # show which selection step
        step_label = sfont.render(f"Selecting: {selecting.upper()}", 1, (255, 215, 0))
        screen.blit(step_label, (W // 2 - step_label.get_width() // 2, 100))

        # confirm button
        confirm_txt = sfont.render("Click selected car again to confirm selection", 1, (180, 180, 180))
        screen.blit(confirm_txt, (W // 2 - confirm_txt.get_width() // 2, H - 100))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                clicked = None
                for r, idx in rects:
                    if r.collidepoint(mx, my):
                        clicked = idx
                        break
                if clicked is None:
                    continue

                if selecting == "player":
                    if selected_player == clicked:
                        # confirmed player car
                        selecting = "enemy"
                    else:
                        selected_player = clicked
                elif selecting == "enemy":
                    if selected_enemy == clicked:
                        # confirmed enemy car -> done
                        # return filenames
                        p_img = cars_list[selected_player]["img"] if selected_player is not None else cars_list[0]["img"]
                        e_img = cars_list[selected_enemy]["img"] if selected_enemy is not None else cars_list[1]["img"]
                        return (p_img, e_img)
                    else:
                        selected_enemy = clicked

# --- Main menu (Shop removed) ---
def main_menu():
    global game_state, MAP_LEN, new_race, mode, ai_difficulty, player, enemy
    play_music(home_music)
    options = ["1. Start Game", "2. Options", "3. Quit"]
    while game_state == "menu":
        screen.fill(BLACK)
        screen.blit(font.render("PIXEL VELOCITY", 1, WHITE), (W // 2 - 250, 100))
        rects = draw_options(options, W // 2 - 150, 250)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    # car selection first
                    sel = car_select_menu()
                    if sel is None:
                        continue
                    # apply chosen cars
                    try:
                        player.frames = [load_img(sel[0], (60, 120))]
                    except Exception:
                        player.frames = [load_img("Car_1.png", (60, 120))]
                    try:
                        enemy.frames = [load_img(sel[1], (60, 120))]
                    except Exception:
                        enemy.frames = [load_img("Car_2.png", (60, 120))]

                    # then mode selection (fix): ask mode and difficulty here
                    mode_result = select_mode()
                    if mode_result is None:
                        # user cancelled mode selection -> go back to menu
                        continue
                    # mode_result is (mode_str, diff, name1, name2_or_AI)
                    mode_str, diff, name1, name2 = mode_result
                    mode = mode_str
                    ai_difficulty = diff if mode == "AI" else "Normal"
                    # apply names
                    player.name = name1
                    enemy.name = name2

                    # then map and length selection
                    bg_idx = map_select_menu()
                    if bg_idx is None:
                        continue
                    chosen = track_length_menu()
                    if chosen is None:
                        continue
                    MAP_LEN = chosen
                    new_race = True
                    game_state = "game"
                    return
                if e.key == pygame.K_2:
                    game_state = "options"
                    return
                if e.key == pygame.K_3:
                    pygame.quit()
                    sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if rects[0].collidepoint(mx, my):
                    sel = car_select_menu()
                    if sel is None:
                        continue
                    try:
                        player.frames = [load_img(sel[0], (60, 120))]
                    except Exception:
                        player.frames = [load_img("Car_1.png", (60, 120))]
                    try:
                        enemy.frames = [load_img(sel[1], (60, 120))]
                    except Exception:
                        enemy.frames = [load_img("Car_2.png", (60, 120))]

                    mode_result = select_mode()
                    if mode_result is None:
                        continue
                    mode_str, diff, name1, name2 = mode_result
                    mode = mode_str
                    ai_difficulty = diff if mode == "AI" else "Normal"
                    player.name = name1
                    enemy.name = name2

                    bg_idx = map_select_menu()
                    if bg_idx is None:
                        continue
                    chosen = track_length_menu()
                    if chosen is None:
                        continue
                    MAP_LEN = chosen
                    new_race = True
                    game_state = "game"
                    return
                if rects[1].collidepoint(mx, my):
                    game_state = "options"
                    return
                if rects[2].collidepoint(mx, my):
                    pygame.quit()
                    sys.exit()

# --- Shop menu (left in place if you want to re-enable later) ---
def shop_menu():
    global money, game_state
    # kept for compatibility but not linked from main menu
    while game_state == "shop":
        screen.fill(BLACK)
        screen.blit(font.render("SHOP", 1, WHITE), (W // 2 - 100, 80))
        rects = []
        y = 200
        # show the first two as legacy shop items (costs kept)
        shop_items = [
            {"name": cars_list[0]["name"], "img": cars_list[0]["img"], "cost": 200},
            {"name": cars_list[1]["name"], "img": cars_list[1]["img"], "cost": 400},
        ]
        for i, c in enumerate(shop_items):
            txt = f"{i + 1}. {c['name']} - ${c['cost']}"
            surf = sfont.render(txt, 1, WHITE)
            r = surf.get_rect(topleft=(W // 2 - 150, y))
            screen.blit(surf, r)
            rects.append((r, i))
            y += 50
        money_txt = sfont.render(f"Money: ${money}", 1, (0, 255, 0))
        screen.blit(money_txt, (W // 2 - 150, y + 30))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_1, pygame.K_2):
                    idx = e.key - pygame.K_1
                    car = shop_items[idx]
                    if money >= car["cost"]:
                        money -= car["cost"]
                        player.frames = [load_img(car["img"], (60, 120))]
                if e.key == pygame.K_ESCAPE:
                    game_state = "menu"
                    return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                clicked_any = False
                for r, i in rects:
                    if r.collidepoint(mx, my):
                        clicked_any = True
                        car = shop_items[i]
                        if money >= car["cost"]:
                            money -= car["cost"]
                            player.frames = [load_img(car["img"], (60, 120))]
                if not clicked_any:
                    game_state = "menu"
                    return

def options_menu():
    global game_state
    music_volume, sfx_volume = 0.5, 0.5
    pygame.mixer.music.set_volume(music_volume)
    engine_sound_player.set_volume(sfx_volume)
    engine_sound_enemy.set_volume(sfx_volume)
    boost_sound_player.set_volume(sfx_volume)
    boost_sound_enemy.set_volume(sfx_volume)

    while game_state == "options":
        screen.fill(BLACK)
        screen.blit(font.render("OPTIONS", 1, WHITE), (W // 2 - 150, 80))
        screen.blit(sfont.render(f"Music Volume: {int(music_volume * 100)}%", 1, WHITE), (W // 2 - 150, 220))
        screen.blit(sfont.render(f"SFX Volume: {int(sfx_volume * 100)}%", 1, WHITE), (W // 2 - 150, 270))
        screen.blit(sfont.render("Up/Down = Music, Left/Right = SFX", 1, WHITE), (W // 2 - 150, 320))
        screen.blit(sfont.render("ESC or click anywhere to exit", 1, WHITE), (W // 2 - 150, 360))
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP:
                    music_volume = min(1.0, music_volume + 0.1)
                    pygame.mixer.music.set_volume(music_volume)
                if e.key == pygame.K_DOWN:
                    music_volume = max(0.0, music_volume - 0.1)
                    pygame.mixer.music.set_volume(music_volume)
                if e.key == pygame.K_RIGHT:
                    sfx_volume = min(1.0, sfx_volume + 0.1)
                if e.key == pygame.K_LEFT:
                    sfx_volume = max(1.0, sfx_volume - 0.1)

                engine_sound_player.set_volume(sfx_volume)
                engine_sound_enemy.set_volume(sfx_volume)
                boost_sound_player.set_volume(sfx_volume)
                boost_sound_enemy.set_volume(sfx_volume)

                if e.key == pygame.K_ESCAPE:
                    game_state = "menu"
                    return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                game_state = "menu"
                return

def pause_menu():
    global game_state
    play_music(pause_music)
    options = ["1. Resume", "2. Main Menu", "3. Quit"]
    while game_state == "pause":
        screen.fill(BLACK)
        screen.blit(font.render("PAUSED", 1, WHITE), (W // 2 - 150, 100))
        rects = draw_options(options, W // 2 - 150, 250)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    play_music(race_music)
                    game_state = "game"
                    return
                if e.key == pygame.K_2:
                    play_music(home_music)
                    reset_game_state()
                    game_state = "menu"
                    return
                if e.key == pygame.K_3:
                    pygame.quit()
                    sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if rects[0].collidepoint(mx, my):
                    play_music(race_music)
                    game_state = "game"
                    return
                if rects[1].collidepoint(mx, my):
                    play_music(home_music)
                    reset_game_state()
                    game_state = "menu"
                    return
                if rects[2].collidepoint(mx, my):
                    pygame.quit()
                    sys.exit()

def post_race_menu():
    global game_state, game_over, new_race, MAP_LEN
    play_music(home_music)
    options = ["1. Play Again", "2. Map Selection", "3. Main Menu", "4. Quit"]
    while game_state == "postrace":
        screen.fill(BLACK)
        screen.blit(font.render("RACE OVER", 1, WHITE), (W // 2 - 200, 100))
        screen.blit(sfont.render(winner_text, 1, (255, 215, 0)), (W // 2 - 200, 180))
        rects = draw_options(options, W // 2 - 150, 250)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    # Play again with same map/length
                    player.rect.x, player.rect.y = 200, H // 2 - 100
                    enemy.rect.x, enemy.rect.y = 200, H // 2 + 100
                    player.energy, enemy.energy = 100, 100
                    play_music(race_music)
                    game_state = "game"
                    game_over = False
                    new_race = False
                    return
                if e.key == pygame.K_2:
                    # Map selection flow: choose map then track length
                    bg_idx = map_select_menu()
                    if bg_idx is None:
                        continue
                    chosen = track_length_menu()
                    if chosen is None:
                        continue
                    MAP_LEN = chosen
                    # reset and start race
                    player.rect.x, player.rect.y = 200, H // 2 - 100
                    enemy.rect.x, enemy.rect.y = 200, H // 2 + 100
                    player.energy, enemy.energy = 100, 100
                    play_music(race_music)
                    game_state = "game"
                    game_over = False
                    new_race = True
                    return
                if e.key == pygame.K_3:
                    play_music(home_music)
                    reset_game_state()
                    game_state = "menu"
                    return
                if e.key == pygame.K_4:
                    pygame.quit()
                    sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if rects[0].collidepoint(mx, my):
                    player.rect.x, player.rect.y = 200, H // 2 - 100
                    enemy.rect.x, enemy.rect.y = 200, H // 2 + 100
                    player.energy, enemy.energy = 100, 100
                    play_music(race_music)
                    game_state = "game"
                    game_over = False
                    new_race = False
                    return
                if rects[1].collidepoint(mx, my):
                    bg_idx = map_select_menu()
                    if bg_idx is None:
                        continue
                    chosen = track_length_menu()
                    if chosen is None:
                        continue
                    MAP_LEN = chosen
                    player.rect.x, player.rect.y = 200, H // 2 - 100
                    enemy.rect.x, enemy.rect.y = 200, H // 2 + 100
                    player.energy, enemy.energy = 100, 100
                    play_music(race_music)
                    game_state = "game"
                    game_over = False
                    new_race = True
                    return
                if rects[2].collidepoint(mx, my):
                    play_music(home_music)
                    reset_game_state()
                    game_state = "menu"
                    return
                if rects[3].collidepoint(mx, my):
                    pygame.quit()
                    sys.exit()

# --- Main loop ---
def main_loop():
    global game_state, new_race, ai_difficulty
    play_music(home_music)
    while True:
        if game_state == "menu":
            main_menu()
        elif game_state == "options":
            options_menu()
        elif game_state == "shop":
            shop_menu()
        elif game_state == "game":
            # start race music if new race
            if new_race:
                play_music(race_music)
                new_race = False
                countdown()
            # game loop
            keys = pygame.key.get_pressed()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        game_state = "pause"
                        pause_menu()
                    if e.key == pygame.K_m:
                        # quick mode select (runtime change)
                        mode_result = select_mode()
                        if mode_result is not None:
                            mode_str, diff, name1, name2 = mode_result
                            # apply changes immediately
                            global mode
                            mode = mode_str
                            ai_difficulty = diff if mode == "AI" else "Normal"
                            player.name = name1
                            enemy.name = name2
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if pause_bg_rect.collidepoint(mx, my):
                        game_state = "pause"
                        pause_menu()

            update(keys)
            scene_draw()
            pygame.display.flip()
            clock.tick(60)
        elif game_state == "pause":
            pause_menu()
        elif game_state == "postrace":
            post_race_menu()
        else:
            # fallback to menu
            game_state = "menu"

if __name__ == "__main__":
    main_loop()

# End of modified script
