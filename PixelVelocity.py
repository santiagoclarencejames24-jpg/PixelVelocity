import os, pygame, sys, time, math, random
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']="hide";

pygame.init()

# --- Screen setup ---
W, H = 1000, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Pixel Velocity")
clock, font, sfont = pygame.time.Clock(), pygame.font.SysFont("Arial",72), pygame.font.SysFont("Arial",28)

# --- Globals ---
MAP_LEN, WHITE, BLACK = 20000, (255,255,255), (0,0,0)
camera_x, game_over, winner_text, mode = 0, False, "", None
game_state, money, new_race = "menu", 500, True

# --- Assets ---
def load_img(path,size=None,alpha=True):
    img=pygame.image.load(path); img=img.convert_alpha() if alpha else img.convert()
    return pygame.transform.smoothscale(img,size) if size else img
progress_bar = load_img("progress_bar.png",(500,40))
boost_gauge  = load_img("boost_circle.png",(120,120))
player_frames=[load_img("Car_1.png",(60,120))]
enemy_frames=[load_img("Car_2.png",(60,120))]
bg,road=load_img("images/bg.png",(W,H),False),load_img("images/road.png",(W,450),False)
road_x,road_speed=0,-5

# --- Audio Setup ---
pygame.mixer.init()
engine_sound_player = pygame.mixer.Sound("engine_player.wav")
engine_sound_enemy  = pygame.mixer.Sound("engine_enemy.wav")
boost_sound_player  = pygame.mixer.Sound("boost_player.wav")
boost_sound_enemy   = pygame.mixer.Sound("boost_enemy.wav")

home_music   = "home_music.mp3"
race_music   = "race_music.mp3"
pause_music  = "pause_music.mp3"

def play_music(track, loop=-1):
    pygame.mixer.music.stop()
    pygame.mixer.music.load(track)
    pygame.mixer.music.play(loop)

# --- Car class ---
class Car:
    def __init__(self,x,y,frames,name,color,engine,boost):
        self.rect=pygame.Rect(x,y,*frames[0].get_size())
        self.frames,self.name,self.color=frames,name,color
        self.speed,self.energy,self.boosting=4,100,False
        self.engine,self.boost=engine,boost
    def draw(self,surf,cx):
        surf.blit(self.frames[0],(self.rect.x-cx,self.rect.y))
        surf.blit(sfont.render(self.name,1,WHITE),(self.rect.x-cx,self.rect.y-25))

