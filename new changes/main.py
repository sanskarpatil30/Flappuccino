import pygame, sys, time, random, colorsys, math, json, os
from pygame.math import Vector2
from pygame.locals import *
from player import Player
from background import Background
from button import Button
from bean import Bean
from utils import clamp, checkCollisions

# ─────────────────────────── STATES ───────────────────────────
class State:
    SPLASH  = "splash"
    TITLE   = "title"
    PLAYING = "playing"
    PAUSED  = "paused"
    DYING   = "dying"   # fall animation before game over screen
    DEAD    = "dead"

# ─────────────────────────── PARTICLES ────────────────────────
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

# ─────────────────────────── WIND GUST ────────────────────────
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

# ─────────────────────────── GOLDEN BEAN ──────────────────────
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

# ─────────────────────────── CAFFEINE RUSH ────────────────────
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

# ─────────────────────────── TOAST ────────────────────────────
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

# ─────────────────────────── FLOATING TEXT ────────────────────
class FloatingText:
    """Visual Polish: +1/+5 floats up from collected bean."""
    def __init__(self, text, x, y, color):
        self.text  = text
        self.x     = x
        self.y     = float(y)
        self.color = color
        self.life  = 1.0
    def update(self, dt):
        self.y  -= 1.2 * dt
        self.life -= 0.025 * dt
    def draw(self, surface, font):
        if self.life > 0:
            s = font.render(self.text, True, self.color)
            s.set_alpha(int(self.life * 255))
            surface.blit(s, (int(self.x - s.get_width()//2), int(self.y)))

# ─────────────────────────── BACKGROUND BUBBLE ────────────────
class BgBubble:
    """Visual Polish: soft foam circles drift upward in bg."""
    def __init__(self, screen_w, screen_h):
        self.x     = random.randint(0, screen_w)
        self.y     = float(random.randint(0, screen_h))
        self.r     = random.randint(8, 28)
        self.speed = random.uniform(0.3, 1.0)
        self.alpha = random.randint(20, 60)
        self.color = (255, 255, 255)
    def update(self, dt):
        self.y -= self.speed * dt
    def reset(self, screen_w, screen_h):
        self.x     = random.randint(0, screen_w)
        self.y     = float(screen_h + self.r)
        self.r     = random.randint(8, 28)
        self.speed = random.uniform(0.3, 1.0)
    def draw(self, surface):
        s = pygame.Surface((self.r*2+2, self.r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, self.alpha), (self.r+1, self.r+1), self.r)
        pygame.draw.circle(s, (*self.color, self.alpha+30), (self.r+1, self.r+1), self.r, 2)
        surface.blit(s, (int(self.x - self.r), int(self.y - self.r)))

# ─────────────────────────── PARALLAX CLOUD ───────────────────
class ParallaxCloud:
    """Visual Polish: 3 layers of clouds at different speeds."""
    def __init__(self, layer, screen_w, screen_h):
        # layer 0 = far (slow), 1 = mid, 2 = near (fast)
        self.layer  = layer
        self.x      = float(random.randint(0, screen_w))
        self.y      = float(random.randint(-screen_h, screen_h))
        self.w      = random.randint(60, 140) - layer*10
        self.h      = random.randint(20, 50)  - layer*5
        self.speed  = [0.2, 0.5, 1.0][layer]
        self.alpha  = [50, 80, 110][layer]
        self.color  = (255, 255, 255)
    def update(self, cam_dy, dt):
        """cam_dy: how much camera moved this frame (upward = positive)."""
        self.y += cam_dy * self.speed
    def draw(self, surface):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*self.color, self.alpha), (0, 0, self.w, self.h))
        surface.blit(s, (int(self.x), int(self.y)))

# ─────────────────────────── BEAN MAGNET ──────────────────────
class BeanMagnet:
    """Game Feel: rare pickup that sucks nearby beans toward player for 5s."""
    RADIUS  = 8
    COLOR   = (180, 80, 220)
    OUTLINE = (120, 30, 180)
    DURATION = 300  # frames

    def __init__(self, cam_y, screen_w, screen_h):
        self.x = random.randint(20, screen_w - 20)
        self.y = cam_y - screen_h//2 - random.randint(100, screen_h*2)
        self.bob_offset = random.uniform(0, math.tau)
        self.active  = False
        self.timer   = 0

    def draw_pickup(self, surface, cam_offset, t):
        bob_y = math.sin(t*4 + self.bob_offset) * 6
        cx = int(self.x)
        cy = int(self.y + cam_offset + bob_y)
        if -20 < cy < 500:
            glow = pygame.Surface((self.RADIUS*4, self.RADIUS*4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*self.COLOR, 50), (self.RADIUS*2, self.RADIUS*2), self.RADIUS*2)
            surface.blit(glow, (cx - self.RADIUS*2, cy - self.RADIUS*2))
            pygame.draw.circle(surface, self.COLOR, (cx, cy), self.RADIUS)
            pygame.draw.circle(surface, self.OUTLINE, (cx, cy), self.RADIUS, 2)
            # M-shape
            pts = [(cx-5,cy+4),(cx-5,cy-4),(cx,cy+1),(cx+5,cy-4),(cx+5,cy+4)]
            pygame.draw.lines(surface, (255,255,255), False, pts, 2)

    def collect_rect(self):
        return pygame.Rect(self.x - self.RADIUS, self.y - self.RADIUS,
                           self.RADIUS*2, self.RADIUS*2)

    def activate(self):
        self.active = True
        self.timer  = self.DURATION

    def update(self, dt):
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False

    @property
    def progress(self):
        return self.timer / self.DURATION if self.active else 0.0

# ─────────────────────────── BEAN CLOUD ZONE ──────────────────
class BeanCloudZone:
    """Depth: rare cluster of 20+ beans in a glowing bubble."""
    def __init__(self, cam_y, screen_w, screen_h):
        self.cx = random.randint(100, screen_w - 100)
        self.cy = cam_y - screen_h//2 - random.randint(200, screen_h*2)
        self.radius = random.randint(60, 90)
        self.beans = []
        count = random.randint(20, 28)
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            r     = random.uniform(0, self.radius * 0.85)
            self.beans.append(Vector2(self.cx + math.cos(angle)*r,
                                      self.cy + math.sin(angle)*r))
        self.active   = True
        self.bob_t    = random.uniform(0, math.tau)

    def draw(self, surface, cam_offset, t, bean_sprite):
        if not self.active:
            return
        cy = int(self.cy + cam_offset)
        if cy < -200 or cy > 700:
            return
        bob = math.sin(t * 2 + self.bob_t) * 4
        # Glowing bubble
        glow = pygame.Surface((self.radius*2+40, self.radius*2+40), pygame.SRCALPHA)
        pulse = int(30 + 20 * math.sin(t*3))
        pygame.draw.circle(glow, (255, 215, 80, pulse),
                           (self.radius+20, self.radius+20), self.radius+12)
        pygame.draw.circle(glow, (255, 240, 150, 60),
                           (self.radius+20, self.radius+20), self.radius)
        surface.blit(glow, (self.cx - self.radius - 20,
                             int(self.cy + cam_offset + bob) - self.radius - 20))
        for b in self.beans:
            bx = int(b.x - bean_sprite.get_width()//2)
            by = int(b.y + cam_offset + bob - bean_sprite.get_height()//2)
            if -20 < by < 520:
                surface.blit(bean_sprite, (bx, by))

    def collect_beans(self, px, py, pw, ph, cam_offset, bob_offset=0):
        """Returns list of bean positions collected."""
        if not self.active:
            return []
        collected = []
        for b in self.beans[:]:
            bx = b.x - 8
            by = b.y + cam_offset + bob_offset - 8
            if checkCollisions(px, py, pw, ph, bx, by, 16, 16):
                collected.append((int(bx+8), int(by+8)))
                self.beans.remove(b)
        if not self.beans:
            self.active = False
        return collected

# ─────────────────────────── WEATHER SYSTEM ───────────────────
class WeatherSystem:
    """Depth: Rain, fog, and lightning that change every 20 seconds."""
    TYPES = ['clear', 'rain', 'fog', 'lightning']
    CHANGE_INTERVAL = 1200  # frames (~20s at 60fps)

    def __init__(self):
        self.current  = 'clear'
        self.timer    = self.CHANGE_INTERVAL
        self.drops    = []   # rain drops: [x, y, speed]
        self.fog_alpha = 0
        self.lightning_flash = 0
        self._spawn_rain()

    def _spawn_rain(self):
        self.drops = [[random.randint(0, 640), random.randint(-480, 480),
                       random.uniform(6, 12)] for _ in range(80)]

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.CHANGE_INTERVAL
            self.current = random.choice(self.TYPES)
        if self.current == 'rain':
            for d in self.drops:
                d[1] += d[2] * dt
                if d[1] > 480:
                    d[0] = random.randint(0, 640)
                    d[1] = -20
        if self.current == 'fog':
            self.fog_alpha = min(80, self.fog_alpha + 1.5 * dt)
        else:
            self.fog_alpha = max(0, self.fog_alpha - 2 * dt)
        if self.current == 'lightning':
            if random.random() < 0.003 * dt:
                self.lightning_flash = 8
            if self.lightning_flash > 0:
                self.lightning_flash -= dt

    def draw(self, surface):
        if self.current == 'rain':
            for d in self.drops:
                pygame.draw.line(surface, (160, 200, 255, 180),
                                 (int(d[0]), int(d[1])),
                                 (int(d[0])-2, int(d[1])+12), 1)
        if self.fog_alpha > 0:
            fog = pygame.Surface((640, 480), pygame.SRCALPHA)
            fog.fill((200, 220, 240, int(self.fog_alpha)))
            surface.blit(fog, (0, 0))
        if self.lightning_flash > 0:
            fl = pygame.Surface((640, 480), pygame.SRCALPHA)
            fl.fill((240, 240, 255, min(200, int(self.lightning_flash * 25))))
            surface.blit(fl, (0, 0))

    @property
    def label(self):
        return {'clear': '', 'rain': '🌧 Rain', 'fog': '🌫 Fog',
                'lightning': '⚡ Lightning'}.get(self.current, '')

# ─────────────────────────── MINI BOSS ────────────────────────
class MiniBoss:
    """Depth: Giant cup chases you at 50m — survive it for a big bean reward."""
    SIZE   = 48
    COLOR  = (180, 60, 20)
    REWARD = 30

    def __init__(self, player_x, player_y, screen_w, screen_h):
        side = random.choice([-1, 1])
        self.x     = float(-self.SIZE if side < 0 else screen_w + self.SIZE)
        self.y     = float(player_y - screen_h // 3)
        self.alive = True
        self.hp    = 3
        self.timer = 600   # 10s at 60fps
        self.shake = 0
        self.speed = 1.5

    def update(self, px, py, dt):
        if not self.alive:
            return
        self.timer -= dt
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) or 1
        self.x += (dx/dist) * self.speed * dt
        self.y += (dy/dist) * self.speed * dt
        self.speed = min(2.5, self.speed + 0.001 * dt)
        if self.shake > 0:
            self.shake -= dt

    def draw(self, surface, cam_offset, t):
        if not self.alive:
            return
        cx = int(self.x)
        cy = int(self.y + cam_offset)
        if cy < -80 or cy > 560:
            return
        shake = random.randint(-2, 2) if self.shake > 0 else 0
        # Draw giant cup shape
        body_r = pygame.Rect(cx - self.SIZE//2 + shake, cy - self.SIZE//2,
                             self.SIZE, self.SIZE)
        pygame.draw.ellipse(surface, self.COLOR, body_r)
        pygame.draw.ellipse(surface, (220, 100, 50), body_r, 3)
        # Steam puffs
        for i in range(3):
            sx = cx - 10 + i * 10
            sy = cy - self.SIZE//2 - 8 + int(math.sin(t*5 + i) * 4)
            pygame.draw.circle(surface, (255, 255, 255, 120), (sx, sy), 5)
        # HP pips
        for h in range(self.hp):
            pygame.draw.circle(surface, (255, 80, 80), (cx - 10 + h*10, cy - self.SIZE//2 - 18), 5)
            pygame.draw.circle(surface, (180, 20, 20), (cx - 10 + h*10, cy - self.SIZE//2 - 18), 5, 1)

    def hit_rect(self):
        return pygame.Rect(self.x - self.SIZE//2, self.y - self.SIZE//2,
                           self.SIZE, self.SIZE)

    def expired(self):
        return self.timer <= 0 or not self.alive

# ─────────────────────────── GHOST ────────────────────────────
class GhostRunner:
    """Social: faint ghost traces your best run — race against yourself."""
    MAX_FRAMES = 3600  # 1 min at 60fps

    def __init__(self):
        self.recording  = []   # list of (x, y) world positions
        self.best_run   = []
        self.playback_idx = 0
        self.visible    = False

    def record(self, x, y):
        if len(self.recording) < self.MAX_FRAMES:
            self.recording.append((x, y))

    def save_run(self):
        if len(self.recording) > len(self.best_run):
            self.best_run = list(self.recording)

    def start_new_run(self):
        self.recording   = []
        self.playback_idx = 0
        self.visible      = len(self.best_run) > 0

    def get_ghost_pos(self):
        if not self.best_run or self.playback_idx >= len(self.best_run):
            return None
        pos = self.best_run[self.playback_idx]
        self.playback_idx += 1
        return pos

    def draw(self, surface, cam_offset, frame_pos):
        if not self.visible or frame_pos is None:
            return
        gx = int(frame_pos[0])
        gy = int(frame_pos[1] + cam_offset)
        if -30 < gy < 510:
            ghost_surf = pygame.Surface((28, 28), pygame.SRCALPHA)
            pygame.draw.ellipse(ghost_surf, (150, 200, 255, 60), (0, 0, 28, 28))
            pygame.draw.ellipse(ghost_surf, (180, 220, 255, 100), (0, 0, 28, 28), 2)
            surface.blit(ghost_surf, (gx - 14, gy - 14))

# ─────────────────────────── ACHIEVEMENTS ─────────────────────
ACHIEVEMENTS_DEF = {
    'first_100m': {'label': '🏆 First 100m', 'desc': 'Reach 100m height'},
    'bean_millionaire': {'label': '☕ Bean Rich', 'desc': 'Collect 1000 total beans'},
    'combo_king': {'label': '🔥 Combo King', 'desc': 'Reach a 10x combo'},
    'survived_boss': {'label': '👹 Boss Slayer', 'desc': 'Survive the mini boss'},
    'speedrun_50': {'label': '⚡ Speed Demon', 'desc': 'Reach 50m in under 30s'},
}

def load_save():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return {}

def save_data(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

SAVE_FILE = "save.json"

def load_high_score():
    return load_save().get("high_score", 0)

def save_high_score(score):
    d = load_save()
    d["high_score"] = score
    save_data(d)

def load_achievements():
    return set(load_save().get("achievements", []))

def save_achievements(ach_set):
    d = load_save()
    d["achievements"] = list(ach_set)
    save_data(d)

def load_lifetime_beans():
    return load_save().get("lifetime_beans", 0)

def save_lifetime_beans(val):
    d = load_save()
    d["lifetime_beans"] = val
    save_data(d)

def load_persistent_upgrades():
    return load_save().get("persistent_upgrades", {})

def save_persistent_upgrades(upgrades):
    d = load_save()
    d["persistent_upgrades"] = upgrades
    save_data(d)

# ─────────────────────────── ZONE NAMES ───────────────────────
ZONE_NAMES = [
    (0,   "Espresso Zone"),
    (10,  "Latte Layer"),
    (25,  "Cappuccino Heights"),
    (50,  "Cloud Roast"),
    (100, "Arabica Summit"),
    (200, "Stellar Brew"),
    (500, "The Void Roast"),
]

def get_zone_name(height):
    name = ZONE_NAMES[0][1]
    for h, n in ZONE_NAMES:
        if height >= h:
            name = n
    return name

# ─────────────────────────── RESET GAME ───────────────────────
def reset_game(DISPLAY, player, persistent_upgrades=None):
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

    flapForce = 3.0
    speed_mult = 1.0
    pu = persistent_upgrades or {}
    for _ in range(pu.get('flap', 0)):
        flapForce *= 1.3
    for _ in range(pu.get('speed', 0)):
        speed_mult *= 1.3
    if speed_mult > 1.0:
        player.velocity.x *= speed_mult

    return dict(
        health=100, beanCount=0, height=0,
        flapForce=flapForce, beanMultiplier=5,
        combo=0, combo_timer=0,
        particles=[], trail=[], toasts=[],
        shake=0.0, difficulty=1.0,
        rotOffset=-5,
        wind_gusts=[], wind_timer=0,
        golden_beans=[], golden_timer=0,
        caffeine=CaffeineRush(),
        beans=beans, buttons=buttons,
        startingHeight=player.position.y,
        # New systems
        floating_texts=[],
        weather=WeatherSystem(),
        bean_magnets=[], magnet_timer=0,
        bean_clouds=[], cloud_timer=0,
        mini_boss=None, boss_spawned=False,
        ghost_pos=None,
        speedrun_start=time.time(),
        run_bean_count=0,
        max_combo=0,
        boss_survived=False,
        die_timer=0, die_fade=0, die_spin=0.0,
    )

# ─────────────────────────── MAIN ─────────────────────────────
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
    achievements = load_achievements()
    lifetime_beans = load_lifetime_beans()
    persistent_upgrades = load_persistent_upgrades()
    state      = State.SPLASH
    last_time  = time.time()
    splashTimer = 0
    bg = [Background(), Background(), Background()]

    # Persistent upgrade shop (title screen upgrade pool)
    PU_COSTS = {'flap': 20, 'speed': 20}

    g  = reset_game(DISPLAY, player, persistent_upgrades)
    MILESTONE_HEIGHTS  = {10, 25, 50, 100, 200, 500}
    reached_milestones = set()
    pygame.mixer.Sound.play(flapfx)

    # Visual polish: parallax clouds (3 layers, 5 clouds each)
    clouds = [ParallaxCloud(layer, 640, 480)
              for layer in range(3) for _ in range(5)]

    # Visual polish: background bubbles
    bg_bubbles = [BgBubble(640, 480) for _ in range(18)]

    # Ghost runner
    ghost = GhostRunner()

    # Persistent upgrade menu state
    show_pu_menu  = False
    pu_pool_beans = 0   # beans available to spend on persistent upgrades
    new_achievements = []  # queued achievement unlock toasts

    prev_cam_y = 0  # for parallax cloud movement

    # ── MENU THEME COLOURS ──────────────────────────────────────
    M_BG_TOP    = (10,  8,  22)   # deep midnight
    M_BG_BOT    = (28, 14,  42)   # dark aubergine
    M_ACCENT    = (138, 80, 220)  # electric violet
    M_ACCENT2   = (80, 160, 230)  # cool blue
    M_GOLD      = (255, 200,  80)
    M_TEXT      = (220, 210, 240)
    M_DIM       = (120, 105, 150)
    M_PANEL     = (22,  15,  40, 210)
    M_BTN_IDLE  = (40,  25,  72)
    M_BTN_HOV   = (65,  38, 115)
    M_BTN_BORD  = (100, 60, 180)

    # ── MENU ANIMATION PARTICLES ────────────────────────────────
    # Floating beans for the menu bg
    class MenuBean:
        def __init__(self):
            self.x     = random.uniform(0, 640)
            self.y     = random.uniform(0, 480)
            self.vy    = random.uniform(-0.3, -0.8)
            self.vx    = random.uniform(-0.2, 0.2)
            self.size  = random.randint(3, 7)
            self.alpha = random.randint(40, 130)
            self.wobble= random.uniform(0, math.tau)
        def update(self, dt):
            self.y  += self.vy * dt
            self.x  += self.vx * dt + math.sin(time.time()*1.5 + self.wobble)*0.3
            if self.y < -12:
                self.y = 492
                self.x = random.uniform(0, 640)
        def draw(self, surface, t):
            pulse = int(self.alpha * (0.75 + 0.25*math.sin(t*2+self.wobble)))
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (160, 100, 50, pulse), (0,0,self.size*2,self.size*2))
            pygame.draw.ellipse(s, (200,140,80,min(255,pulse+40)), (0,0,self.size*2,self.size*2), 1)
            surface.blit(s, (int(self.x)-self.size, int(self.y)-self.size))

    # Steam particles
    class SteamPuff:
        def __init__(self, ox, oy):
            self.ox, self.oy = ox, oy
            self._reset()
        def _reset(self):
            self.x     = self.ox + random.uniform(-8, 8)
            self.y     = float(self.oy)
            self.vy    = random.uniform(-0.6, -1.2)
            self.vx    = random.uniform(-0.15, 0.15)
            self.life  = random.uniform(0.4, 1.0)
            self.max_life = self.life
            self.r     = random.randint(4, 10)
        def update(self, dt):
            self.y   += self.vy * dt
            self.x   += self.vx * dt
            self.r   += 0.04 * dt
            self.life -= 0.012 * dt
            if self.life <= 0:
                self._reset()
        def draw(self, surface):
            if self.life > 0:
                a = int(70 * (self.life / self.max_life))
                s = pygame.Surface((int(self.r)*2+2, int(self.r)*2+2), pygame.SRCALPHA)
                pygame.draw.circle(s, (200, 190, 220, a), (int(self.r)+1, int(self.r)+1), int(self.r))
                surface.blit(s, (int(self.x)-int(self.r), int(self.y)-int(self.r)))

    # Star field
    stars = [(random.randint(0,639), random.randint(0,479),
              random.uniform(0.5,2.5), random.uniform(0,math.tau)) for _ in range(80)]

    menu_beans  = [MenuBean() for _ in range(28)]
    steam_puffs = [SteamPuff(320 + random.randint(-30,30), 295) for _ in range(14)]

    # Menu sub-screen state
    # 0=home, 1=achievements, 2=upgrades
    menu_tab = 0
    menu_tab_anim = 0.0  # for slide-in effect

    # Button hover tracking
    hovered_btn = None

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
                if event.key == K_SPACE or event.key == K_UP:
                    jump = True
                if event.key == K_ESCAPE:
                    if state == State.PLAYING:  state = State.PAUSED
                    elif state == State.PAUSED: state = State.PLAYING
                if event.key == K_r and state == State.PLAYING:
                    g['caffeine'].activate()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
                if state == State.PLAYING and mouseY < DISPLAY.get_height() - 90:
                    jump = True

        # ── SPLASH ──────────────────────────────────────────────
        if state == State.SPLASH:
            splashTimer += dt
            DISPLAY.fill((10, 8, 22))
            fade_a = int(255 * min(1.0, splashTimer / 30))
            msg = font_small.render("Dev By Pygame", True, (138, 80, 220))
            msg.set_alpha(fade_a)
            DISPLAY.blit(msg, (320 - msg.get_width()//2, 240 - msg.get_height()//2))
            pygame.display.update(); pygame.time.delay(10)
            if splashTimer >= 100:
                state = State.TITLE
                menu_tab = 0; menu_tab_anim = 0.0
                pygame.mixer.Sound.play(flapfx)
            continue

        # ── TITLE ───────────────────────────────────────────────
        if state == State.TITLE:
            # ── helpers ──────────────────────────────────────────
            def draw_grad_bg():
                """Vertical gradient: deep midnight → dark aubergine."""
                for row in range(0, 480, 2):
                    f = row / 480
                    r = int(M_BG_TOP[0]*(1-f) + M_BG_BOT[0]*f)
                    g2= int(M_BG_TOP[1]*(1-f) + M_BG_BOT[1]*f)
                    b = int(M_BG_TOP[2]*(1-f) + M_BG_BOT[2]*f)
                    pygame.draw.rect(DISPLAY, (r,g2,b), (0, row, 640, 2))

            def draw_rounded_rect(surf, color, rect, radius=10, border=0, border_color=None):
                pygame.draw.rect(surf, color, rect, border_radius=radius)
                if border and border_color:
                    pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

            def draw_glowing_btn(rect, label_surf, hov, accent=M_ACCENT):
                base_col  = M_BTN_HOV if hov else M_BTN_IDLE
                bord_col  = accent if hov else M_BTN_BORD
                # glow under
                if hov:
                    glow = pygame.Surface((rect.w+16, rect.h+16), pygame.SRCALPHA)
                    pygame.draw.rect(glow, (*accent, 55), (0,0,rect.w+16,rect.h+16), border_radius=14)
                    DISPLAY.blit(glow, (rect.x-8, rect.y-8))
                draw_rounded_rect(DISPLAY, base_col, rect, radius=10)
                draw_rounded_rect(DISPLAY, (0,0,0,0), rect, radius=10, border=2, border_color=bord_col)
                lx = rect.centerx - label_surf.get_width()//2
                ly = rect.centery - label_surf.get_height()//2
                DISPLAY.blit(label_surf, (lx, ly))

            # ── update animations ─────────────────────────────────
            for mb in menu_beans:  mb.update(dt)
            for sp in steam_puffs: sp.update(dt)
            menu_tab_anim = min(1.0, menu_tab_anim + 0.08 * dt)

            # ── draw gradient background ──────────────────────────
            draw_grad_bg()

            # star field
            star_surf = pygame.Surface((640,480), pygame.SRCALPHA)
            for (sx, sy, sr, sphase) in stars:
                twinkle = int(140 + 80 * math.sin(t*1.8 + sphase))
                pygame.draw.circle(star_surf, (220, 210, 255, twinkle), (sx, sy), int(sr*0.7)+1)
            DISPLAY.blit(star_surf, (0,0))

            # floating beans
            bean_surf = pygame.Surface((640,480), pygame.SRCALPHA)
            for mb in menu_beans:  mb.draw(bean_surf, t)
            DISPLAY.blit(bean_surf, (0,0))

            # subtle horizontal scanline atmosphere
            scan_surf = pygame.Surface((640,480), pygame.SRCALPHA)
            for row in range(0, 480, 4):
                pygame.draw.line(scan_surf, (0,0,0,18), (0,row),(640,row))
            DISPLAY.blit(scan_surf, (0,0))

            # ── glowing orb behind logo ───────────────────────────
            orb_y  = 112 + int(math.sin(t*0.8)*5)
            orb_r  = 68 + int(math.sin(t*1.2)*4)
            orb_s  = pygame.Surface((orb_r*4, orb_r*4), pygame.SRCALPHA)
            for i in range(4):
                alpha = [35, 25, 15, 8][i]
                rad   = [orb_r, orb_r+14, orb_r+28, orb_r+42][i]
                pygame.draw.circle(orb_s, (*M_ACCENT, alpha),
                                   (orb_r*2, orb_r*2), rad)
            DISPLAY.blit(orb_s, (320 - orb_r*2, orb_y - orb_r*2))

            # ── logo ─────────────────────────────────────────────
            logo_y = orb_y - logo.get_height()//2 + int(math.sin(t*1.4)*4)
            DISPLAY.blit(logo, (320 - logo.get_width()//2, logo_y))

            # steam puffs rising from logo bottom
            steam_s = pygame.Surface((640,480), pygame.SRCALPHA)
            for sp in steam_puffs: sp.draw(steam_s)
            DISPLAY.blit(steam_s, (0,0))

            # ── tab bar: HOME / ACHIEVEMENTS / UPGRADES ───────────
            tab_labels  = ["PLAY", "TROPHIES", "UPGRADES"]
            tab_w, tab_h = 160, 32
            tab_total_w  = tab_w * 3 + 8
            tab_x0       = 320 - tab_total_w//2
            tab_y        = 180
            tab_bar_bg   = pygame.Surface((tab_total_w+4, tab_h+4), pygame.SRCALPHA)
            tab_bar_bg.fill((15,10,30,180))
            pygame.draw.rect(tab_bar_bg,(60,40,100,200),(0,0,tab_total_w+4,tab_h+4),border_radius=12)
            DISPLAY.blit(tab_bar_bg, (tab_x0-2, tab_y-2))

            for ti, tlbl in enumerate(tab_labels):
                tx = tab_x0 + ti*(tab_w+4)
                tr = pygame.Rect(tx, tab_y, tab_w, tab_h)
                is_active = (menu_tab == ti)
                hov_tab   = tr.collidepoint(mouseX, mouseY)
                if is_active:
                    pygame.draw.rect(DISPLAY, M_ACCENT, tr, border_radius=9)
                    pygame.draw.rect(DISPLAY, (180,120,255), tr, 2, border_radius=9)
                elif hov_tab:
                    pygame.draw.rect(DISPLAY, (55,35,90), tr, border_radius=9)
                t_surf = font_14.render(tlbl, True, (255,255,255) if is_active else M_DIM)
                DISPLAY.blit(t_surf, (tr.centerx - t_surf.get_width()//2,
                                      tr.centery - t_surf.get_height()//2))
                if clicked and hov_tab and not is_active:
                    menu_tab = ti
                    menu_tab_anim = 0.0
                    pygame.mixer.Sound.play(flapfx)

            # slide-in panel offset
            slide_off = int((1.0 - menu_tab_anim) * 40)

            # ── PANEL BACKGROUND ──────────────────────────────────
            panel_rect = pygame.Rect(60, 222 + slide_off, 520, 218)
            panel_s = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
            panel_s.fill((18, 10, 35, 200))
            pygame.draw.rect(panel_s, (70, 45, 120, 160),
                             (0,0,panel_rect.w,panel_rect.h), 2, border_radius=14)
            DISPLAY.blit(panel_s, (panel_rect.x, panel_rect.y))

            # ── TAB 0: PLAY ───────────────────────────────────────
            if menu_tab == 0:
                # Best score badge
                score_y = 234 + slide_off
                if high_score > 0:
                    badge_s = pygame.Surface((200, 36), pygame.SRCALPHA)
                    badge_s.fill((40,25,72,200))
                    pygame.draw.rect(badge_s,(100,60,180,220),(0,0,200,36),2,border_radius=10)
                    DISPLAY.blit(badge_s, (220, score_y))
                    hs_icon = font_14.render("BEST", True, M_DIM)
                    hs_val  = font_small.render(f"{high_score}m", True, M_GOLD)
                    DISPLAY.blit(hs_icon, (232, score_y + 4))
                    DISPLAY.blit(hs_val,  (290, score_y - 2))

                # PLAY button — big glowing
                play_rect = pygame.Rect(185, 280 + slide_off, 270, 52)
                hov_play  = play_rect.collidepoint(mouseX, mouseY)
                pulse_w   = int(math.sin(t*2.5)*4)
                if hov_play:
                    glow2 = pygame.Surface((play_rect.w+30, play_rect.h+30), pygame.SRCALPHA)
                    pygame.draw.rect(glow2, (*M_ACCENT, 70),
                                     (0,0,play_rect.w+30,play_rect.h+30), border_radius=18)
                    DISPLAY.blit(glow2, (play_rect.x-15, play_rect.y-15))
                grad_play = pygame.Surface((play_rect.w, play_rect.h), pygame.SRCALPHA)
                for px2 in range(play_rect.w):
                    f2 = px2 / play_rect.w
                    cr = int(M_ACCENT[0]*(1-f2) + M_ACCENT2[0]*f2)
                    cg2= int(M_ACCENT[1]*(1-f2) + M_ACCENT2[1]*f2)
                    cb = int(M_ACCENT[2]*(1-f2) + M_ACCENT2[2]*f2)
                    pygame.draw.rect(grad_play, (cr,cg2,cb,230), (px2,0,1,play_rect.h))
                mask = pygame.Surface((play_rect.w, play_rect.h), pygame.SRCALPHA)
                pygame.draw.rect(mask, (255,255,255,255), (0,0,play_rect.w,play_rect.h), border_radius=14)
                grad_play.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MIN)
                DISPLAY.blit(grad_play, (play_rect.x, play_rect.y))
                pygame.draw.rect(DISPLAY, (200,160,255) if hov_play else (150,100,220),
                                 play_rect, 2, border_radius=14)
                play_lbl = font_small.render("PLAY", True, (255,255,255))
                DISPLAY.blit(play_lbl, (play_rect.centerx - play_lbl.get_width()//2,
                                        play_rect.centery - play_lbl.get_height()//2))

                # Hint
                hint_s = font_14.render("SPACE / CLICK to flap  ·  R = caffeine rush  ·  ESC = pause",
                                        True, M_DIM)
                DISPLAY.blit(hint_s, (320 - hint_s.get_width()//2, 344 + slide_off))

                if clicked and hov_play:
                    pygame.mixer.Sound.play(upgradefx)
                    ghost.start_new_run()
                    state = State.PLAYING

            # ── TAB 1: ACHIEVEMENTS ───────────────────────────────
            elif menu_tab == 1:
                ach_title = font_20.render(
                    f"TROPHIES  {len(achievements)}/{len(ACHIEVEMENTS_DEF)}", True, M_GOLD)
                DISPLAY.blit(ach_title, (320 - ach_title.get_width()//2, 232 + slide_off))

                # Progress bar
                prog_w = int(400 * len(achievements) / max(1, len(ACHIEVEMENTS_DEF)))
                pygame.draw.rect(DISPLAY, (40,25,72), (120, 256+slide_off, 400, 8), border_radius=4)
                if prog_w > 0:
                    pygame.draw.rect(DISPLAY, M_ACCENT, (120, 256+slide_off, prog_w, 8), border_radius=4)
                pygame.draw.rect(DISPLAY, M_BTN_BORD, (120, 256+slide_off, 400, 8), 1, border_radius=4)

                for i, (key, info) in enumerate(ACHIEVEMENTS_DEF.items()):
                    unlocked = key in achievements
                    row_y    = 272 + i*30 + slide_off
                    # row bg
                    row_bg   = pygame.Surface((480, 26), pygame.SRCALPHA)
                    row_bg.fill((80,50,130,60) if unlocked else (25,15,45,60))
                    pygame.draw.rect(row_bg, (100,65,170,80) if unlocked else (40,25,72,60),
                                     (0,0,480,26), 1, border_radius=6)
                    DISPLAY.blit(row_bg, (80, row_y))
                    icon_col = M_GOLD if unlocked else (70,55,95)
                    icon_s   = font_14.render("★" if unlocked else "○", True, icon_col)
                    DISPLAY.blit(icon_s, (90, row_y+6))
                    lbl_col  = M_TEXT if unlocked else M_DIM
                    lbl_s    = font_14.render(info['label'], True, lbl_col)
                    DISPLAY.blit(lbl_s, (110, row_y+6))
                    if not unlocked:
                        desc_s = font_14.render(info['desc'], True, (80,65,110))
                        DISPLAY.blit(desc_s, (300, row_y+6))

            # ── TAB 2: UPGRADES ───────────────────────────────────
            elif menu_tab == 2:
                ug_title = font_20.render("PERMANENT UPGRADES", True, M_GOLD)
                DISPLAY.blit(ug_title, (320 - ug_title.get_width()//2, 232 + slide_off))

                # Bean wallet
                wallet_s = font_14.render(f"☕  {pu_pool_beans}  beans available", True, (180,220,160))
                DISPLAY.blit(wallet_s, (320 - wallet_s.get_width()//2, 256 + slide_off))

                pu_items = [
                    ('flap',  '⬆  FLAP POWER',  PU_COSTS['flap'],  persistent_upgrades.get('flap', 0)),
                    ('speed', '➤  RUN SPEED',   PU_COSTS['speed'], persistent_upgrades.get('speed', 0)),
                ]
                for i, (key, label, cost, lvl) in enumerate(pu_items):
                    row_y = 278 + i*62 + slide_off
                    # card bg
                    card = pygame.Surface((460, 52), pygame.SRCALPHA)
                    card.fill((28,16,52,210))
                    pygame.draw.rect(card, M_BTN_BORD, (0,0,460,52), 1, border_radius=10)
                    DISPLAY.blit(card, (90, row_y))

                    lbl_s  = font_20.render(label, True, M_TEXT)
                    DISPLAY.blit(lbl_s, (104, row_y+8))

                    # level pips
                    for pip in range(max(1, lvl+1)):
                        pc = M_ACCENT if pip < lvl else (45,30,80)
                        pygame.draw.circle(DISPLAY, pc, (104 + pip*16, row_y+40), 5)
                        pygame.draw.circle(DISPLAY, M_BTN_BORD, (104 + pip*16, row_y+40), 5, 1)

                    can_afford = pu_pool_beans >= cost
                    buy_r = pygame.Rect(410, row_y+10, 108, 32)
                    hov_buy = buy_r.collidepoint(mouseX, mouseY)
                    buy_col = (60,150,70) if (can_afford and hov_buy) else \
                              (40,110,50) if can_afford else (60,45,75)
                    draw_rounded_rect(DISPLAY, buy_col, buy_r, radius=8)
                    draw_rounded_rect(DISPLAY, (0,0,0,0), buy_r, radius=8, border=1,
                                      border_color=(80,200,90) if can_afford else M_BTN_BORD)
                    cost_lbl = font_14.render(f"BUY  {cost}☕", True,
                                              (220,255,220) if can_afford else M_DIM)
                    DISPLAY.blit(cost_lbl, (buy_r.centerx - cost_lbl.get_width()//2,
                                            buy_r.centery - cost_lbl.get_height()//2))
                    if clicked and hov_buy and can_afford:
                        pu_pool_beans -= cost
                        persistent_upgrades[key] = lvl + 1
                        save_persistent_upgrades(persistent_upgrades)
                        pygame.mixer.Sound.play(upgradefx)

            # ── bottom accent line ────────────────────────────────
            for xi in range(0, 640, 2):
                f3 = xi / 640
                r3 = int(M_ACCENT[0]*(1-f3) + M_ACCENT2[0]*f3)
                g3 = int(M_ACCENT[1]*(1-f3) + M_ACCENT2[1]*f3)
                b3 = int(M_ACCENT[2]*(1-f3) + M_ACCENT2[2]*f3)
                pygame.draw.rect(DISPLAY, (r3,g3,b3), (xi,476,2,4))

            # ── version watermark ─────────────────────────────────
            ver_s = font_14.render("FLAPPUCCINO  v2.0", True, (50,38,75))
            DISPLAY.blit(ver_s, (320 - ver_s.get_width()//2, 460))

            pygame.display.update(); pygame.time.delay(10); continue

        # ── PAUSED ──────────────────────────────────────────────
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
            zn = font_20.render(get_zone_name(g['height']),True,(255,215,100))
            DISPLAY.blit(zn,(320-zn.get_width()//2,295))
            if clicked: state = State.PLAYING
            pygame.display.update(); pygame.time.delay(10); continue

        # ── Shared render setup ──────────────────────────────────
        # Day/Night cycle: sky shifts from cool cyan/blue (day) → deep midnight (night)
        day_t    = min(1.0, g['height'] / 200.0)  # 0=day, 1=night
        # Lock hue to cyan/blue band (0.50–0.65) — prevents pink/red tint on bg sprite
        raw_hue  = (player.position.y / 50 % 100) / 100
        hue_base = 0.50 + (raw_hue % 0.15)   # cycles only within cyan→blue, never red/pink
        if day_t < 0.35:
            # Bright day: vivid sky blue → cyan
            f = day_t / 0.35
            sky_r = int(40  + f * 10)
            sky_g = int(160 + f * 30)
            sky_b = int(230 + f * 20)
        elif day_t < 0.65:
            # Dusk: cyan fading into deep blue-violet
            f = (day_t - 0.35) / 0.30
            sky_r = int(50  * (1 - f) + 20  * f)
            sky_g = int(190 * (1 - f) + 60  * f)
            sky_b = int(250 * (1 - f) + 180 * f)
        else:
            # Night: deep indigo/midnight
            f = (day_t - 0.65) / 0.35
            sky_r = int(max(0, 20  - f * 15))
            sky_g = int(max(0, 60  - f * 55))
            sky_b = int(min(255, 180 + f * 50))
        sky_color = (sky_r, sky_g, sky_b)

        shake_x  = random.randint(-int(g['shake']),int(g['shake'])) if g['shake']>0 else 0
        shake_y  = random.randint(-int(g['shake']),int(g['shake'])) if g['shake']>0 else 0
        camOffset= (-player.position.y+DISPLAY.get_height()//2
                    -player.currentSprite.get_size()[1]//2+shake_y)
        rush_alpha = int(g['caffeine'].progress*60)

        # Parallax cloud update (camera movement delta)
        cam_y_now = camOffset
        cam_dy = cam_y_now - prev_cam_y
        prev_cam_y = cam_y_now
        for cloud in clouds:
            cloud.update(cam_dy, dt)
            if cloud.y > 500:
                cloud.y = -60

        # Background bubbles
        for bbl in bg_bubbles:
            bbl.update(dt)
            if bbl.y < -40:
                bbl.reset(640, 480)

        DISPLAY.fill(sky_color)

        # Draw stars at night
        if day_t > 0.5:
            star_alpha = int((day_t - 0.5) * 2 * 200)
            for sx, sy in [(50,30),(120,80),(300,20),(500,60),(580,30),(420,90),(200,15)]:
                twinkle = int(star_alpha * (0.7 + 0.3 * math.sin(t*3 + sx)))
                pygame.draw.circle(DISPLAY, (255,255,220), (sx, sy), 2)

        for o in bg:
            o.setSprite(hue_base)
            DISPLAY.blit(o.sprite,(shake_x,o.position))

        # Background bubbles
        bbl_surf = pygame.Surface((640,480), pygame.SRCALPHA)
        for bbl in bg_bubbles:
            bbl.draw(bbl_surf)
        DISPLAY.blit(bbl_surf, (0,0))

        # Parallax clouds (draw far→near)
        cloud_surf = pygame.Surface((640,480), pygame.SRCALPHA)
        for cloud in sorted(clouds, key=lambda c: c.layer):
            cloud.draw(cloud_surf)
        DISPLAY.blit(cloud_surf, (0,0))

        if rush_alpha > 0:
            vig = pygame.Surface((640,480),pygame.SRCALPHA)
            vig.fill((255,210,0,rush_alpha))
            DISPLAY.blit(vig,(0,0))

        # Low health flash (Game Feel)
        if g['health'] < 30:
            pulse = abs(math.sin(t * 6))
            lh_surf = pygame.Surface((640,480), pygame.SRCALPHA)
            pygame.draw.rect(lh_surf, (255, 0, 0, int(pulse * 80)), (0,0,640,480))
            pygame.draw.rect(lh_surf, (255, 0, 0, int(pulse * 120)), (0,0,640,12))
            pygame.draw.rect(lh_surf, (255, 0, 0, int(pulse * 120)), (0,468,640,12))
            pygame.draw.rect(lh_surf, (255, 0, 0, int(pulse * 120)), (0,0,12,480))
            pygame.draw.rect(lh_surf, (255, 0, 0, int(pulse * 120)), (628,0,12,480))
            DISPLAY.blit(lh_surf, (0,0))

        rgb = colorsys.hsv_to_rgb(hue_base,0.5,0.5)
        hsurf = font.render(str(g['height']),True,(int(rgb[0]*255),int(rgb[1]*255),int(rgb[2]*255)))
        DISPLAY.blit(hsurf,(320-hsurf.get_width()//2,
                    camOffset+round((player.position.y-g['startingHeight'])/DISPLAY.get_height())
                    *DISPLAY.get_height()+player.currentSprite.get_height()-40))

        # Zone name display (Visual Polish)
        zone_name = get_zone_name(g['height'])
        zn_surf = font_14.render(zone_name, True, (int(rgb[0]*200), int(rgb[1]*200), int(rgb[2]*200)))
        DISPLAY.blit(zn_surf, (320 - zn_surf.get_width()//2,
                     camOffset + round((player.position.y - g['startingHeight'])/DISPLAY.get_height())
                     * DISPLAY.get_height() + player.currentSprite.get_height() + 50))

        for wg in g['wind_gusts']: wg.draw(DISPLAY,camOffset)
        for gb in g['golden_beans']: gb.draw(DISPLAY,camOffset,t)

        # Bean cloud zones
        for bcz in g['bean_clouds']:
            bcz.draw(DISPLAY, camOffset, t, g['beans'][0].sprite if g['beans'] else Bean().sprite)

        for bean in g['beans']:
            DISPLAY.blit(bean.sprite,(bean.position.x+shake_x,bean.position.y+camOffset))

        # Bean magnets pickups
        for bm in g['bean_magnets']:
            if not bm.active:
                bm.draw_pickup(DISPLAY, camOffset, t)

        # Mini boss
        if g['mini_boss'] and g['mini_boss'].alive:
            g['mini_boss'].draw(DISPLAY, camOffset, t)

        trail_surf = pygame.Surface((640,480),pygame.SRCALPHA)
        for td in g['trail']: td.draw(trail_surf)
        DISPLAY.blit(trail_surf,(0,0))

        # Ghost runner draw
        ghost_frame_pos = ghost.get_ghost_pos() if state == State.PLAYING else None
        ghost.draw(DISPLAY, camOffset, ghost_frame_pos)

        # Squash & Stretch (Game Feel)
        vy_clamped = clamp(player.velocity.y, -10, 10)
        stretch_y = 1.0 + vy_clamped * 0.03
        stretch_x = 1.0 - vy_clamped * 0.02
        base_sprite = pygame.transform.rotate(player.currentSprite,
                          clamp(player.velocity.y,-10,5)*g['rotOffset'])
        sw = int(base_sprite.get_width() * stretch_x)
        sh = int(base_sprite.get_height() * stretch_y)
        sw = max(4, sw); sh = max(4, sh)
        squashed = pygame.transform.scale(base_sprite, (sw, sh))
        DISPLAY.blit(squashed,(player.position.x+shake_x,player.position.y+camOffset))

        psurf = pygame.Surface((640,480),pygame.SRCALPHA)
        for p in g['particles']: p.draw(psurf)
        DISPLAY.blit(psurf,(0,0))

        # Floating score texts (Visual Polish)
        ft_surf = pygame.Surface((640,480), pygame.SRCALPHA)
        for ft in g['floating_texts']:
            ft.update(dt)
            ft.draw(ft_surf, font_20)
        DISPLAY.blit(ft_surf, (0,0))

        # Weather effects
        g['weather'].update(dt)
        g['weather'].draw(DISPLAY)
        if g['weather'].current != 'clear':
            wlbl = font_14.render(g['weather'].label, True, (200,220,255))
            DISPLAY.blit(wlbl, (320 - wlbl.get_width()//2, 2))

        # ═══════════════════════════════════════════════════════
        # REDESIGNED HUD
        # ═══════════════════════════════════════════════════════

        # ── Helper: frosted glass panel ──────────────────────────
        def hud_panel(x, y, w, h, alpha=170, radius=10,
                      fill=(15, 10, 30), border=(90, 60, 160)):
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(s, (*fill, alpha), (0, 0, w, h), border_radius=radius)
            pygame.draw.rect(s, (*border, 200),  (0, 0, w, h), 2, border_radius=radius)
            DISPLAY.blit(s, (x, y))

        # ── TOP-LEFT: Health bar ──────────────────────────────────
        hbar_x, hbar_y, hbar_w, hbar_h = 8, 8, 160, 18
        hud_panel(hbar_x - 4, hbar_y - 4, hbar_w + 8, hbar_h + 8,
                  alpha=150, radius=8, fill=(12, 6, 24), border=(80, 50, 140))
        hp_ratio = g['health'] / 100
        # Health colour: green → yellow → red
        if hp_ratio > 0.5:
            hcr = int(255 * (1 - hp_ratio) * 2)
            hcg = 220
        else:
            hcr = 220
            hcg = int(220 * hp_ratio * 2)
        hp_fill_w = max(0, int(hbar_w * hp_ratio))
        # Glow behind bar
        if hp_fill_w > 4:
            glow_s = pygame.Surface((hp_fill_w, hbar_h), pygame.SRCALPHA)
            glow_s.fill((hcr, hcg, 60, 60))
            DISPLAY.blit(glow_s, (hbar_x, hbar_y))
        pygame.draw.rect(DISPLAY, (30, 18, 50),
                         (hbar_x, hbar_y, hbar_w, hbar_h), border_radius=6)
        if hp_fill_w > 0:
            pygame.draw.rect(DISPLAY, (hcr, hcg, 60),
                             (hbar_x, hbar_y, hp_fill_w, hbar_h), border_radius=6)
            # Shine strip
            pygame.draw.rect(DISPLAY, (255, 255, 255),
                             (hbar_x + 2, hbar_y + 2, max(0, hp_fill_w - 4), 3),
                             border_radius=3)
        pygame.draw.rect(DISPLAY, (100, 70, 180),
                         (hbar_x, hbar_y, hbar_w, hbar_h), 2, border_radius=6)
        hp_lbl = font_14.render(f"HP  {int(g['health'])}%", True, (230, 215, 255))
        DISPLAY.blit(hp_lbl, (hbar_x + 4, hbar_y + 2))

        # ── TOP-LEFT: Caffeine pips (below health bar) ────────────
        pip_y = hbar_y + hbar_h + 8
        caf_panel_w = 8 + max(1, g['caffeine'].charges) * 22
        hud_panel(hbar_x - 4, pip_y - 4, caf_panel_w + 8, 22,
                  alpha=140, radius=7, fill=(12, 6, 24), border=(80, 50, 140))
        for ci in range(g['caffeine'].charges):
            pip_col   = (255, 180, 0) if not g['caffeine'].active else (255, 100, 20)
            pip_glow  = (255, 220, 80, 80) if not g['caffeine'].active else (255, 140, 40, 80)
            gp = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(gp, pip_glow, (10, 10), 10)
            DISPLAY.blit(gp, (hbar_x + ci*22 - 2, pip_y - 2))
            pygame.draw.circle(DISPLAY, pip_col,    (hbar_x + 8 + ci*22, pip_y + 7), 7)
            pygame.draw.circle(DISPLAY, (200, 120, 0), (hbar_x + 8 + ci*22, pip_y + 7), 7, 2)
        if g['caffeine'].charges == 0:
            no_caf = font_14.render("☕ 0", True, (80, 60, 110))
            DISPLAY.blit(no_caf, (hbar_x + 2, pip_y + 1))

        # Caffeine rush progress bar
        if g['caffeine'].active:
            bar_w2 = int(152 * g['caffeine'].progress)
            rush_bar_y = pip_y + 22
            pygame.draw.rect(DISPLAY, (40, 20, 10),
                             (hbar_x, rush_bar_y, 152, 7), border_radius=4)
            pygame.draw.rect(DISPLAY, (255, 160, 0),
                             (hbar_x, rush_bar_y, bar_w2, 7), border_radius=4)
            pygame.draw.rect(DISPLAY, (220, 100, 0),
                             (hbar_x, rush_bar_y, 152, 7), 1, border_radius=4)
            rl = font_14.render("RUSH", True, (255, 210, 80))
            DISPLAY.blit(rl, (hbar_x + 156, rush_bar_y - 1))
        elif g['caffeine'].charges > 0:
            hint2 = font_14.render("[R] Rush", True, (180, 120, 40))
            DISPLAY.blit(hint2, (hbar_x, pip_y + 22))

        # ── TOP-LEFT: Bean counter ────────────────────────────────
        bc_y = pip_y + 50
        hud_panel(hbar_x - 4, bc_y - 4, 168, 28,
                  alpha=160, radius=8, fill=(14, 8, 28), border=(100, 65, 170))
        bean_icon = font_14.render("☕", True, (210, 150, 60))
        DISPLAY.blit(bean_icon, (hbar_x + 2, bc_y + 2))
        bean_val = font_20.render(str(g['beanCount']).zfill(7), True, (255, 220, 130))
        DISPLAY.blit(bean_val, (hbar_x + 22, bc_y + 3))

        # ── TOP-RIGHT: Height + speedrun timer ───────────────────
        elapsed = time.time() - g['speedrun_start']
        mins    = int(elapsed // 60)
        secs    = int(elapsed % 60)
        centis  = int((elapsed % 1) * 100)
        timer_str  = f"{mins:02d}:{secs:02d}.{centis:02d}"
        height_str = f"{g['height']}m"
        tr_panel_w = 120
        hud_panel(640 - tr_panel_w - 8, 6, tr_panel_w, 48,
                  alpha=150, radius=8, fill=(12, 6, 24), border=(80, 50, 140))
        h_surf = font_20.render(height_str, True, (160, 220, 255))
        DISPLAY.blit(h_surf, (640 - tr_panel_w//2 - h_surf.get_width()//2 - 4, 10))
        t_surf2 = font_14.render(timer_str, True, (120, 180, 140))
        DISPLAY.blit(t_surf2, (640 - tr_panel_w//2 - t_surf2.get_width()//2 - 4, 34))

        # NEW BEST badge (top right, above panel)
        if g['height'] > high_score and state == State.PLAYING:
            pb_s = pygame.Surface((90, 18), pygame.SRCALPHA)
            pb_s.fill((255, 200, 0, 50))
            pygame.draw.rect(pb_s, (200, 150, 0, 180), (0, 0, 90, 18), 1, border_radius=5)
            DISPLAY.blit(pb_s, (640 - 98, 56))
            pb = font_14.render("★ NEW BEST", True, (255, 215, 0))
            DISPLAY.blit(pb, (640 - 98 + 45 - pb.get_width()//2, 58))

        # ── MAGNET bar (top-left below beans) ─────────────────────
        for bm in g['bean_magnets']:
            if bm.active and bm.progress > 0:
                mag_y = bc_y + 34
                hud_panel(hbar_x - 4, mag_y - 4, 168, 20,
                          alpha=140, radius=6, fill=(30, 10, 50), border=(140, 60, 200))
                mbar_w2 = int(152 * bm.progress)
                pygame.draw.rect(DISPLAY, (60, 20, 90),
                                 (hbar_x, mag_y + 2, 152, 10), border_radius=4)
                pygame.draw.rect(DISPLAY, (200, 80, 255),
                                 (hbar_x, mag_y + 2, mbar_w2, 10), border_radius=4)
                mlbl = font_14.render("✦ MAGNET", True, (220, 140, 255))
                DISPLAY.blit(mlbl, (hbar_x + 4, mag_y + 1))

        # ── BOTTOM HUD: upgrade shop buttons ─────────────────────
        DISPLAY.blit(shop_bg, (0, 0))

        # Redesigned health bar in shop strip (replaces original brown bar)
        strip_hp_w = int(150 * (g['health'] / 100))
        # Gradient fill matching top bar colours
        for px3 in range(strip_hp_w):
            f3 = px3 / max(1, 150)
            cr3 = int((1 - f3) * hcr + f3 * max(0, hcr - 40))
            cg3 = int((1 - f3) * hcg + f3 * max(0, hcg - 30))
            pygame.draw.rect(DISPLAY, (cr3, cg3, 40), (21 + px3, 437, 1, 25))
        # Shine
        pygame.draw.rect(DISPLAY, (255, 255, 255), (21, 438, strip_hp_w, 4), border_radius=2)

        DISPLAY.blit(shop, (0, 0))

        for button in g['buttons']:
            bi  = g['buttons'].index(button)
            bx  = 220 + bi * 125

            # Glowing card behind each button
            card_s = pygame.Surface((110, 80), pygame.SRCALPHA)
            card_s.fill((20, 10, 40, 180))
            pygame.draw.rect(card_s, (100, 65, 180, 200), (0, 0, 110, 80), 2, border_radius=10)
            DISPLAY.blit(card_s, (bx - 5, 385))

            DISPLAY.blit(button.sprite, (bx, 393))
            DISPLAY.blit(button.typeIndicatorSprite, (202 + bi*125, 377))

            # Price in golden text
            price_s = font_small.render(str(button.price), True, (255, 210, 80))
            DISPLAY.blit(price_s, (262 + bi*125, 408))

            # Level badge
            lvl_bg = pygame.Surface((52, 18), pygame.SRCALPHA)
            lvl_bg.fill((138, 80, 220, 160))
            pygame.draw.rect(lvl_bg, (180, 120, 255, 200), (0, 0, 52, 18), 1, border_radius=5)
            DISPLAY.blit(lvl_bg, (232 + bi*125, 440))
            lvl_s = font_20.render(f"Lv.{button.level}", True, (240, 220, 255))
            DISPLAY.blit(lvl_s, (234 + bi*125, 441))

        # Bean counter in shop strip — glowing amber text
        bc_shop = font_small.render(str(g['beanCount']).zfill(7), True, (255, 210, 80))
        DISPLAY.blit(bc_shop, (72, 394))

        # ── COMBO display ─────────────────────────────────────────
        if g['combo'] >= 3:
            combo_alpha = int(255 * min(1.0, g['combo_timer'] / 20))
            combo_bg = pygame.Surface((180, 36), pygame.SRCALPHA)
            combo_bg.fill((255, 180, 0, int(combo_alpha * 0.25)))
            pygame.draw.rect(combo_bg, (255, 200, 60, combo_alpha), (0, 0, 180, 36), 2, border_radius=10)
            DISPLAY.blit(combo_bg, (320 - 90, 46))
            cs = font_small.render(f"✦ x{g['combo']} COMBO!", True, (255, 230, 60))
            cs.set_alpha(combo_alpha)
            DISPLAY.blit(cs, (320 - cs.get_width()//2, 50))

        # ── Toasts ───────────────────────────────────────────────
        for i, toast in enumerate(g['toasts']):
            ts_bg = pygame.Surface((min(400, font_20.size(toast.text)[0] + 24), 26), pygame.SRCALPHA)
            ts_bg.fill((20, 10, 40, int(toast.alpha * 0.55)))
            pygame.draw.rect(ts_bg, (*toast.color, toast.alpha), (0, 0, ts_bg.get_width(), 26), 1, border_radius=8)
            tx = 320 - ts_bg.get_width()//2
            DISPLAY.blit(ts_bg, (tx, 88 + i*28))
            ts = font_20.render(toast.text, True, toast.color)
            ts.set_alpha(toast.alpha)
            DISPLAY.blit(ts, (320 - ts.get_width()//2, 91 + i*28))

        # ── DYING: bean tumbles and falls, then transitions to DEAD ──
        if state == State.DYING:
            g['die_timer'] += dt

            # Physics: fall fast with spin
            player.velocity.y = clamp(
                player.velocity.y + player.acceleration * dt * 2.5, -99999, 60)
            player.position.y += player.velocity.y * dt
            g['die_spin'] += 6 * dt

            # Camera follows bean down
            camOffset = (-player.position.y + DISPLAY.get_height()//2
                         - player.currentSprite.get_size()[1]//2)

            # Spawn ember particles
            if int(g['die_timer']) % 4 == 0:
                g['particles'].append(Particle(
                    player.position.x + player.currentSprite.get_width()//2,
                    player.position.y + camOffset,
                    (200, 80, 30), speed_range=(1, 3)))

            # Draw spinning shrinking bean
            base_spr = pygame.transform.rotate(player.currentSprite, g['die_spin'])
            shrink   = max(0.1, 1.0 - g['die_timer'] / 80)
            sw2 = max(4, int(base_spr.get_width()  * shrink))
            sh2 = max(4, int(base_spr.get_height() * shrink))
            dying_spr = pygame.transform.scale(base_spr, (sw2, sh2))
            DISPLAY.blit(dying_spr, (
                int(player.position.x + player.currentSprite.get_width()//2  - sw2//2),
                int(player.position.y + camOffset + player.currentSprite.get_height()//2 - sh2//2)))

            # Particles on top
            psurf2 = pygame.Surface((640, 480), pygame.SRCALPHA)
            for p in g['particles']: p.draw(psurf2)
            DISPLAY.blit(psurf2, (0, 0))

            # Darkening vignette
            vfade = min(220, int(g['die_timer'] * 3.0))
            vsurf = pygame.Surface((640, 480), pygame.SRCALPHA)
            vsurf.fill((0, 0, 0, vfade))
            DISPLAY.blit(vsurf, (0, 0))

            # After ~2 seconds → switch to DEAD
            if g['die_timer'] >= 120:
                state = State.DEAD
                g['dead_anim'] = 0.0   # fade-in counter for game over screen

            pygame.display.update(); pygame.time.delay(10); continue

        # ── DEAD: full standalone game-over screen ───────────────
        if state == State.DEAD:
            g['dead_anim'] = min(1.0, g.get('dead_anim', 0.0) + 0.025 * dt)
            fade = g['dead_anim']

            # ── Background: deep red-black gradient ──────────────
            for row in range(0, 480, 2):
                f4 = row / 480
                r4 = int((18  + f4 * 8)  * fade)
                g4 = int((4   + f4 * 2)  * fade)
                b4 = int((10  + f4 * 8)  * fade)
                pygame.draw.rect(DISPLAY, (r4, g4, b4), (0, row, 640, 2))

            # Ambient red glow at top
            glow_s = pygame.Surface((640, 240), pygame.SRCALPHA)
            for gi in range(5):
                ga = int(30 * fade * (1 - gi/5))
                pygame.draw.ellipse(glow_s, (200, 30, 30, ga),
                                    (-60 + gi*10, -40 + gi*8, 760 - gi*20, 200 - gi*20))
            DISPLAY.blit(glow_s, (0, 0))

            # Floating ember particles (reuse existing system)
            psurf3 = pygame.Surface((640, 480), pygame.SRCALPHA)
            for p in g['particles']:
                p.update(dt)
                p.draw(psurf3)
            DISPLAY.blit(psurf3, (0, 0))
            g['particles'] = [p for p in g['particles'] if p.life > 0]

            # ── Panel ────────────────────────────────────────────
            panel_a = int(210 * fade)
            panel_s = pygame.Surface((500, 340), pygame.SRCALPHA)
            panel_s.fill((12, 4, 18, panel_a))
            pygame.draw.rect(panel_s, (160, 30, 30, panel_a), (0, 0, 500, 340), 2, border_radius=18)
            DISPLAY.blit(panel_s, (70, 60))

            # ── GAME OVER title ───────────────────────────────────
            pulse2 = 0.85 + 0.15 * math.sin(time.time() * 3.5)
            go_col = (int(255 * pulse2), int(60 * pulse2), int(50 * pulse2))
            go_surf = font_small.render("GAME  OVER", True, go_col)
            go_surf.set_alpha(int(255 * fade))
            # Stroke
            go_stk = font_small.render("GAME  OVER", True, (80, 10, 10))
            go_stk.set_alpha(int(255 * fade))
            for ddx, ddy in [(-2,0),(2,0),(0,-2),(0,2)]:
                DISPLAY.blit(go_stk, (320 - go_surf.get_width()//2 + ddx, 78 + ddy))
            DISPLAY.blit(go_surf, (320 - go_surf.get_width()//2, 78))

            # Divider line
            line_a = int(120 * fade)
            pygame.draw.line(DISPLAY, (160, 30, 30, line_a), (110, 126), (530, 126), 1)

            # ── Run stats ────────────────────────────────────────
            run_time = time.time() - g['speedrun_start']
            run_mins = int(run_time // 60)
            run_secs = int(run_time % 60)
            is_new_best = g['height'] >= high_score and high_score > 0

            stats = [
                ("📍 Height",        f"{g['height']}m",
                    (255, 215, 0) if is_new_best else (200, 200, 255)),
                ("☕ Beans",          str(g['beanCount']),       (255, 200, 100)),
                ("🔥 Best Combo",     f"x{g['max_combo']}",      (255, 160, 60)),
                ("⏱ Time",           f"{run_mins:02d}:{run_secs:02d}", (140, 220, 160)),
                ("🏆 All-time Best",  f"{high_score}m",
                    (255, 215, 0) if is_new_best else (160, 150, 200)),
            ]
            for si, (label, value, vcol) in enumerate(stats):
                row_y  = 138 + si * 38
                row_a  = int(255 * min(1.0, fade * 2 - si * 0.15))
                row_bg = pygame.Surface((480, 32), pygame.SRCALPHA)
                row_bg.fill((255, 255, 255, 12))
                pygame.draw.rect(row_bg, (120, 30, 30, 60), (0, 0, 480, 32), 1, border_radius=7)
                DISPLAY.blit(row_bg, (80, row_y))
                lbl_s2 = font_14.render(label, True, (160, 130, 160))
                lbl_s2.set_alpha(row_a)
                DISPLAY.blit(lbl_s2, (92, row_y + 7))
                val_s = font_20.render(value, True, vcol)
                val_s.set_alpha(row_a)
                DISPLAY.blit(val_s, (530 - val_s.get_width(), row_y + 6))

            # NEW BEST banner
            if is_new_best:
                nb_pulse = int(200 + 55 * math.sin(time.time() * 4))
                nb_s = font_20.render("✦ NEW RECORD! ✦", True, (255, 230, 0))
                nb_s.set_alpha(nb_pulse)
                DISPLAY.blit(nb_s, (320 - nb_s.get_width()//2, 330))

            # Unlocked achievements
            if new_achievements:
                ach_s = font_14.render(
                    "★ UNLOCKED: " + ", ".join(
                        ACHIEVEMENTS_DEF[k]['label'] for k in new_achievements[:2]),
                    True, (255, 215, 0))
                ach_s.set_alpha(int(255 * fade))
                DISPLAY.blit(ach_s, (320 - ach_s.get_width()//2, 355))

            # ── Buttons ──────────────────────────────────────────
            btn_a = int(255 * min(1.0, fade * 1.8))

            # RETRY button
            retry_r = pygame.Rect(140, 400, 160, 44)
            hov_retry = retry_r.collidepoint(mouseX, mouseY)
            retry_bg = pygame.Surface((160, 44), pygame.SRCALPHA)
            retry_bg.fill((138, 40, 220, 190) if hov_retry else (80, 20, 140, 180))
            pygame.draw.rect(retry_bg,
                             (200, 100, 255) if hov_retry else (120, 50, 200),
                             (0, 0, 160, 44), 2, border_radius=12)
            retry_bg.set_alpha(btn_a)
            DISPLAY.blit(retry_bg, (retry_r.x, retry_r.y))
            rl2 = font_20.render("▶  RETRY", True, (240, 220, 255))
            rl2.set_alpha(btn_a)
            DISPLAY.blit(rl2, (retry_r.centerx - rl2.get_width()//2,
                               retry_r.centery - rl2.get_height()//2))

            # MAIN MENU button
            menu_r = pygame.Rect(340, 400, 160, 44)
            hov_menu2 = menu_r.collidepoint(mouseX, mouseY)
            menu_bg2 = pygame.Surface((160, 44), pygame.SRCALPHA)
            menu_bg2.fill((50, 30, 80, 190) if hov_menu2 else (30, 15, 50, 180))
            pygame.draw.rect(menu_bg2,
                             (120, 80, 200) if hov_menu2 else (70, 45, 120),
                             (0, 0, 160, 44), 2, border_radius=12)
            menu_bg2.set_alpha(btn_a)
            DISPLAY.blit(menu_bg2, (menu_r.x, menu_r.y))
            ml2 = font_20.render("⌂  MENU", True, (200, 190, 230))
            ml2.set_alpha(btn_a)
            DISPLAY.blit(ml2, (menu_r.centerx - ml2.get_width()//2,
                               menu_r.centery - ml2.get_height()//2))

            # Button actions (only register clicks after screen has faded in)
            if fade >= 0.6:
                if clicked and retry_r.collidepoint(mouseX, mouseY):
                    ghost.start_new_run()
                    g = reset_game(DISPLAY, player, persistent_upgrades)
                    reached_milestones = set()
                    new_achievements = []
                    pygame.mixer.Sound.play(upgradefx)
                    state = State.PLAYING
                if clicked and menu_r.collidepoint(mouseX, mouseY):
                    pu_pool_beans += g.get('run_bean_count', 0)
                    ghost.save_run()
                    g = reset_game(DISPLAY, player, persistent_upgrades)
                    reached_milestones = set()
                    new_achievements = []
                    state = State.TITLE; menu_tab = 0; menu_tab_anim = 0.0

            pygame.display.update(); pygame.time.delay(10); continue

        # ── PLAYING logic ────────────────────────────────────────
        if state != State.PLAYING:
            pygame.display.update(); pygame.time.delay(10); continue

        g['difficulty'] = 1.0+abs(player.position.y-g['startingHeight'])/(DISPLAY.get_height()*10)
        health_drain    = 0.10*g['difficulty']

        g['caffeine'].update(dt)
        rush_mult = 1.8 if g['caffeine'].active else 1.0

        if g['caffeine'].active:
            th = colorsys.hsv_to_rgb(hue_base,1,1)
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
                g['run_bean_count'] += bonus
                g['health']     = min(100,g['health']+30)
                g['caffeine'].charges = min(3,g['caffeine'].charges+1)
                g['toasts'].append(Toast(f"GOLDEN BEAN  +{bonus}!",(255,215,0)))
                for _ in range(25):
                    g['particles'].append(Particle(gr.centerx,gr.centery+camOffset,(255,215,0),(3,8)))
                g['golden_beans'].remove(gb)

        # Bean magnet spawn
        g['magnet_timer'] += dt
        if g['magnet_timer'] >= 800 and len(g['bean_magnets']) < 1:
            g['magnet_timer'] = 0
            if random.random() < 0.4:
                g['bean_magnets'].append(BeanMagnet(player.position.y,640,480))

        for bm in g['bean_magnets'][:]:
            bm.update(dt)
            if not bm.active:
                br = bm.collect_rect()
                if checkCollisions(player.position.x, player.position.y,
                        player.currentSprite.get_width(), player.currentSprite.get_height(),
                        br.x, br.y, br.width, br.height):
                    bm.activate()
                    g['toasts'].append(Toast("BEAN MAGNET!", (220, 100, 255)))
                    pygame.mixer.Sound.play(upgradefx)
                if bm.y + camOffset > 560:
                    g['bean_magnets'].remove(bm)
            # If active, pull beans toward player
            if bm.active:
                PULL_RANGE = 200
                PULL_SPEED = 4.0
                for bean in g['beans']:
                    bdx = player.position.x - bean.position.x
                    bdy = player.position.y - bean.position.y
                    bdist = math.hypot(bdx, bdy) or 1
                    if bdist < PULL_RANGE:
                        bean.position.x += (bdx/bdist) * PULL_SPEED * dt
                        bean.position.y += (bdy/bdist) * PULL_SPEED * dt

        # Bean cloud zone spawn
        g['cloud_timer'] += dt
        if g['cloud_timer'] >= 600:
            g['cloud_timer'] = 0
            if random.random() < 0.3 and len(g['bean_clouds']) < 2:
                g['bean_clouds'].append(BeanCloudZone(player.position.y,640,480))

        # Bean cloud zone collection
        for bcz in g['bean_clouds'][:]:
            if not bcz.active:
                g['bean_clouds'].remove(bcz); continue
            bob = math.sin(t*2 + bcz.bob_t) * 4
            collected = bcz.collect_beans(player.position.x, player.position.y,
                player.currentSprite.get_width(), player.currentSprite.get_height(),
                camOffset, bob)
            for (cx_, cy_) in collected:
                pygame.mixer.Sound.play(beanfx)
                bonus = 1 * (2 if g['caffeine'].active else 1)
                g['beanCount'] += bonus
                g['run_bean_count'] += bonus
                g['health'] = min(100, g['health'] + 5)
                g['floating_texts'].append(FloatingText(f"+{bonus}", cx_, cy_, (255,200,80)))
                for _ in range(4):
                    g['particles'].append(Particle(cx_, cy_, (200,140,80)))

        # Mini boss at 50m
        if g['height'] >= 50 and not g['boss_spawned']:
            g['boss_spawned'] = True
            g['mini_boss'] = MiniBoss(player.position.x, player.position.y, 640, 480)
            g['toasts'].append(Toast("MINI BOSS INCOMING!", (255,60,60)))

        if g['mini_boss'] and g['mini_boss'].alive:
            g['mini_boss'].update(player.position.x, player.position.y, dt)
            mbr = g['mini_boss'].hit_rect()
            # Player hits boss (from above)
            if checkCollisions(player.position.x, player.position.y,
                    player.currentSprite.get_width(), player.currentSprite.get_height(),
                    mbr.x, mbr.y, mbr.width, mbr.height):
                if player.velocity.y < -1:
                    g['mini_boss'].hp -= 1
                    g['mini_boss'].shake = 20
                    player.velocity.y = 4
                    if g['mini_boss'].hp <= 0:
                        g['mini_boss'].alive = False
                        g['beanCount'] += MiniBoss.REWARD
                        g['run_bean_count'] += MiniBoss.REWARD
                        g['health'] = min(100, g['health'] + 25)
                        g['boss_survived'] = True
                        g['toasts'].append(Toast(f"BOSS DEFEATED! +{MiniBoss.REWARD}☕",(255,215,0)))
                        pygame.mixer.Sound.play(upgradefx)
                        for _ in range(40):
                            g['particles'].append(Particle(
                                player.position.x+14, player.position.y+camOffset+14, (255,120,60),(3,9)))
                else:
                    g['health'] -= 0.5 * dt
            if g['mini_boss'].expired() and g['mini_boss'].alive:
                g['mini_boss'].alive = False
                if g['boss_survived'] is False:
                    g['boss_survived'] = True  # survived by outlasting
                    g['toasts'].append(Toast("Boss fled!", (200,200,200)))

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
        if g['health'] <= 0 and state == State.PLAYING:
            g['health'] = 0
            state = State.DYING
            g['die_timer'] = 0          # counts up during fall animation
            g['die_fade']  = 0          # 0→255 black fade-in
            player.velocity.x = 0       # stop horizontal movement
            player.velocity.y = -4      # small upward pop then fall
            g['die_spin']  = 0.0        # rotation angle
            g['shake'] = 12
            for _ in range(40):
                g['particles'].append(Particle(
                    player.position.x + player.currentSprite.get_width()//2,
                    player.position.y + player.currentSprite.get_height()//2 + camOffset,
                    (255, 100, 50)))
            pygame.mixer.Sound.play(deadfx)
            if g['height'] > high_score:
                high_score = g['height']; save_high_score(high_score)
            lifetime_beans += g['run_bean_count']
            save_lifetime_beans(lifetime_beans)
            pu_pool_beans  += g['run_bean_count']
            ghost.save_run()
            # Check achievements
            new_achievements = []
            run_elapsed = time.time() - g['speedrun_start']
            checks = {
                'first_100m':       g['height'] >= 100,
                'bean_millionaire': lifetime_beans >= 1000,
                'combo_king':       g['max_combo'] >= 10,
                'survived_boss':    g.get('boss_survived', False),
                'speedrun_50':      g['height'] >= 50 and run_elapsed <= 30,
            }
            for key, cond in checks.items():
                if cond and key not in achievements:
                    achievements.add(key)
                    new_achievements.append(key)
            if new_achievements:
                save_achievements(achievements)

        for bean in g['beans']:
            if bean.position.y+camOffset+90 > DISPLAY.get_height():
                bean.position.y-=DISPLAY.get_height()*2
                bean.position.x =random.randrange(0,DISPLAY.get_width()-bean.sprite.get_width())
            if checkCollisions(player.position.x,player.position.y,
                    player.currentSprite.get_width(),player.currentSprite.get_height(),
                    bean.position.x,bean.position.y,bean.sprite.get_width(),bean.sprite.get_height()):
                pygame.mixer.Sound.play(beanfx)
                g['combo_timer']=70; g['combo']+=1
                if g['combo'] > g['max_combo']:
                    g['max_combo'] = g['combo']
                bonus=max(1,g['combo']//3)*(2 if g['caffeine'].active else 1)
                g['beanCount']+=bonus
                g['run_bean_count']+=bonus
                g['health']=min(100,g['health']+12)
                bean.position.y-=DISPLAY.get_height()-random.randrange(0,200)
                bean.position.x =random.randrange(0,DISPLAY.get_width()-bean.sprite.get_width())
                for _ in range(10):
                    g['particles'].append(Particle(
                        bean.position.x+bean.sprite.get_width()//2,
                        bean.position.y+bean.sprite.get_height()//2+camOffset,(200,140,80)))
                # Floating score text
                fx_x = bean.position.x + bean.sprite.get_width()//2
                fx_y = bean.position.y + camOffset
                g['floating_texts'].append(FloatingText(f"+{bonus}", fx_x, fx_y,
                    (255, 200, 80) if bonus == 1 else (255, 80, 255)))

        g['combo_timer']-=dt
        if g['combo_timer']<=0: g['combo']=0

        for p in g['particles'][:]:
            p.update(dt)
            if p.life<=0: g['particles'].remove(p)
        for td in g['trail'][:]:
            td.update(dt)
            if td.life<=0: g['trail'].remove(td)
        for ft in g['floating_texts'][:]:
            if ft.life <= 0: g['floating_texts'].remove(ft)

        g['shake']=max(0.0,g['shake']-0.5*dt)

        for to in g['toasts'][:]:
            to.timer-=dt
            if to.timer<=0: g['toasts'].remove(to)

        g['height']=round(-(player.position.y-g['startingHeight'])/DISPLAY.get_height())
        for m in MILESTONE_HEIGHTS:
            if g['height']>=m and m not in reached_milestones:
                reached_milestones.add(m)
                g['toasts'].append(Toast(f"  {m}m — {get_zone_name(g['height'])}!"))

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

        # Ghost recording
        ghost.record(player.position.x, player.position.y)

        pygame.display.update()
        pygame.time.delay(10)

if __name__ == "__main__":
    main()