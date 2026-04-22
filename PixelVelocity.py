# Pixel Velocity — merged with per-car boost animation support (fixed boost animation index switching)
import os, pygame, sys, time, math, random, logging, glob
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
pygame.init()

# screen / fonts / globals
W, H = 1000, 600
screen = pygame.display.set_mode((W, H)); pygame.display.set_caption("Pixel Velocity")
clock = pygame.time.Clock(); font = pygame.font.SysFont("Arial", 72); sfont = pygame.font.SysFont("Arial", 28)
MAP_LEN = 20000; WHITE = (255, 255, 255); BLACK = (0, 0, 0)
camera_x = 0; game_over = False; winner_text = ""; mode = None
game_state = "menu"; money = 500; new_race = True
ai_difficulty = "Normal"

# minimal asset loader with fallback
def load_img(path, size=None, alpha=True):
    try:
        img = pygame.image.load(path); img = img.convert_alpha() if alpha else img.convert()
        return pygame.transform.smoothscale(img, size) if size else img
    except Exception:
        s = pygame.Surface(size if size else (60, 60)); s.fill((100, 100, 100)); return s

progress_bar = load_img("progress_bar.png", (500, 40))
boost_gauge = load_img("boost_circle.png", (120, 120))
player_frames = [load_img("Car_1.png", (60, 120))]; enemy_frames = [load_img("Car_2.png", (60, 120))]

# backgrounds (load safe)
bg_files = ["images/bg.png","images/bg2.png","images/bg3.png","images/bg4.png","images/bg5.png","images/bg6.png","images/bg7.png","images/bg8.png","images/bg9.png"]
bg_display_names = ["Default","Universal","End of the World","Western","Futuristic","Snow","Autumn","Spring","Volcanic"]
bg_images = []; bg_thumbs = []; thumb_w, thumb_h = 200, 120
for f in bg_files:
    if not os.path.exists(f):
        s = pygame.Surface((W, H)); s.fill((30, 30, 30)); bg_images.append(s)
        t = pygame.Surface((thumb_w, thumb_h)); t.fill((60, 60, 60)); bg_thumbs.append(t)
    else:
        try:
            full = pygame.image.load(f); full = full.convert() if hasattr(full, 'convert') else full.convert_alpha()
            bg_images.append(pygame.transform.smoothscale(full, (W, H)))
            t = pygame.image.load(f); t = t.convert() if hasattr(t, 'convert') else t.convert_alpha()
            bg_thumbs.append(pygame.transform.smoothscale(t, (thumb_w, thumb_h)))
        except Exception:
            s = pygame.Surface((W, H)); s.fill((30, 30, 30)); bg_images.append(s)
            t = pygame.Surface((thumb_w, thumb_h)); t.fill((60, 60, 60)); bg_thumbs.append(t)

current_bg_idx = 0; current_bg = bg_images[current_bg_idx]
road = load_img("images/road.png", (W, 450), False); road_x = 0; road_speed = -5

# audio (safe)
try:
    pygame.mixer.init()
    engine_sound_player = pygame.mixer.Sound("engine_player.wav")
    engine_sound_enemy = pygame.mixer.Sound("engine_enemy.wav")
    boost_sound_player = pygame.mixer.Sound("boost_player.wav")
    boost_sound_enemy = pygame.mixer.Sound("boost_enemy.wav")
except Exception:
    class Dummy:
        def play(self, *a, **k): pass
        def stop(self): pass
        def set_volume(self, v): pass
    engine_sound_player = engine_sound_enemy = boost_sound_player = boost_sound_enemy = Dummy()

home_music = "home_music.mp3"; race_music = "race_music.mp3"; pause_music = "pause_music.mp3"
def play_music(track, loop=-1):
    try:
        pygame.mixer.music.stop(); pygame.mixer.music.load(track); pygame.mixer.music.play(loop)
    except Exception: pass

# ---------------------------
# Animation loader utilities
# ---------------------------
def load_animation_frames_multi(base_name, size=(60,120), alpha=True):
    """
    Load files like 'Car_17_boost_0.png', 'Car_17_boost_1.png', ...
    Returns list of Surfaces or [] if none found.
    """
    base_root = os.path.splitext(base_name)[0]
    pattern = base_root + "_boost_*"
    files = sorted(glob.glob(pattern + ".*"))
    frames = []
    for f in files:
        try:
            frames.append(load_img(f, size, alpha))
        except Exception:
            pass
    return frames

