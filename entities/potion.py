import math, pygame
from settings import *

class Potion:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w, self.h = 24, 24
        self.collected = False
        self.bob = 0
        # свечение кэшируем один раз (как у кристалла)
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255, 150, 150, 70), (30, 30), 30)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, dt):
        self.bob += dt * 0.005

    def draw(self, screen, cam):
        if self.collected:
            return
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 3)
        screen.blit(self.glow, (sx - 18, sy - 18))
        # горлышко
        pygame.draw.rect(screen, (80, 60, 40), (sx+9, sy+2, 6, 8))
        # пробка
        pygame.draw.rect(screen, (150, 100, 50), (sx+8, sy, 8, 4), border_radius=2)
        # тело флакона
        pygame.draw.rect(screen, (200, 40, 40), (sx+4, sy+8, 16, 14), border_radius=4)
        pygame.draw.rect(screen, (60, 10, 10), (sx+4, sy+8, 16, 14), 1, border_radius=4)
        # блик
        pygame.draw.circle(screen, (255, 200, 200), (sx+8, sy+12), 2)