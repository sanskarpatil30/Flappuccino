import pygame, sys, time, random, colorsys, math, json, os
from pygame.math import Vector2
from pygame.locals import *
from player import Player
from background import Background
from button import Button
from bean import Bean
from utils import clamp, checkCollisions

class State:
    SPLASH  = "splash"
    TITLE   = "title"
    PLAYING = "playing"
    PAUSED  = "paused"
    DEAD    = "dead"

class Particle:
    def __init__(self, x, y, color, speed_range=(2, 6)):
        angle      = random.uniform(0, math.tau)
        speed      = random.uniform(*speed_range)
        self.pos   = Vector2(x, y)
        self.vel   = Vector2(math.cos(angle)*speed, math.sin(angle)*speed)
        self.color = color
        self.life  = 1.0
        self.size  = random.randint(3, 7)
    def update(self, dt):
        self.vel *= 0.90
        self.pos += self.vel * dt
        self.life -= 0.04 * dt
    def draw(self, surface):
        if self.life > 0:
            s = max(1, int(self.size * self.life))
            pygame.draw.rect(surface, (*self.color, int(self.life*255)),
                             (int(self.pos.x), int(self.pos.y), s, s))

class TrailDot:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.life  = 1.0
    def update(self, dt):
        self.life -= 0.05 * dt
    def draw(self, surface):
        if self.life > 0:
            r = max(1, int(4 * self.life))
            pygame.draw.circle(surface, (*self.color, int(self.life*180)),
                               (int(self.x), int(self.y)), r)

class Star:
    def __init__(self):
        self.x = random.randint(0, 640)
        self.y = random.randint(0, 480)
        self.size = random.randint(1, 3)
        self.brightness = random.uniform(0.3, 1.0)
        self.twinkle_speed = random.uniform(0.01, 0.04)
        self.parallax_factor = random.uniform(0.05, 0.2)

    def update(self, dt):
        self.brightness += self.twinkle_speed * dt
        if self.brightness >= 1.0:
            self.brightness = 1.0
            self.twinkle_speed *= -1
        elif self.brightness <= 0.1:
            self.brightness = 0.1
            self.twinkle_speed *= -1

    def draw(self, surface, night_intensity, cam_offset):
        # Wrap the Y position using modulo for infinite scrolling
        draw_y = (self.y + cam_offset * self.parallax_factor) % 480
        alpha = int(255 * self.brightness * night_intensity)
        pygame.draw.circle(surface, (255, 255, 255, alpha), (int(self.x), int(draw_y)), self.size)

class WindGust:
    WIDTH  = 80
    HEIGHT = 120
    def __init__(self, cam_y, screen_w, screen_h):
        side       = random.choice([-1, 1])
        self.force = side * random.uniform(1.5, 3.0)
        self.x     = random.randint(40, screen_w - self.WIDTH - 40)
        self.y     = cam_y - screen_h//2 - random.randint(50, screen_h)
        self.timer = random.randint(180, 320)
        self.alpha = 0
        self.fade_in = True
    def update(self, dt):
        self.timer -= dt
        if self.fade_in:
            self.alpha = min(160, self.alpha + 6*dt)
            if self.alpha >= 160:
                self.fade_in = False
        elif self.timer < 60:
            self.alpha = max(0, self.alpha - 4*dt)
    def draw(self, surface, cam_offset):
        draw_y = int(self.y + cam_offset)
        if draw_y > 480 or draw_y + self.HEIGHT < -100:
            return
        col = (100, 180, 255) if self.force > 0 else (255, 160, 80)
        s   = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        s.fill((*col, int(self.alpha * 0.4)))
        arrow_col = (*col, int(self.alpha))
        cx = self.WIDTH // 2
        for ay in [30, 60, 90]:
            dx = 18 if self.force > 0 else -18
            pygame.draw.line(s, arrow_col, (cx - dx, ay), (cx + dx, ay), 2)
            pts = ([(cx+dx-6, ay-5),(cx+dx, ay),(cx+dx-6, ay+5)] if self.force > 0
                   else [(cx+dx+6, ay-5),(cx+dx, ay),(cx+dx+6, ay+5)])
            pygame.draw.lines(s, arrow_col, False, pts, 2)
        surface.blit(s, (self.x, draw_y))
    def rect(self):
        return pygame.Rect(self.x, self.y, self.WIDTH, self.HEIGHT)
    def expired(self):
        return self.timer <= 0

