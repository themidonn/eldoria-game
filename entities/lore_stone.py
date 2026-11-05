import pygame
from settings import *

class LoreStone:
    def __init__(self, x, y, title, text):
        self.x, self.y = x, y
        self.w, self.h = 36, 36
        self.title = title
        self.text = text
        self.is_read = False  # Флаг: прочитал игрок или нет

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def draw(self, screen, cam):
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # Тень
        pygame.draw.ellipse(screen, (20, 40, 20), (sx, sy + 26, self.w, 10))

        # Камень (монолит)
        pygame.draw.rect(screen, (100, 100, 110), (sx + 4, sy, self.w - 8, self.h), border_radius=4)
        pygame.draw.rect(screen, (60, 60, 70), (sx + 4, sy, self.w - 8, self.h), 2, border_radius=4)

        # Руна
        if not self.is_read:
            # Светящаяся синяя руна (привлекает внимание)
            pygame.draw.line(screen, (100, 200, 255), (sx + 18, sy + 8), (sx + 18, sy + 24), 2)
            pygame.draw.line(screen, (100, 200, 255), (sx + 12, sy + 14), (sx + 24, sy + 14), 2)
            pygame.draw.circle(screen, (150, 220, 255), (sx + 18, sy + 16), 3)
        else:
            # Потухшая руна (серая)
            pygame.draw.line(screen, (60, 60, 70), (sx + 18, sy + 8), (sx + 18, sy + 24), 2)
            pygame.draw.line(screen, (60, 60, 70), (sx + 12, sy + 14), (sx + 24, sy + 14), 2)