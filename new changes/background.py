import pygame
import colorsys

class Background:
    def __init__(self):
        self.sprite = pygame.image.load('data/gfx/bg.png')
        self.position = 0
        self.uncoloredSprite = pygame.image.load('data/gfx/bg.png')

    def setSprite(self, tint):
        copy = self.uncoloredSprite.copy()
        color = colorsys.hsv_to_rgb(tint, 1, 1)
        copy.fill((color[0]*255, color[1]*255, color[2]*255), special_flags=pygame.BLEND_ADD)
        self.sprite = copy

    def setSpriteNight(self, tint, night_factor):
        """
        Blend between normal tinted sprite (day) and a dark-blue tinted sprite (night).
        night_factor: 0.0 = full day, 1.0 = full night
        """
        copy = self.uncoloredSprite.copy()
        # Day color
        color = colorsys.hsv_to_rgb(tint, 1, 1)
        day_r, day_g, day_b = color[0]*255, color[1]*255, color[2]*255
        # Night color (deep blue tint)
        night_r, night_g, night_b = 10, 20, 60
        r = int(day_r * (1 - night_factor) + night_r * night_factor)
        g = int(day_g * (1 - night_factor) + night_g * night_factor)
        b = int(day_b * (1 - night_factor) + night_b * night_factor)
        copy.fill((r, g, b), special_flags=pygame.BLEND_ADD)
        # Darken overall at night
        if night_factor > 0:
            dark = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
            dark.fill((0, 0, 0, int(night_factor * 160)))
            copy.blit(dark, (0, 0))
        self.sprite = copy
