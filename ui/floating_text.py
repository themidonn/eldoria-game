import pygame
from settings import *

class FloatingText:
    def __init__(self, x, y, text, color=COLOR_UI_TEXT, duration=1200):
        self.x = float(x)
        self.y = float(y)
        self.duration = duration
        self.elapsed = 0
        self.dead = False
        # шрифты и поверхности кэшируются один раз
        self.font = pygame.font.SysFont('arial', 22, bold=True)
        self.text_surf = self.font.render(text, True, color)
        self.shadow_surf = self.font.render(text, True, (0, 0, 0))

    def update(self, dt):
        self.elapsed += dt
        self.y -= dt * 0.04        # поднимается вверх ~40 px/сек
        if self.elapsed >= self.duration:
            self.dead = True

    def draw(self, screen, cam):
        if self.dead:
            return
        # плавное исчезновение в последние 40% времени
        if self.elapsed > self.duration * 0.6:
            p = (self.elapsed - self.duration * 0.6) / (self.duration * 0.4)
            alpha = max(0, int(255 * (1 - p)))
            self.text_surf.set_alpha(alpha)
            self.shadow_surf.set_alpha(alpha)
        sx = int(self.x - cam.x) - self.text_surf.get_width() // 2
        sy = int(self.y - cam.y)
        screen.blit(self.shadow_surf, (sx + 1, sy + 1))
        screen.blit(self.text_surf, (sx, sy))