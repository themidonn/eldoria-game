import math, pygame
from settings import *

class Crystal:
    def __init__(self, x, y, name="Кристалл Света"):
        self.x, self.y = x, y
        self.w, self.h = 24, 24
        self.name = name
        self.collected = False
        self.bob = 0
        # glow кэшируется один раз
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (180, 240, 255, 80), (30, 30), 30)

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
        screen.blit(self.glow, (sx - 18, sy - 18))
        pts = [(sx+12, sy), (sx+24, sy+10), (sx+20, sy+24),
               (sx+4, sy+24), (sx, sy+10)]
        pygame.draw.polygon(screen, COLOR_CRYSTAL, pts)
        pygame.draw.polygon(screen, (100, 180, 220), pts, 2)
        pygame.draw.line(screen, (255, 255, 255), (sx+12, sy+4), (sx+8, sy+16), 2)