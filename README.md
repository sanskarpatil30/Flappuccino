<p align="center">
  <img src="flappuccino demo.gif" width="420px" alt="Flappuccino gameplay demo">
</p>

<h1 align="center">☕ FLAPPUCCINO</h1>
<p align="center"><strong>Flap. Collect. Rush. Repeat.</strong><br>A coffee-themed arcade game brewed with Python &amp; Pygame — now featuring a full upgrade ecosystem, dynamic weather, a ghost runner, achievements, and a cinematic death sequence.</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Pygame-2.5.0-brightgreen?style=flat-square" alt="Pygame">
  <img src="https://img.shields.io/badge/Version-2.0-orange?style=flat-square" alt="Version 2.0">
  <img src="https://img.shields.io/github/stars/sanskarpatil30/Flappuccino?style=social" alt="Stars">
  <img src="https://img.shields.io/github/license/sanskarpatil30/Flappuccino" alt="License">
</p>

---

## 🎮 About

Flappuccino is a fast-paced vertical climber where you guide a coffee cup upward, collecting beans to stay alive and power up. The higher you climb, the more the world shifts — the sky cycles from bright day to deep night, weather rolls in, and a mini boss ambushes you at 50m.

Every run earns lifetime beans you can spend on permanent upgrades between runs. Your best run is saved as a ghost that races alongside you next time.

---

## 🕹️ Controls

| Action | Input |
|---|---|
| Flap / Jump | `SPACE`, `↑ Up Arrow`, or left-click the play area |
| Activate Caffeine Rush | `R` (requires a charge) |
| Pause / Resume | `ESC` |
| Navigate menus | Mouse click |

---

## ✨ Features

### Core Gameplay
- **Vertical climbing** — the camera follows your cup upward; health drains over time so you must collect beans to survive
- **Shop upgrades** — spend beans mid-run to boost flap power, horizontal speed, or spawn more beans on screen
- **Difficulty scaling** — health drain and wind intensity increase gradually as you climb higher

### Power-ups & Collectibles
- **Golden Beans** — glowing bobbing collectibles worth 5× a normal bean; restore 30 health and grant a Caffeine Rush charge
- **Bean Magnet** — rare purple pickup that pulls all nearby beans toward you for 5 seconds
- **Bean Cloud Zones** — glowing bubble clusters of 20–28 beans that appear rarely; clean them out for a big haul
- **Caffeine Rush** — press `R` to spend a charge: 1.8× horizontal speed, 1.3× flap force, doubled bean value, and a rainbow trail behind you

### Environmental Systems
- **Wind Gusts** — semi-transparent directional zones (blue = push right, orange = push left) that nudge your cup as you fly through them
- **Day / Night Cycle** — the sky shifts from vivid cyan through dusk violet to deep midnight indigo as you climb to 200m+; stars appear at night
- **Parallax Clouds** — three layers of clouds scroll at different speeds for a sense of depth
- **Background Foam Bubbles** — soft white circles drift upward continuously behind everything else
- **Weather Events** — every ~20 seconds the weather can change: Rain (slows visibility), Fog (milky overlay), Lightning (screen flash), or Clear

### Combat
- **Mini Boss at 50m** — a giant angry coffee cup charges at you. Hit it from above (while moving upward) three times to defeat it and earn 30 beans + 25 health. Survive by outlasting it if you can't fight back.

### Visual Polish
- **Squash & Stretch** — the cup stretches while flying up and squashes on the way down
- **Floating Score Text** — `+1` or `+5` floats up from every bean you collect in the matching color
- **Particle Bursts** — bean collects, golden bean grabs, obstacle hits, and death all spray coloured particles
- **Combo Banner** — chaining bean collects quickly builds a combo multiplier displayed with a glowing gold banner
- **Screen Shake** — hits and death trigger camera shake that smoothly decays
- **Zone Names** — each altitude band has a coffee-themed name displayed in-world:

