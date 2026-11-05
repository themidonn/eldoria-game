import math, pygame
from settings import *


class Key:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w, self.h = 24, 24
        self.collected = False
        self.bob = 0

        # Кэшируем золотое свечение
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255, 215, 0, 80), (30, 30), 30)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, dt):
        self.bob += dt * 0.005

    def draw(self, screen, cam):
        if self.collected:
            return
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 4)

        # Свечение
        screen.blit(self.glow, (sx - 18, sy - 18))

        # Основа ключа (кольцо)
        pygame.draw.circle(screen, (255, 215, 0), (sx + 8, sy + 8), 5, 2)
        # Стержень
        pygame.draw.line(screen, (255, 215, 0), (sx + 11, sy + 11), (sx + 18, sy + 18), 3)
        # Зубчики
        pygame.draw.line(screen, (255, 215, 0), (sx + 15, sy + 15), (sx + 18, sy + 12), 2)
        pygame.draw.line(screen, (255, 215, 0), (sx + 18, sy + 18), (sx + 20, sy + 16), 2)