class GoldenBean:
    VALUE   = 5
    RADIUS  = 10
    COLOR   = (255, 215, 0)
    OUTLINE = (200, 140, 0)
    def __init__(self, cam_y, screen_w, screen_h):
        self.x = random.randint(20, screen_w - 20)
        self.y = cam_y - screen_h//2 - random.randint(100, screen_h*2)
        self.bob_offset = random.uniform(0, math.tau)
    def draw(self, surface, cam_offset, t):
        bob_y = math.sin(t*3 + self.bob_offset) * 5
        cx = int(self.x)
        cy = int(self.y + cam_offset + bob_y)
        if -20 < cy < 500:
            glow = pygame.Surface((self.RADIUS*4, self.RADIUS*4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255,215,0,40), (self.RADIUS*2,self.RADIUS*2), self.RADIUS*2)
            surface.blit(glow, (cx - self.RADIUS*2, cy - self.RADIUS*2))
            pygame.draw.circle(surface, self.COLOR, (cx, cy), self.RADIUS)
            pygame.draw.circle(surface, self.OUTLINE, (cx, cy), self.RADIUS, 2)
            pygame.draw.circle(surface, (255,255,200), (cx-3, cy-3), 3)
    def collect_rect(self):
        return pygame.Rect(self.x - self.RADIUS, self.y - self.RADIUS,
                           self.RADIUS*2, self.RADIUS*2)

class CaffeineRush:
    DURATION = 300
    def __init__(self):
        self.active  = False
        self.timer   = 0
        self.charges = 0
    def activate(self):
        if self.charges > 0:
            self.active  = True
            self.timer   = self.DURATION
            self.charges -= 1
    def update(self, dt):
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False
    @property
    def progress(self):
        return self.timer / self.DURATION if self.active else 0.0

class Toast:
    def __init__(self, text, color=(255,240,180)):
        self.text  = text
        self.color = color
        self.timer = 130
    @property
    def alpha(self):
        if self.timer > 100:
            return int(255*(130-self.timer)/30)
        return int(255*min(1.0, self.timer/60))

SAVE_FILE = "save.json"
def load_high_score():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                return json.load(f).get("high_score", 0)
        except Exception:
            pass
    return 0
def save_high_score(score):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump({"high_score": score}, f)
    except Exception:
        pass

def reset_game(DISPLAY, player):
    player.velocity.xy   = 3, 0
    player.position.xy   = 295, 100
    player.currentSprite = player.rightSprite
    beans   = []
    buttons = []
    for _ in range(3):
        buttons.append(Button())
    buttons[0].typeIndicatorSprite = pygame.image.load('data/gfx/flap_indicator.png')
    buttons[0].price = 5
    buttons[1].typeIndicatorSprite = pygame.image.load('data/gfx/speed_indicator.png')
    buttons[1].price = 5
    buttons[2].typeIndicatorSprite = pygame.image.load('data/gfx/beanup_indicator.png')
    buttons[2].price = 30
    for i in range(5):
        beans.append(Bean())
    for bean in beans:
        bean.position.xy = (random.randrange(0, DISPLAY.get_width() - bean.sprite.get_width()),
                            beans.index(bean)*-200 - player.position.y)
    return dict(
        health=100, beanCount=0, height=0,
        flapForce=3.0, beanMultiplier=5,
        combo=0, combo_timer=0,
        particles=[], trail=[], toasts=[],
        shake=0.0, difficulty=1.0,
        rotOffset=-5,
        wind_gusts=[], wind_timer=0,
        golden_beans=[], golden_timer=0,
        caffeine=CaffeineRush(),
        beans=beans, buttons=buttons,
        startingHeight=player.position.y,
        day_timer=0.0,
        stars=[Star() for _ in range(60)]
    )