| Height | Zone |
|---|---|
| 0m | Espresso Zone |
| 10m | Latte Layer |
| 25m | Cappuccino Heights |
| 50m | Cloud Roast |
| 100m | Arabica Summit |
| 200m | Stellar Brew |
| 500m | The Void Roast |

### Screens & UI
- **Animated Title Screen** — deep violet starfield, floating bean particles, steam puffs, glowing orb behind the logo, and a three-tab menu (Play / Trophies / Upgrades)
- **Redesigned HUD** — frosted glass panels; health bar changes colour green→yellow→red with a shine strip; caffeine pip indicators; speedrun timer top-right
- **Low Health Flash** — the screen border pulses red when health drops below 30%
- **Milestone Toasts** — hitting 10m, 25m, 50m, 100m, 200m, and 500m shows a named zone toast
- **Pause Menu** — press `ESC` mid-run to pause; shows current height, beans, and zone name
- **Cinematic Death Sequence** — on death the cup spins and shrinks while falling, ember particles trail it, and a darkening vignette fades in before the Game Over screen appears
- **Game Over Screen** — full animated stats panel: height, beans collected, best combo, run time, all-time best, plus RETRY and MAIN MENU buttons

### Persistence & Meta Progression
- **High Score** — best height saved across sessions in `save.json`
- **Lifetime Beans** — total beans collected across all runs, tracked toward the Bean Rich achievement
- **Permanent Upgrades** — from the Upgrades tab on the title screen, spend beans earned across runs to permanently increase starting flap power or speed (persists between sessions)
- **Ghost Runner** — your best run is recorded and replayed as a faint blue ghost alongside you on every subsequent run
- **Speedrun Timer** — live MM:SS.cc timer shown in the top-right HUD; run time is displayed on the Game Over screen

### Achievements

| Badge | Condition |
|---|---|
| 🏆 First 100m | Reach 100m in a single run |
| ☕ Bean Rich | Collect 1000 lifetime beans across all runs |
| 🔥 Combo King | Reach a 10× combo in a single run |
| 👹 Boss Slayer | Defeat or survive the mini boss |
| ⚡ Speed Demon | Reach 50m in under 30 seconds |

---

## 📦 Installation

### 1. Install Python
Download from [python.org](https://www.python.org/downloads/) — Python 3.8 or newer.

### 2. Install Pygame

```bash
# Windows
python -m pip install pygame

# macOS / Linux
python3 -m pip install pygame
```

### 3. Clone and run

```bash
git clone https://github.com/sanskarpatil30/Flappuccino.git
cd Flappuccino
python main.py
```

---

## 🗂️ Project Structure

```
Flappuccino/
│── main.py           # Game loop, all systems and states
│── player.py         # Player sprite and physics properties
│── background.py     # Scrolling background with day/night tinting
│── bean.py           # Regular bean collectible
│── button.py         # Shop upgrade button
│── utils.py          # clamp() and checkCollisions() helpers
│── save.json         # Persistent data (high score, beans, achievements, upgrades)
│── README.md
│
└── data/
    ├── fonts/
    │     └── font.otf
    ├── gfx/
    │     ├── player.png
    │     ├── bg.png
    │     ├── bean.png
    │     ├── button.png
    │     ├── shop.png
    │     ├── shop_bg.png
    │     ├── logo.png
    │     ├── shadow.png
    │     ├── retry_button.png
    │     ├── flap_indicator.png
    │     ├── speed_indicator.png
    │     ├── beanup_indicator.png
    │     └── null_indicator.png
    └── sfx/
          ├── flap.wav
          ├── bean.wav
          ├── dead.wav
          └── upgrade.wav
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a new branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a pull request

For major changes, open an issue first to discuss the idea.

---

## 🎉 Credits

Developed by **Sanskar Patil** ([@sanskarpatil30](https://github.com/sanskarpatil30))
Original game concept inspired by PolyMars.
Assets, gameplay systems, and visual design crafted with love and caffeine ☕

---

## ❤️ Support

If you enjoy this project:

- ⭐ Star the repo
- 🍴 Fork it and build on top
- 📢 Share it with friends

Every star motivates future improvements!
