import pygame
from settings import *


class FloatingText:
    # Кэшируем шрифт на уровне класса (создается один раз при импорте)
    _font = None

    def __init__(self, x, y, text, color=COLOR_UI_TEXT, duration=1200):
        # Ленивая инициализация шрифта при первом создании объекта
        if FloatingText._font is None:
            FloatingText._font = pygame.font.SysFont('arial', 22, bold=True)

        self.x = float(x)
        self.y = float(y)
        self.duration = duration
        self.elapsed = 0
        self.dead = False

        # Используем общий шрифт
        self.text_surf = FloatingText._font.render(text, True, color)
        self.shadow_surf = FloatingText._font.render(text, True, (0, 0, 0))

    def update(self, dt):
        self.elapsed += dt
        self.y -= dt * 0.04
        if self.elapsed >= self.duration:
            self.dead = True

    def draw(self, screen, cam):
        if self.dead:
            return
        if self.elapsed > self.duration * 0.6:
            p = (self.elapsed - self.duration * 0.6) / (self.duration * 0.4)
            alpha = max(0, int(255 * (1 - p)))
            self.text_surf.set_alpha(alpha)
            self.shadow_surf.set_alpha(alpha)
        sx = int(self.x - cam.x) - self.text_surf.get_width() // 2
        sy = int(self.y - cam.y)
        screen.blit(self.shadow_surf, (sx + 1, sy + 1))
        screen.blit(self.text_surf, (sx, sy))