def load_animation_frames_sheet(sheet_name, size=(60,120), alpha=True):
    """
    Load frames from a single image where frames are arranged horizontally.
    Returns [] if sheet not found or cannot be split.
    """
    if not os.path.exists(sheet_name):
        return []
    try:
        sheet = pygame.image.load(sheet_name)
        sheet = sheet.convert_alpha() if alpha else sheet.convert()
        sw, sh = sheet.get_size()
        fw, fh = size
        # If sheet height differs from requested frame height, use sheet height
        if sh != fh:
            fh = sh
            if fw > 0 and sw % fw != 0:
                cols = 1
                fw = sw
            else:
                cols = max(1, sw // fw)
        else:
            cols = max(1, sw // fw)
        frames = []
        for i in range(cols):
            rect = pygame.Rect(i * fw, 0, fw, fh)
            frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            if (fw, fh) != size:
                frame = pygame.transform.smoothscale(frame, size)
            frames.append(frame)
        return frames
    except Exception:
        return []

def load_animation_frames_for(base_name, size=(60,120), alpha=True):
    """
    Try multi-file boost frames first, then fallback to a sprite sheet named
    base_root + '_animation.png'. Returns [] if none found.
    """
    frames = load_animation_frames_multi(base_name, size, alpha)
    if frames:
        return frames
    base_root = os.path.splitext(base_name)[0]
    sheet_name = base_root + "_animation.png"
    frames = load_animation_frames_sheet(sheet_name, size, alpha)
    return frames

# ---------------------------
# Updated Car class with animation support (with fix)
# ---------------------------
class Car:
    def __init__(self, x, y, frames, name, color, engine, boost, source_img_name=None):
        # frames: list of surfaces for idle/default appearance (can be 1)
        self.idle_frames = frames[:]                # default idle frames
        self.rect = pygame.Rect(x, y, *self.idle_frames[0].get_size())
        self.name = name
        self.color = color
        self.engine = engine
        self.boost = boost

        # movement / energy
        self.speed = 4
        self.energy = 100
        self.boosting = False
        self.base_speed = 4
        self.boost_speed = 8
        self.boost_cooldown = 0.0
        self.last_boost_time = 0.0

        # animation state
        self.boost_frames = []                      # optional boost animation frames
        self.anim_index = 0.0                       # float to allow fractional frame advance
        self.anim_fps = 18.0                        # animation speed (frames per second)
        self.anim_loop = True                       # whether animation loops

        # track which frame list was used last update so we can reset index on change
        self._last_frames_id = None

        # try to auto-load boost/animation frames if a source filename is provided
        if source_img_name:
            self.boost_frames = load_animation_frames_for(source_img_name, size=self.idle_frames[0].get_size())

    def start_boost_animation(self, loop_while_holding=False):
        if self.boost_frames:
            self.anim_index = 0.0
            self.anim_loop = bool(loop_while_holding)
            # ensure the last frames id is reset so update_animation will rebase index
            self._last_frames_id = None

    def stop_boost_animation(self):
        self.anim_index = 0.0
        self.anim_loop = True
        # ensure the last frames id is reset so update_animation will rebase index
        self._last_frames_id = None

    def update_animation(self, dt):
        # choose the active frames based on boosting state
        frames = self.boost_frames if (self.boosting and self.boost_frames) else self.idle_frames
        if not frames:
            return

        # If the frame list changed since last update, reset/rebase anim_index
        current_id = id(frames)
        if self._last_frames_id is None or self._last_frames_id != current_id:
            # start from beginning to avoid big jumps when switching sets
            self.anim_index = 0.0
            self._last_frames_id = current_id

        # advance animation index
        self.anim_index += self.anim_fps * dt

        # keep anim_index in a sane range
        if self.anim_index >= len(frames):
            if self.anim_loop:
                # wrap around but keep it small to avoid huge ints
                self.anim_index = self.anim_index % len(frames)
            else:
                # clamp to last frame if not looping
                self.anim_index = float(len(frames) - 1)

    def current_frame(self):
        frames = self.boost_frames if (self.boosting and self.boost_frames) else self.idle_frames
        if not frames:
            return pygame.Surface((60,120))
        idx = int(self.anim_index)
        # safe clamp to avoid out-of-range indexing
        if idx < 0:
            idx = 0
        elif idx >= len(frames):
            idx = len(frames) - 1
        return frames[idx]

    def draw(self, surf, cx):
        surf.blit(self.current_frame(), (self.rect.x - cx, self.rect.y))
        surf.blit(sfont.render(self.name, 1, WHITE), (self.rect.x - cx, self.rect.y - 25))

# ---------------------------
# Create player and enemy with source filenames
# ---------------------------
player = Car(200, H//2-100, player_frames, "Player 1", (220,20,60), engine_sound_player, boost_sound_player, source_img_name="Car_1.png")
enemy  = Car(200, H//2+100, enemy_frames,  "Enemy",    (30,144,255), engine_sound_enemy, boost_sound_enemy, source_img_name="Car_2.png")

cars_list = [{"name": n, "img": f"Car_{i+1}.png"} for i, n in enumerate(["Speedster","Tank","Racer X","Phantom","Blaze","Comet","Vortex","Shadow","Aurora","Titan","Nebula","Cyclone","Mirage","Bolt","Drift","Specter","Inferno"])]

def load_car_thumb(img_name, size=(120,60)):
    try: return load_img(img_name, size)
    except Exception:
        t = pygame.Surface(size); t.fill((80,80,80)); return t

def swap_car_image(car, new_img_filename, size=(60,120)):
    """
    Replace car's idle image and auto-load boost/animation frames.
    Use this in menus where you previously set player.frames = [...]
    """
    try:
        car.idle_frames = [load_img(new_img_filename, size)]
        car.boost_frames = load_animation_frames_for(new_img_filename, size=car.idle_frames[0].get_size())
        car.rect.size = car.idle_frames[0].get_size()
        car.anim_index = 0.0
        car._last_frames_id = None
    except Exception:
        pass

def clamp_to_road(car):
    top, bottom = H//2, H//2+450-car.rect.height
    car.rect.y = max(top, min(car.rect.y, bottom))

# UI pause button
pause_surf = sfont.render("⏸ Pause", True, WHITE); pause_rect = pause_surf.get_rect(topright=(W-20,20))
pause_bg_color = (40,40,40); pause_bg_padding = 8
pause_bg_rect = pygame.Rect(pause_rect.left-pause_bg_padding, pause_rect.top-pause_bg_padding, pause_rect.width+pause_bg_padding*2, pause_rect.height+pause_bg_padding*2)

def reset_game_state():
    global game_over, new_race, camera_x, ai_difficulty, current_bg
    # Do NOT overwrite current_bg_idx or MAP_LEN here; keep whatever was selected.
    ai_difficulty = ai_difficulty  # keep existing difficulty
    game_over = False
    new_race = True
    camera_x = 0
    # position cars and reset energies/animations
    player.rect.x, player.rect.y = 200, H//2-100
    enemy.rect.x, enemy.rect.y = 200, H//2+100
    player.energy, enemy.energy = 100, 100
    player.boosting = enemy.boosting = False
    player.anim_index = 0.0; enemy.anim_index = 0.0
    player._last_frames_id = None; enemy._last_frames_id = None
    # ensure current background surface matches current_bg_idx
    try:
        current_bg = bg_images[current_bg_idx]
    except Exception:
        pass

def start_race_with_selection(selected_map_idx=None, selected_length=None, selected_mode="AI", selected_diff="Normal", p_name="Player 1", e_name="Enemy"):
    """
    Apply selections (map index and track length) then reset and start the race.
    Pass None for any selection you want to keep as-is.
    """
    global current_bg_idx, current_bg, MAP_LEN, mode, ai_difficulty, player, enemy, game_state

    # Apply map selection if provided
    if selected_map_idx is not None and 0 <= selected_map_idx < len(bg_images):
        current_bg_idx = selected_map_idx
        current_bg = bg_images[current_bg_idx]

    # Apply track length if provided
    if selected_length is not None and selected_length > 0:
        MAP_LEN = selected_length

    # Apply mode/difficulty and player names
    mode = selected_mode
    ai_difficulty = selected_diff
    player.name = p_name
    enemy.name = e_name

    # Reset positions and animation state without clobbering chosen map/length
    reset_game_state()

    # Start countdown and switch to race state
    game_state = "race"
    countdown()
    # play race music if you want
    try:
        play_music(race_music)
    except Exception:
        pass

# drawing helpers
def progress_bar_draw():
    bx = (W - progress_bar.get_width()) // 2; by = 20; screen.blit(progress_bar, (bx, by))
    screen.blit(sfont.render("START", 1, WHITE), (bx - sfont.size("START")[0] - 10, by))
    screen.blit(sfont.render("FINISH", 1, WHITE), (bx + progress_bar.get_width() + 10, by))
    for c in (player, enemy):
        pos = bx + (c.rect.x / MAP_LEN) * progress_bar.get_width()
        pygame.draw.circle(screen, c.color, (int(pos), by + progress_bar.get_height() // 2), 8)

def boost_draw(c, y):
    gx = W - boost_gauge.get_width() - 60; screen.blit(boost_gauge, (gx, y))
    rect = pygame.Rect(gx, y, boost_gauge.get_width(), boost_gauge.get_height()); ang = (c.energy / 100) * math.pi * 2
    color = (0,255,0) if c.energy > 70 else (255,165,0) if c.energy > 30 else (255,0,0)
    pygame.draw.arc(screen, color, rect, 0, ang, 6)

def scene_draw():
    global road_x, current_bg
    road_x = (road_x + road_speed) % (-W)
    screen.blit(current_bg, (0, 0)); [screen.blit(road, (road_x + i, H//2)) for i in (0, W)]
    [c.draw(screen, camera_x) for c in (player, enemy)]; progress_bar_draw()
    pygame.draw.rect(screen, pause_bg_color, pause_bg_rect, border_radius=6); screen.blit(pause_surf, pause_rect)
    if player.boosting or player.energy < 100: boost_draw(player, H//2-150)
    if enemy.boosting or enemy.energy < 100: boost_draw(enemy, H//2+50)
    if game_over:
        txt = font.render(winner_text, 1, WHITE)
        screen.blit(txt, txt.get_rect(center=(W//2, H//2)))

# AI settings
def ai_settings_for_difficulty(diff):
    if diff == "Easy": return {"speed_mult":0.9,"boost_chance":0.02,"boost_duration":0.6,"reaction":0.9}
    if diff == "Hard": return {"speed_mult":1.15,"boost_chance":0.12,"boost_duration":1.6,"reaction":0.6}
    return {"speed_mult":1.0,"boost_chance":0.06,"boost_duration":1.0,"reaction":0.75}

# ---------------------------
# Update (player + AI) — now accepts dt and advances animations
# ---------------------------
def update(keys, dt):
    global camera_x, game_over, winner_text, game_state, ai_difficulty
    if game_over: return
    def move(c, up, down, boost_key):
        c.rect.x += c.speed
        if keys[up]: c.rect.y -= 5
        if keys[down]: c.rect.y += 5
        try:
            if not pygame.mixer.Channel(0).get_busy(): pygame.mixer.Channel(0).play(c.engine, loops=-1)
        except Exception: pass
        if keys[boost_key] and c.energy > 0:
            if not c.boosting:
                c.start_boost_animation(loop_while_holding=True)
            c.speed, c.energy, c.boosting = c.boost_speed, max(0, c.energy - 0.8), True
            try:
                if not pygame.mixer.Channel(1).get_busy(): pygame.mixer.Channel(1).play(c.boost)
            except Exception: pass
        else:
            if c.boosting:
                c.stop_boost_animation()
            c.speed, c.boosting = c.base_speed, False
            try:
                if pygame.mixer.Channel(1).get_busy(): pygame.mixer.Channel(1).stop()
            except Exception: pass
        if not c.boosting: c.energy = min(100, c.energy + 0.3)
        clamp_to_road(c)
        c.update_animation(dt)

    def ai_move(ai_car, target_car, diff):
        params = ai_settings_for_difficulty(diff)
        ai_car.base_speed = 4 * params["speed_mult"]; ai_car.boost_speed = 8 * params["speed_mult"]
        ai_car.rect.x += ai_car.base_speed
        if random.random() > params["reaction"]:
            ai_car.rect.y += -3 if target_car.rect.y < ai_car.rect.y else 3 if target_car.rect.y > ai_car.rect.y else 0
        dist = (target_car.rect.x - ai_car.rect.x); behind_factor = 1.0 if dist > 0 else 0.6
        boost_prob = params["boost_chance"] * behind_factor; now = time.time()
        if now - ai_car.last_boost_time >= ai_car.boost_cooldown and ai_car.energy > 10 and random.random() < boost_prob:
            ai_car.boosting = True; ai_car.speed = ai_car.boost_speed
            ai_car.energy = max(0, ai_car.energy - 1.2 * params["boost_duration"] * 10)
            ai_car.last_boost_time = now; ai_car.boost_cooldown = params["boost_duration"] + 0.8
            try: pygame.mixer.Channel(1).play(ai_car.boost)
            except Exception: pass
            ai_car.start_boost_animation(loop_while_holding=True)
        if ai_car.boosting:
            ai_car.energy = max(0, ai_car.energy - 0.6)
            if random.random() < 0.02:
                ai_car.boosting = False; ai_car.speed = ai_car.base_speed
                try: pygame.mixer.Channel(1).stop()
                except Exception: pass
                ai_car.stop_boost_animation()
        else:
            ai_car.speed = ai_car.base_speed; ai_car.energy = min(100, ai_car.energy + 0.3)
        clamp_to_road(ai_car)
        ai_car.update_animation(dt)

    move(player, pygame.K_UP, pygame.K_DOWN, pygame.K_b)
    if mode == "AI": ai_move(enemy, player, ai_difficulty)
    else: move(enemy, pygame.K_w, pygame.K_s, pygame.K_v)
    camera_x = max(0, min(player.rect.x - W//2, MAP_LEN - W))

    if player.rect.x >= MAP_LEN - player.rect.w:
        game_over = True; winner_text = f"{player.name} WINS"; game_state = "postrace"; play_music(home_music)
    if enemy.rect.x >= MAP_LEN - enemy.rect.w:
        game_over = True; winner_text = f"{enemy.name} WINS"; game_state = "postrace"; play_music(home_music)

# UI / input helpers (unchanged)
def countdown():
    for i in ["READY", "SET", "GO!"]:
        screen.fill(BLACK); screen.blit(font.render(i, 1, WHITE), font.render(i, 1, WHITE).get_rect(center=(W//2, H//2)))
        pygame.display.flip(); time.sleep(1)

def text_input(prompt):
    text = ""
    while True:
        screen.fill(BLACK); screen.blit(font.render(prompt, 1, WHITE), (W//2 - font.size(prompt)[0]//2, H//2 - 100))
        screen.blit(font.render(text[-25:], 1, (255,215,0)), font.render(text[-25:], 1, (255,215,0)).get_rect(center=(W//2, H//2)))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN: return text.strip() or prompt
                if e.key == pygame.K_BACKSPACE: text = text[:-1]
                else: text += e.unicode

def draw_options(options, start_x, start_y, spacing=50):
    rects = []
    for i, opt in enumerate(options):
        txt = sfont.render(opt, 1, WHITE); r = txt.get_rect(topleft=(start_x, start_y + i*spacing)); screen.blit(txt, r); rects.append(r)
    return rects

# Menus and selection dialogs
def select_mode():
    options = ["1. VS AI", "2. VS Player"]
    while True:
        screen.fill(BLACK); screen.blit(font.render("Choose Mode", 1, WHITE), (W//2 - 200, H//2 - 160))
        rects = draw_options(options, W//2 - 100, H//2 - 60, spacing=80); pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    diff = difficulty_menu() or "Normal"; name = text_input("Enter Player 1 Name"); return ("AI", diff, name, "AI")
                if e.key == pygame.K_2:
                    n1 = text_input("Enter Player 1 Name"); n2 = text_input("Enter Player 2 Name"); return ("Player", "Normal", n1, n2)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if rects[0].collidepoint(mx, my):
                    diff = difficulty_menu() or "Normal"; name = text_input("Enter Player 1 Name"); return ("AI", diff, name, "AI")
                if rects[1].collidepoint(mx, my):
                    n1 = text_input("Enter Player 1 Name"); n2 = text_input("Enter Player 2 Name"); return ("Player", "Normal", n1, n2)

def difficulty_menu():
    options = ["1. Easy", "2. Normal", "3. Hard", "4. Cancel"]
    while True:
        screen.fill(BLACK); screen.blit(font.render("Select AI Difficulty", 1, WHITE), (W//2 - 300, 40))
        rects = draw_options(options, W//2 - 150, 200); pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: return "Easy"
                if e.key == pygame.K_2: return "Normal"
                if e.key == pygame.K_3: return "Hard"
                if e.key == pygame.K_4 or e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for i, r in enumerate(rects):
                    if r.collidepoint(mx, my):
                        return ["Easy", "Normal", "Hard", None][i]

def map_select_menu():
    global current_bg_idx, current_bg
    sx, sy = W//2 - 320, 120; gap = 20; per_row = 3
    last_click_idx = None; last_click_time = 0; timeout = 0.6
    scroll_y = 0; scroll_speed = 40
    rows = (len(bg_thumbs) + per_row - 1) // per_row
    content_h = sy + rows * (thumb_h + 40); visible_h = H - 160; max_scroll = max(0, content_h - visible_h)
    while True:
        screen.fill(BLACK); screen.blit(font.render("CHOOSE MAP", 1, WHITE), (W//2 - 200, 40))
        thumb_rects = []
        for i, thumb in enumerate(bg_thumbs):
            row = i // per_row; col = i % per_row
            x = sx + col * (thumb.get_width() + gap); y = sy + row * (thumb.get_height() + 40) - scroll_y
            if -thumb.get_height() < y < H - 80:
                screen.blit(thumb, (x, y)); screen.blit(sfont.render(str(i+1), 1, WHITE), (x+4, y+thumb.get_height()+4))
                screen.blit(sfont.render(bg_display_names[i], 1, (200,200,200)), (x+28, y+thumb.get_height()+4))
            thumb_rects.append((pygame.Rect(x, y, thumb.get_width(), thumb.get_height()), i))
        preview = pygame.transform.smoothscale(bg_images[current_bg_idx], (300, 180))
        pygame.draw.rect(screen, (200,200,200), (W-322, 18, 304, 184), 2); screen.blit(preview, (W-320, 20))
        screen.blit(sfont.render(f"Preview: {bg_display_names[current_bg_idx]}", 1, WHITE), (W-320, 20+180+8))
        screen.blit(sfont.render("Click once to preview. Click again to confirm. ESC to cancel.", 1, (180,180,180)), (W//2-260, H-60))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if pygame.K_1 <= e.key <= pygame.K_9:
                    idx = e.key - pygame.K_1
                    if 0 <= idx < len(bg_images): current_bg_idx = idx; current_bg = bg_images[idx]; return idx
                if e.key == pygame.K_UP: scroll_y = max(0, scroll_y - scroll_speed)
                if e.key == pygame.K_DOWN: scroll_y = min(max_scroll, scroll_y + scroll_speed)
                if e.key == pygame.K_PAGEUP: scroll_y = max(0, scroll_y - visible_h//2)
                if e.key == pygame.K_PAGEDOWN: scroll_y = min(max_scroll, scroll_y + visible_h//2)
            if e.type == pygame.MOUSEWHEEL: scroll_y = min(max_scroll, max(0, scroll_y - e.y*30))
            if e.type == pygame.MOUSEBUTTONDOWN and e.button in (4,5):
                scroll_y = max(0, scroll_y - 30) if e.button == 4 else min(max_scroll, scroll_y + 30)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos; clicked = None
                for r, i in thumb_rects:
                    if r.collidepoint(mx, my): clicked = i; break
                now = time.time()
                if clicked is None: return None
                if clicked != current_bg_idx:
                    current_bg_idx = clicked; current_bg = bg_images[clicked]; last_click_idx = clicked; last_click_time = now; continue
                else:
                    if last_click_idx == clicked and (now - last_click_time) <= timeout: return clicked
                    last_click_idx = clicked; last_click_time = now; continue

def track_length_menu():
    maps = ["1. Short Track (5000m)", "2. Medium Track (20000m)", "3. Long Track (40000m)"]
    lengths = [5000, 20000, 40000]
    while True:
        screen.fill(BLACK); screen.blit(font.render("CHOOSE TRACK LENGTH", 1, WHITE), (W//2 - 300, 40))
        rects = draw_options(maps + ["4. Custom length (meters)", "5. Cancel"], W//2 - 150, 160)
        screen.blit(sfont.render("Choose length or press ESC to cancel. Click outside to go back.", 1, (180,180,180)), (W//2 - 350, H-60))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: return lengths[0]
                if e.key == pygame.K_2: return lengths[1]
                if e.key == pygame.K_3: return lengths[2]
                if e.key == pygame.K_4:
                    val = text_input("Enter track length in meters")
                    try:
                        m = int(val); return max(100, m)
                    except Exception: pass
                if e.key == pygame.K_5 or e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for i, r in enumerate(rects[:3]):
                    if r.collidepoint(mx, my): return lengths[i]
                if rects[3].collidepoint(mx, my):
                    val = text_input("Enter track length in meters")
                    try: m = int(val); return max(100, m)
                    except Exception: pass
                if rects[4].collidepoint(mx, my): return None
                if not any(r.collidepoint(mx, my) for r in rects): return None

def car_select_menu(two_player=False):
    thumb_w, thumb_h, cols, gap = 160, 80, 4, 20
    start_x = (W - (cols * thumb_w + (cols - 1) * gap)) // 2; start_y = 140
    thumbs = [load_car_thumb(c["img"], (thumb_w, thumb_h)) for c in cars_list]
    sel_p = None; sel_e = None; selecting = "player"
    scroll_y = 0; scroll_speed = 40; rows = (len(thumbs) + cols - 1) // cols
    content_h = start_y + rows * (thumb_h + 60); visible_h = H - 200; max_scroll = max(0, content_h - visible_h)
    while True:
        screen.fill(BLACK); screen.blit(font.render("CHOOSE CARS", 1, WHITE), (W//2 - 200, 40))
        screen.blit(sfont.render("Select Player car, then select Opponent car. ESC to cancel.", 1, (200,200,200)), (W//2 - 300, H-60))
        rects = []
        for i, thumb in enumerate(thumbs):
            row = i // cols; col = i % cols
            x = start_x + col * (thumb_w + gap); y = start_y + row * (thumb_h + 60) - scroll_y
            if -thumb_h < y < H - 80:
                screen.blit(thumb, (x, y)); screen.blit(sfont.render(cars_list[i]["name"], 1, WHITE), (x, y + thumb_h + 6))
            r = pygame.Rect(x, y, thumb_w, thumb_h); rects.append((r, i))
            if sel_p == i: pygame.draw.rect(screen, (0,200,0), (x-4, y-4, thumb_w+8, thumb_h+8), 3)
            if sel_e == i: pygame.draw.rect(screen, (200,0,0), (x-4, y-4, thumb_w+8, thumb_h+8), 3)
        screen.blit(sfont.render(f"Selecting: {selecting.upper()}", 1, (255,215,0)), (W//2 - 100, 100))
        screen.blit(sfont.render("Click selected car again to confirm selection", 1, (180,180,180)), (W//2 - 250, H-100))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if e.key == pygame.K_UP: scroll_y = max(0, scroll_y - scroll_speed)
                if e.key == pygame.K_DOWN: scroll_y = min(max_scroll, scroll_y + scroll_speed)
                if e.key == pygame.K_PAGEUP: scroll_y = max(0, scroll_y - visible_h//2)
                if e.key == pygame.K_PAGEDOWN: scroll_y = min(max_scroll, scroll_y + visible_h//2)
            if e.type == pygame.MOUSEWHEEL: scroll_y = min(max_scroll, max(0, scroll_y - e.y*30))
            if e.type == pygame.MOUSEBUTTONDOWN and e.button in (4,5):
                scroll_y = max(0, scroll_y - 30) if e.button == 4 else min(max_scroll, scroll_y + 30)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos; clicked = None
                for r, i in rects:
                    if r.collidepoint(mx, my): clicked = i; break
                if clicked is None: continue
                if selecting == "player":
                    if sel_p == clicked: selecting = "enemy"
                    else: sel_p = clicked
                elif selecting == "enemy":
                    if sel_e == clicked:
                        p_img = cars_list[sel_p]["img"] if sel_p is not None else cars_list[0]["img"]
                        e_img = cars_list[sel_e]["img"] if sel_e is not None else cars_list[1]["img"]
                        return (p_img, e_img)
                    else: sel_e = clicked

# menus (main, shop, options, pause, postrace) — with swap_car_image used where appropriate
def main_menu():
    global game_state, MAP_LEN, new_race, mode, ai_difficulty, player, enemy, current_bg_idx, current_bg
    play_music(home_music)
    options = ["1. Start Game", "2. Options", "3. Quit"]
    while game_state == "menu":
        screen.fill(BLACK); screen.blit(font.render("PIXEL VELOCITY", 1, WHITE), (W//2 - 250, 100))
        rects = draw_options(options, W//2 - 150, 250); pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    # Car selection first
                    sel = car_select_menu()
                    if sel is None: continue
                    p_img, e_img = sel
                    # swap visuals for player/enemy
                    swap_car_image(player, p_img)
                    swap_car_image(enemy, e_img)

                    # Ask for map selection (preview then confirm)
                    chosen_map = map_select_menu()
                    # Ask for track length
                    chosen_length = track_length_menu()

                    # Ask for mode (AI vs Player) and names
                    chosen_mode, diff, p_name, e_name = select_mode()
                    # Normalize values:
                    if chosen_mode is None:
                        chosen_mode = "AI"
                    # Start the race applying the selections
                    start_race_with_selection(selected_map_idx=chosen_map, selected_length=chosen_length,
                                              selected_mode=("AI" if chosen_mode == "AI" else "Player"),
                                              selected_diff=diff or "Normal",
                                              p_name=p_name or player.name,
                                              e_name=e_name or enemy.name)
                if e.key == pygame.K_2:
                    # Options placeholder - you can expand this
                    pass
                if e.key == pygame.K_3:
                    pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # handle mouse clicks on menu options
                for i, r in enumerate(rects):
                    if r.collidepoint(mx, my):
                        if i == 0:
                            # Start Game (same flow as above)
                            sel = car_select_menu()
                            if sel is None: continue
                            p_img, e_img = sel
                            swap_car_image(player, p_img)
                            swap_car_image(enemy, e_img)
                            chosen_map = map_select_menu()
                            chosen_length = track_length_menu()
                            chosen_mode, diff, p_name, e_name = select_mode()
                            if chosen_mode is None:
                                chosen_mode = "AI"
                            start_race_with_selection(selected_map_idx=chosen_map, selected_length=chosen_length,
                                                      selected_mode=("AI" if chosen_mode == "AI" else "Player"),
                                                      selected_diff=diff or "Normal",
                                                      p_name=p_name or player.name,
                                                      e_name=e_name or enemy.name)
                        elif i == 1:
                            pass
                        elif i == 2:
                            pygame.quit(); sys.exit()

def pause_menu():
    play_music(pause_music)
    while True:
        screen.fill(BLACK); screen.blit(font.render("PAUSED", 1, WHITE), (W//2 - 150, H//2 - 80))
        screen.blit(sfont.render("Press P to resume or ESC to quit to menu", 1, (200,200,200)), (W//2 - 260, H//2 + 20))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p: play_music(race_music); return
                if e.key == pygame.K_ESCAPE:
                    play_music(home_music)
                    # return to main menu
                    global game_state
                    game_state = "menu"
                    return

def postrace_menu():
    global game_state
    while True:
        screen.fill(BLACK); screen.blit(font.render("RACE OVER", 1, WHITE), (W//2 - 220, 80))
        screen.blit(sfont.render(winner_text, 1, (255,215,0)), (W//2 - 100, 180))
        rects = draw_options(["1. Play Again", "2. Main Menu", "3. Quit"], W//2 - 150, 260)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    # restart with same settings
                    start_race_with_selection(selected_map_idx=current_bg_idx, selected_length=MAP_LEN, selected_mode=mode, selected_diff=ai_difficulty, p_name=player.name, e_name=enemy.name)
                    return
                if e.key == pygame.K_2:
                    game_state = "menu"; play_music(home_music); return
                if e.key == pygame.K_3:
                    pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for i, r in enumerate(rects):
                    if r.collidepoint(mx, my):
                        if i == 0:
                            start_race_with_selection(selected_map_idx=current_bg_idx, selected_length=MAP_LEN, selected_mode=mode, selected_diff=ai_difficulty, p_name=player.name, e_name=enemy.name)
                            return
                        if i == 1:
                            game_state = "menu"; play_music(home_music); return
                        if i == 2:
                            pygame.quit(); sys.exit()

# Main loop
def main_loop():
    global game_state, camera_x, game_over, winner_text
    # Start in menu
    while True:
        if game_state == "menu":
            main_menu()
        elif game_state == "race":
            dt = clock.tick(60) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        # go back to menu
                        game_state = "menu"; play_music(home_music)
                    if e.key == pygame.K_p:
                        pause_menu()
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if pause_bg_rect.collidepoint(mx, my):
                        pause_menu()
            keys = pygame.key.get_pressed()
            update(keys, dt)
            scene_draw()
            pygame.display.flip()
            if game_state == "postrace":
                postrace_menu()
        elif game_state == "postrace":
            postrace_menu()
        else:
            # fallback to menu
            game_state = "menu"

if __name__ == "__main__":
    try:
        main_loop()
    except Exception as ex:
        logging.exception("Unhandled exception in main loop: %s", ex)
        pygame.quit()
        raise