player=Car(200,H//2-100,player_frames,"Player 1",(220,20,60),engine_sound_player,boost_sound_player)
enemy=Car(200,H//2+100,enemy_frames,"Enemy",(30,144,255),engine_sound_enemy,boost_sound_enemy)

# --- Shop Cars ---
cars_shop = [
    {"name":"Speedster","img":"Car_1.png","cost":200},
    {"name":"Tank","img":"Car_2.png","cost":400},
]

# --- Clamp cars to road ---
def clamp_to_road(car):
    top,bottom=H//2,H//2+450-car.rect.height
    car.rect.y=max(top,min(car.rect.y,bottom))

# --- UI ---
def progress_bar_draw():
    bar_x=(W-progress_bar.get_width())//2; bar_y=20
    screen.blit(progress_bar,(bar_x,bar_y))
    start_text = sfont.render("START", True, WHITE)
    finish_text = sfont.render("FINISH", True, WHITE)
    screen.blit(start_text, (bar_x - start_text.get_width() - 10, bar_y))
    screen.blit(finish_text, (bar_x + progress_bar.get_width() + 10, bar_y))
    for c in(player,enemy):
        pos=bar_x+(c.rect.x/MAP_LEN)*progress_bar.get_width()
        pygame.draw.circle(screen,c.color,(int(pos),bar_y+progress_bar.get_height()//2),8)

def boost_draw(c,y):
    gx = W - boost_gauge.get_width() - 60
    screen.blit(boost_gauge,(gx,y))
    rect = pygame.Rect(gx,y,boost_gauge.get_width(),boost_gauge.get_height())
    ang = (c.energy/100)*math.pi*2
    color = (0,255,0) if c.energy>70 else (255,165,0) if c.energy>30 else (255,0,0)
    pygame.draw.arc(screen,color,rect,0,ang,6)

def scene_draw():
    global road_x; road_x=(road_x+road_speed)%(-W)
    screen.blit(bg,(0,0)); [screen.blit(road,(road_x+i,H//2)) for i in(0,W)]
    [c.draw(screen,camera_x) for c in(player,enemy)]
    progress_bar_draw()
    if player.boosting or player.energy<100: boost_draw(player,H//2-150)
    if enemy.boosting or enemy.energy<100: boost_draw(enemy,H//2+50)
    if game_over: screen.blit(font.render(winner_text,1,WHITE),font.render(winner_text,1,WHITE).get_rect(center=(W//2,H//2)))

# --- Game update ---
def update(keys):
    global camera_x,game_over,winner_text
    if game_over: return
    def move(c,up,down,boost):
        c.rect.x+=c.speed
        if keys[up]: c.rect.y-=5
        if keys[down]: c.rect.y+=5

        if not pygame.mixer.Channel(0).get_busy():
            pygame.mixer.Channel(0).play(c.engine, loops=-1)

        if keys[boost] and c.energy>0:
            c.speed,c.energy,c.boosting=8,max(0,c.energy-0.8),True
            if not pygame.mixer.Channel(1).get_busy():
                pygame.mixer.Channel(1).play(c.boost)
        else:
            c.speed,c.boosting=4,False
            if pygame.mixer.Channel(1).get_busy():
                pygame.mixer.Channel(1).stop()

        if not c.boosting: c.energy=min(100,c.energy+0.3)
        clamp_to_road(c)

    move(player,pygame.K_UP,pygame.K_DOWN,pygame.K_b)
    if mode=="AI":
        enemy.rect.x+=enemy.speed
        clamp_to_road(enemy)
    else: move(enemy,pygame.K_w,pygame.K_s,pygame.K_v)

    camera_x=max(0,min(player.rect.x-W//2,MAP_LEN-W))
    if player.rect.x>=MAP_LEN-player.rect.w: game_over,winner_text=True,f"{player.name} WINS"
    if enemy.rect.x>=MAP_LEN-enemy.rect.w: game_over,winner_text=True,f"{enemy.name} WINS"

# --- Countdown + mode selection ---
def countdown():
    for i in["READY","SET","GO!"]:
        screen.fill(BLACK)
        screen.blit(font.render(i,1,WHITE),font.render(i,1,WHITE).get_rect(center=(W//2,H//2)))
        pygame.display.flip(); time.sleep(1)

def text_input(prompt):
    text=""
    while True:
        screen.fill(BLACK)
        screen.blit(font.render(prompt,1,WHITE),font.render(prompt,1,WHITE).get_rect(center=(W//2,H//2-100)))
        screen.blit(font.render(text[-25:],1,(255,215,0)),font.render(text[-25:],1,(255,215,0)).get_rect(center=(W//2,H//2)))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_RETURN: return text.strip() or prompt
                elif e.key==pygame.K_BACKSPACE: text=text[:-1]
                else: text+=e.unicode

def select_mode():
    global mode
    while True:
        screen.fill(BLACK)
        screen.blit(font.render("Press 1: VS AI",1,WHITE),(W//2-200,H//2-100))
        screen.blit(font.render("Press 2: VS Player",1,WHITE),(W//2-200,H//2+50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1: mode="AI"; player.name=text_input("Enter Player 1 Name"); enemy.name="AI"; return
                if e.key==pygame.K_2: mode="Player"; player.name=text_input("Enter Player 1 Name"); enemy.name=text_input("Enter Player 2 Name"); return

# --- Menus ---
# (main_menu, shop_menu, options_menu, map_menu, pause_menu, post_race_menu)
# [Keep your existing menu definitions here — unchanged except for adding play_music(home_music), play_music(race_music), play_music(pause_music) where needed]

# --- Menus ---
def main_menu():
    global game_state
    play_music(home_music)   # Home screen music
    while game_state=="menu":
        screen.fill(BLACK)
        screen.blit(font.render("PIXEL VELOCITY",1,WHITE),(W//2-250,100))
        options=["1. Start Game","2. Choose Map","3. Shop","4. Options","5. Quit"]
        for i,opt in enumerate(options): screen.blit(sfont.render(opt,1,WHITE),(W//2-150,250+i*50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1: game_state="game"; return
                if e.key==pygame.K_2: game_state="map"; return
                if e.key==pygame.K_3: game_state="shop"; return
                if e.key==pygame.K_4: game_state="options"; return
                if e.key==pygame.K_5: pygame.quit(); sys.exit()

def shop_menu():
    global money, game_state
    while game_state=="shop":
        screen.fill(BLACK)
        screen.blit(font.render("SHOP",1,WHITE),(W//2-100,80))
        y=200
        for i,c in enumerate(cars_shop):
            txt=f"{i+1}. {c['name']} - ${c['cost']}"
            screen.blit(sfont.render(txt,1,WHITE),(W//2-150,y)); y+=50
        screen.blit(sfont.render(f"Money: ${money}",1,(0,255,0)),(W//2-150,y+30))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key in (pygame.K_1,pygame.K_2):
                    idx=e.key-pygame.K_1
                    car=cars_shop[idx]
                    if money>=car["cost"]:
                        money-=car["cost"]
                        newcar=load_img(car["img"],(60,120))
                        player.frames=[newcar]
                if e.key==pygame.K_ESCAPE: game_state="menu"; return

def options_menu():
    global game_state
    music_volume, sfx_volume = 0.5, 0.5
    pygame.mixer.music.set_volume(music_volume)
    engine_sound_player.set_volume(sfx_volume)
    engine_sound_enemy.set_volume(sfx_volume)
    boost_sound_player.set_volume(sfx_volume)
    boost_sound_enemy.set_volume(sfx_volume)

    while game_state=="options":
        screen.fill(BLACK)
        screen.blit(font.render("OPTIONS",1,WHITE),(W//2-150,80))
        screen.blit(sfont.render(f"Music Volume: {int(music_volume*100)}%",1,WHITE),(W//2-150,220))
        screen.blit(sfont.render(f"SFX Volume: {int(sfx_volume*100)}%",1,WHITE),(W//2-150,270))
        screen.blit(sfont.render("Up/Down = Music, Left/Right = SFX",1,WHITE),(W//2-150,320))
        screen.blit(sfont.render("ESC to exit",1,WHITE),(W//2-150,360))
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_UP: music_volume=min(1.0,music_volume+0.1); pygame.mixer.music.set_volume(music_volume)
                if e.key==pygame.K_DOWN: music_volume=max(0.0,music_volume-0.1); pygame.mixer.music.set_volume(music_volume)
                if e.key==pygame.K_RIGHT: sfx_volume=min(1.0,sfx_volume+0.1)
                if e.key==pygame.K_LEFT: sfx_volume=max(0.0,sfx_volume-0.1)

                engine_sound_player.set_volume(sfx_volume)
                engine_sound_enemy.set_volume(sfx_volume)
                boost_sound_player.set_volume(sfx_volume)
                boost_sound_enemy.set_volume(sfx_volume)

                if e.key==pygame.K_ESCAPE: game_state="menu"; return

def map_menu():
    global MAP_LEN, game_state
    while game_state=="map":
        screen.fill(BLACK)
        screen.blit(font.render("CHOOSE MAP",1,WHITE),(W//2-200,80))
        maps=["1. Short Track (5000m)","2. Medium Track (20000m)","3. Long Track (40000m)"]
        for i,m in enumerate(maps): screen.blit(sfont.render(m,1,WHITE),(W//2-200,200+i*50))
        screen.blit(sfont.render("ESC to return",1,WHITE),(W//2-200,400))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1: MAP_LEN=5000; game_state="menu"; return
                if e.key==pygame.K_2: MAP_LEN=20000; game_state="menu"; return
                if e.key==pygame.K_3: MAP_LEN=40000; game_state="menu"; return
                if e.key==pygame.K_ESCAPE: game_state="menu"; return

# --- Pause and Post-Race Menus ---
def pause_menu():
    global game_state
    play_music(pause_music)
    while game_state=="pause":
        screen.fill(BLACK)
        screen.blit(font.render("PAUSED",1,WHITE),(W//2-150,100))
        options=["1. Resume","2. Main Menu","3. Quit"]
        for i,opt in enumerate(options):
            screen.blit(sfont.render(opt,1,WHITE),(W//2-150,250+i*50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1:
                    play_music(race_music)
                    game_state="game"; return
                if e.key==pygame.K_2:
                    play_music(home_music)
                    game_state="menu"; return
                if e.key==pygame.K_3: pygame.quit(); sys.exit()

def post_race_menu():
    global game_state, game_over, new_race
    play_music(home_music)
    while game_state=="postrace":
        screen.fill(BLACK)
        screen.blit(font.render("RACE OVER",1,WHITE),(W//2-200,100))
        screen.blit(sfont.render(winner_text,1,(255,215,0)),(W//2-200,180))
        options=["1. Play Again","2. Main Menu","3. Quit"]
        for i,opt in enumerate(options):
            screen.blit(sfont.render(opt,1,WHITE),(W//2-150,250+i*50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1:
                    player.rect.x, player.rect.y = 200, H//2-100
                    enemy.rect.x, enemy.rect.y = 200, H//2+100
                    player.energy, enemy.energy = 100, 100
                    play_music(race_music)
                    game_state="game"; game_over=False; new_race=True; return
                if e.key==pygame.K_2:
                    play_music(home_music)
                    game_state="menu"; game_over=False; return
                if e.key==pygame.K_3: pygame.quit(); sys.exit()

# --- Main Loop ---
while True:
    if game_state=="menu":
        main_menu()
    elif game_state=="map":
        map_menu()
    elif game_state=="shop":
        shop_menu()
    elif game_state=="options":
        options_menu()
    elif game_state=="pause":
        pause_menu()
    elif game_state=="postrace":
        post_race_menu()
    elif game_state=="game":
        if new_race:
            select_mode()
            countdown()
            play_music(race_music)   # Race background music
            new_race=False
        while game_state=="game":
            for e in pygame.event.get():
                if e.type==pygame.QUIT: pygame.quit(); sys.exit()
                if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE:
                    game_state="pause"
            update(pygame.key.get_pressed())
            scene_draw(); pygame.display.flip(); clock.tick(60)
            if game_over:
                game_state="postrace"