def main():
    pygame.init()
    DISPLAY = pygame.display.set_mode((640,480),0,32)
    pygame.display.set_caption('Flappuccino')
    pygame.display.set_icon(Bean().sprite)

    font       = pygame.font.Font('data/fonts/font.otf', 100)
    font_small = pygame.font.Font('data/fonts/font.otf', 32)
    font_20    = pygame.font.Font('data/fonts/font.otf', 20)
    font_14    = pygame.font.Font('data/fonts/font.otf', 14)

    shop         = pygame.image.load('data/gfx/shop.png')
    shop_bg      = pygame.image.load('data/gfx/shop_bg.png')
    retry_button = pygame.image.load('data/gfx/retry_button.png')
    logo         = pygame.image.load('data/gfx/logo.png')
    title_bg     = pygame.image.load('data/gfx/bg.png')
    title_bg.fill((255,30,0), special_flags=pygame.BLEND_ADD)
    shadow       = pygame.image.load('data/gfx/shadow.png')

    flapfx    = pygame.mixer.Sound("data/sfx/flap.wav")
    upgradefx = pygame.mixer.Sound("data/sfx/upgrade.wav")
    beanfx    = pygame.mixer.Sound("data/sfx/bean.wav")
    deadfx    = pygame.mixer.Sound("data/sfx/dead.wav")

    WHITE      = (255,255,255)
    player     = Player()
    high_score = load_high_score()
    state      = State.SPLASH
    last_time  = time.time()
    splashTimer = 0
    bg = [Background(), Background(), Background()]
    g  = reset_game(DISPLAY, player)
    MILESTONE_HEIGHTS  = {10, 25, 50, 100, 200, 500}
    reached_milestones = set()
    pygame.mixer.Sound.play(flapfx)

    while True:
        now      = time.time()
        dt       = min((now - last_time)*60, 3.5)
        last_time = now
        t         = now

        mouseX, mouseY = pygame.mouse.get_pos()
        jump    = False
        clicked = False

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == K_SPACE:
                    jump = True
                if event.key == K_ESCAPE:
                    if state == State.PLAYING:  state = State.PAUSED
                    elif state == State.PAUSED: state = State.PLAYING
                if event.key == K_r and state == State.PLAYING:
                    g['caffeine'].activate()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
                if mouseY < DISPLAY.get_height() - 90:
                    jump = True

        # SPLASH
        if state == State.SPLASH:
            splashTimer += dt
            DISPLAY.fill((231,205,183))
            msg = font_small.render("POLYMARS", True, (171,145,123))
            DISPLAY.blit(msg, (320 - msg.get_width()//2, 240 - msg.get_height()//2))
            pygame.display.update(); pygame.time.delay(10)
            if splashTimer >= 100:
                state = State.TITLE
                pygame.mixer.Sound.play(flapfx)
            continue

        # TITLE
        if state == State.TITLE:
            DISPLAY.fill(WHITE)
            DISPLAY.blit(title_bg,(0,0)); DISPLAY.blit(shadow,(0,0))
            DISPLAY.blit(logo,(320-logo.get_width()//2, 240-logo.get_height()//2+math.sin(t*5)*5-25))
            DISPLAY.blit(retry_button,(320-retry_button.get_width()//2,288))
            sm = font_small.render("START",True,(0,0,0))
            DISPLAY.blit(sm,(320-sm.get_width()//2,292))
            if high_score > 0:
                hs = font_20.render(f"Best: {high_score}m",True,(100,60,20))
                DISPLAY.blit(hs,(320-hs.get_width()//2,340))
            hint = font_14.render("R = caffeine rush  |  ESC = pause",True,(160,120,80))
            DISPLAY.blit(hint,(320-hint.get_width()//2,375))
            if clicked and checkCollisions(mouseX,mouseY,3,3,320-retry_button.get_width()//2,288,
                    retry_button.get_width(),retry_button.get_height()):
                pygame.mixer.Sound.play(upgradefx); state = State.PLAYING
            pygame.display.update(); pygame.time.delay(10); continue

        # PAUSED
        if state == State.PAUSED:
            DISPLAY.fill(WHITE)
            for o in bg: DISPLAY.blit(o.sprite,(0,o.position))
            ov = pygame.Surface((640,480),pygame.SRCALPHA); ov.fill((0,0,0,160))
            DISPLAY.blit(ov,(0,0))
            pm = font_small.render("PAUSED",True,(255,220,150))
            DISPLAY.blit(pm,(320-pm.get_width()//2,160))
            rm = font_20.render("Press ESC or click to resume",True,(255,255,255))
            DISPLAY.blit(rm,(320-rm.get_width()//2,220))
            hm = font_20.render(f"Height: {g['height']}m   Beans: {g['beanCount']}",True,(200,200,200))
            DISPLAY.blit(hm,(320-hm.get_width()//2,260))
            if clicked: state = State.PLAYING
            pygame.display.update(); pygame.time.delay(10); continue

        # Shared render setup
        hue      = ((player.position.y/50)%100)/100
        shake_x  = random.randint(-int(g['shake']),int(g['shake'])) if g['shake']>0 else 0
        shake_y  = random.randint(-int(g['shake']),int(g['shake'])) if g['shake']>0 else 0
        camOffset= (-player.position.y+DISPLAY.get_height()//2
                    -player.currentSprite.get_size()[1]//2+shake_y)
        rush_alpha = int(g['caffeine'].progress*60)

        DISPLAY.fill(WHITE)
        for o in bg:
            o.setSprite(hue)
            DISPLAY.blit(o.sprite,(shake_x,o.position))

        # --- DAY/NIGHT CYCLE & STARS ---
        progress = g['day_timer'] / 3000.0
        night_intensity = 0.0
        overlay_color = (0, 0, 0, 0)
        
        if 0.4 <= progress <= 0.6:   # Sunset to Night
            t = (progress - 0.4) / 0.2
            overlay_color = (int(255*(1-t)), int(100*(1-t)), 50, int(180*t))
            night_intensity = max(0, (progress - 0.45) / 0.15)
        elif 0.6 < progress < 0.8:   # Deep Night
            overlay_color = (0, 0, 50, 180)
            night_intensity = 1.0
        elif 0.8 <= progress <= 1.0: # Sunrise to Day
            t = (progress - 0.8) / 0.2
            overlay_color = (int(255*t), int(150*t), 50, int(180*(1-t)))
            night_intensity = max(0, 1.0 - t)

        # Apply the time-of-day tint
        if overlay_color[3] > 0:
            overlay = pygame.Surface((640, 480), pygame.SRCALPHA)
            overlay.fill(overlay_color)
            DISPLAY.blit(overlay, (0, 0))

        # Render stars when it's dark
        if night_intensity > 0:
            star_surf = pygame.Surface((640, 480), pygame.SRCALPHA)
            for star in g['stars']:
                star.update(dt)
                star.draw(star_surf, night_intensity, camOffset)
            DISPLAY.blit(star_surf, (0, 0))
        # -------------------------------

        if rush_alpha > 0:
            vig = pygame.Surface((640,480),pygame.SRCALPHA)
            vig.fill((255,210,0,rush_alpha))
            DISPLAY.blit(vig,(0,0))

        rgb = colorsys.hsv_to_rgb(hue,0.5,0.5)
        hsurf = font.render(str(g['height']),True,(int(rgb[0]*255),int(rgb[1]*255),int(rgb[2]*255)))
        DISPLAY.blit(hsurf,(320-hsurf.get_width()//2,
                    camOffset+round((player.position.y-g['startingHeight'])/DISPLAY.get_height())
                    *DISPLAY.get_height()+player.currentSprite.get_height()-40))

        for wg in g['wind_gusts']: wg.draw(DISPLAY,camOffset)
        for gb in g['golden_beans']: gb.draw(DISPLAY,camOffset,t)
        for bean in g['beans']:
            DISPLAY.blit(bean.sprite,(bean.position.x+shake_x,bean.position.y+camOffset))

        trail_surf = pygame.Surface((640,480),pygame.SRCALPHA)
        for td in g['trail']: td.draw(trail_surf)
        DISPLAY.blit(trail_surf,(0,0))

        rotated = pygame.transform.rotate(player.currentSprite,
                    clamp(player.velocity.y,-10,5)*g['rotOffset'])
        DISPLAY.blit(rotated,(player.position.x+shake_x,player.position.y+camOffset))

        psurf = pygame.Surface((640,480),pygame.SRCALPHA)
        for p in g['particles']: p.draw(psurf)
        DISPLAY.blit(psurf,(0,0))

        DISPLAY.blit(shop_bg,(0,0))
        pygame.draw.rect(DISPLAY,(81,48,20),(21,437,int(150*(g['health']/100)),25))
        DISPLAY.blit(shop,(0,0))

        for button in g['buttons']:
            bi = g['buttons'].index(button)
            bx = 220+bi*125
            DISPLAY.blit(button.sprite,(bx,393))
            DISPLAY.blit(font_small.render(str(button.price),True,(0,0,0)),(262+bi*125,408))
            DISPLAY.blit(font_20.render('Lvl. '+str(button.level),True,(200,200,200)),(234+bi*125,441))
            DISPLAY.blit(button.typeIndicatorSprite,(202+bi*125,377))
        DISPLAY.blit(font_small.render(str(g['beanCount']).zfill(7),True,(0,0,0)),(72,394))

        # Caffeine charge pips
        for ci in range(g['caffeine'].charges):
            col = (255,200,0) if not g['caffeine'].active else (255,140,0)
            pygame.draw.circle(DISPLAY,col,(12+ci*18,18),7)
            pygame.draw.circle(DISPLAY,(200,140,0),(12+ci*18,18),7,2)
        if g['caffeine'].active:
            bar_w = int(100*g['caffeine'].progress)
            pygame.draw.rect(DISPLAY,(255,200,0),(5,30,bar_w,6))
            pygame.draw.rect(DISPLAY,(200,140,0),(5,30,100,6),1)
        elif g['caffeine'].charges > 0:
            hint2 = font_14.render("R",True,(200,140,0))
            DISPLAY.blit(hint2,(12+g['caffeine'].charges*18+4,11))

        if g['combo'] >= 3:
            cs = font_small.render(f"x{g['combo']} COMBO!",True,(255,200,0))
            cs.set_alpha(int(255*min(1.0,g['combo_timer']/20)))
            DISPLAY.blit(cs,(320-cs.get_width()//2,50))

        for i,toast in enumerate(g['toasts']):
            ts = font_20.render(toast.text,True,toast.color)
            ts.set_alpha(toast.alpha)
            DISPLAY.blit(ts,(320-ts.get_width()//2,90+i*28))

        if g['height'] > high_score and state == State.PLAYING:
            pb = font_14.render("NEW BEST!",True,(255,215,0))
            DISPLAY.blit(pb,(DISPLAY.get_width()-pb.get_width()-10,10))

        # DEAD overlay
        if state == State.DEAD:
            ov = pygame.Surface((640,480),pygame.SRCALPHA); ov.fill((0,0,0,150))
            DISPLAY.blit(ov,(0,0))
            for surf,y in [
                (font_small.render("GAME OVER",True,(255,80,60)),120),
                (font_small.render(f"Height: {g['height']}m",True,(255,255,255)),175),
                (font_small.render(f"Beans: {g['beanCount']}",True,(255,255,255)),215),
                (font_small.render(f"Best: {high_score}m",True,
                    (255,215,0) if g['height']>=high_score else (180,180,180)),255),
            ]:
                DISPLAY.blit(surf,(320-surf.get_width()//2,y))
            retryX=320-retry_button.get_width()//2; retryY=308
            DISPLAY.blit(retry_button,(retryX,retryY))
            rm2 = font_small.render("RETRY",True,(0,0,0))
            DISPLAY.blit(rm2,(320-rm2.get_width()//2,retryY+4))
            if clicked and checkCollisions(mouseX,mouseY,3,3,retryX,retryY,
                    retry_button.get_width(),retry_button.get_height()):
                g=reset_game(DISPLAY,player); reached_milestones=set()
                pygame.mixer.Sound.play(upgradefx); state=State.PLAYING
            pygame.display.update(); pygame.time.delay(10); continue

        # PLAYING logic
        g['difficulty'] = 1.0+abs(player.position.y-g['startingHeight'])/(DISPLAY.get_height()*10)
        health_drain    = 0.18*g['difficulty']
        g['day_timer']  = (g['day_timer'] + dt) % 3000

        g['caffeine'].update(dt)
        rush_mult = 1.8 if g['caffeine'].active else 1.0

        if g['caffeine'].active:
            th = colorsys.hsv_to_rgb(hue,1,1)
            g['trail'].append(TrailDot(
                player.position.x+player.currentSprite.get_width()//2+shake_x,
                player.position.y+player.currentSprite.get_height()//2+camOffset,
                (int(th[0]*255),int(th[1]*255),int(th[2]*255))))

        g['wind_timer'] += dt
        wind_interval = max(200,350-int((g['difficulty']-1)*40))
        if g['wind_timer'] >= wind_interval:
            g['wind_timer'] = 0
            g['wind_gusts'].append(WindGust(player.position.y,640,480))

        for wg in g['wind_gusts'][:]:
            wg.update(dt)
            if wg.expired():
                g['wind_gusts'].remove(wg); continue
            wr = wg.rect()
            if checkCollisions(player.position.x,player.position.y,
                    player.currentSprite.get_width(),player.currentSprite.get_height(),
                    wr.x,wr.y,wr.w,wr.h):
                player.position.x += wg.force*dt*0.5
                player.position.x  = clamp(player.position.x,0,640-player.currentSprite.get_width())

        g['golden_timer'] += dt
        if g['golden_timer'] >= 400 and len(g['golden_beans']) < 2:
            g['golden_timer'] = 0
            g['golden_beans'].append(GoldenBean(player.position.y,640,480))

        for gb in g['golden_beans'][:]:
            if gb.y+camOffset > 540:
                g['golden_beans'].remove(gb); continue
            gr = gb.collect_rect()
            if checkCollisions(player.position.x,player.position.y,
                    player.currentSprite.get_width(),player.currentSprite.get_height(),
                    gr.x,gr.y,gr.w,gr.h):
                pygame.mixer.Sound.play(upgradefx)
                bonus = GoldenBean.VALUE*(2 if g['caffeine'].active else 1)
                g['beanCount'] += bonus
                g['health']     = min(100,g['health']+30)
                g['caffeine'].charges = min(3,g['caffeine'].charges+1)
                g['toasts'].append(Toast(f"GOLDEN BEAN  +{bonus}!",(255,215,0)))
                for _ in range(25):
                    g['particles'].append(Particle(gr.centerx,gr.centery+camOffset,
                                                   (255,215,0),(3,8)))
                g['golden_beans'].remove(gb)

        player.position.x += player.velocity.x*dt*rush_mult
        if player.position.x+player.currentSprite.get_size()[0] > 640:
            player.velocity.x=-abs(player.velocity.x); player.currentSprite=player.leftSprite; g['rotOffset']=5
        if player.position.x < 0:
            player.velocity.x=abs(player.velocity.x); player.currentSprite=player.rightSprite; g['rotOffset']=-5

        if jump:
            flap = g['flapForce']*(1.3 if g['caffeine'].active else 1.0)
            player.velocity.y = -flap
            pygame.mixer.Sound.play(flapfx)
        player.position.y += player.velocity.y*dt
        player.velocity.y  = clamp(player.velocity.y+player.acceleration*dt,-99999,50)

        g['health'] -= health_drain*dt
        if g['health'] <= 0:
            g['health']=0; state=State.DEAD; player.velocity.xy=0,0; g['shake']=12
            for _ in range(40):
                g['particles'].append(Particle(
                    player.position.x+player.currentSprite.get_width()//2,
                    player.position.y+player.currentSprite.get_height()//2+camOffset,(255,100,50)))
            pygame.mixer.Sound.play(deadfx)
            if g['height']>high_score: high_score=g['height']; save_high_score(high_score)

        for bean in g['beans']:
            if bean.position.y+camOffset+90 > DISPLAY.get_height():
                bean.position.y-=DISPLAY.get_height()*2
                bean.position.x =random.randrange(0,DISPLAY.get_width()-bean.sprite.get_width())
            if checkCollisions(player.position.x,player.position.y,
                    player.currentSprite.get_width(),player.currentSprite.get_height(),
                    bean.position.x,bean.position.y,bean.sprite.get_width(),bean.sprite.get_height()):
                pygame.mixer.Sound.play(beanfx)
                g['combo_timer']=70; g['combo']+=1
                bonus=max(1,g['combo']//3)*(2 if g['caffeine'].active else 1)
                g['beanCount']+=bonus; g['health']=min(100,g['health']+12)
                bean.position.y-=DISPLAY.get_height()-random.randrange(0,200)
                bean.position.x =random.randrange(0,DISPLAY.get_width()-bean.sprite.get_width())
                for _ in range(10):
                    g['particles'].append(Particle(
                        bean.position.x+bean.sprite.get_width()//2,
                        bean.position.y+bean.sprite.get_height()//2+camOffset,(200,140,80)))

        g['combo_timer']-=dt
        if g['combo_timer']<=0: g['combo']=0

        for p in g['particles'][:]:
            p.update(dt)
            if p.life<=0: g['particles'].remove(p)
        for td in g['trail'][:]:
            td.update(dt)
            if td.life<=0: g['trail'].remove(td)

        g['shake']=max(0.0,g['shake']-0.5*dt)

        for to in g['toasts'][:]:
            to.timer-=dt
            if to.timer<=0: g['toasts'].remove(to)

        g['height']=round(-(player.position.y-g['startingHeight'])/DISPLAY.get_height())
        for m in MILESTONE_HEIGHTS:
            if g['height']>=m and m not in reached_milestones:
                reached_milestones.add(m)
                g['toasts'].append(Toast(f"  {m}m reached!"))

        for button in g['buttons']:
            bi=g['buttons'].index(button); bx,by=220+bi*125,393
            if clicked and checkCollisions(mouseX,mouseY,3,3,bx,by,
                    button.sprite.get_width(),button.sprite.get_height()):
                if g['beanCount']>=button.price:
                    pygame.mixer.Sound.play(upgradefx)
                    button.level+=1; g['beanCount']-=button.price
                    button.price=round(button.price*2.5)
                    if bi==0: g['flapForce']*=1.5
                    elif bi==1: player.velocity.x*=1.5
                    elif bi==2:
                        g['beanMultiplier']+=10
                        for _ in range(g['beanMultiplier']):
                            nb=Bean()
                            nb.position.xy=(random.randrange(0,640-nb.sprite.get_width()),
                                player.position.y-480-random.randrange(0,200))
                            g['beans'].append(nb)

        bg[0].position=camOffset+round(player.position.y/DISPLAY.get_height())*DISPLAY.get_height()
        bg[1].position=bg[0].position+DISPLAY.get_height()
        bg[2].position=bg[0].position-DISPLAY.get_height()

        pygame.display.update()
        pygame.time.delay(10)

if __name__ == "__main__":
    main()