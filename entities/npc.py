import pygame
from settings import *

class NPC:
    def __init__(self, x, y, name, color=COLOR_ELDER):
        self.x, self.y = x, y
        self.w, self.h = 30, 34
        self.name = name
        self.color = color
        self.font = pygame.font.SysFont('arial', 12)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def draw(self, screen, cam):
        sx, sy = int(self.x - cam.x), int(self.y - cam.y)
        pygame.draw.rect(screen, self.color, (sx, sy, self.w, self.h), border_radius=6)
        pygame.draw.rect(screen, (30, 30, 30), (sx, sy, self.w, self.h), 2, border_radius=6)
        pygame.draw.circle(screen, (0, 0, 0), (sx+9, sy+12), 2)
        pygame.draw.circle(screen, (0, 0, 0), (sx+self.w-9, sy+12), 2)
        t = self.font.render(self.name, True, (255, 255, 255))
        screen.blit(t, (sx + self.w//2 - t.get_width()//2, sy - 14))