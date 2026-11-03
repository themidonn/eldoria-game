import pygame
from settings import *

class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont('arial', 20, bold=True)

    def _heart(self, screen, x, y, color):
        pygame.draw.circle(screen, color, (x+8, y+8), 8)
        pygame.draw.circle(screen, color, (x+20, y+8), 8)
        pygame.draw.polygon(screen, color,
                            [(x, y+10), (x+28, y+10), (x+14, y+26)])
        pygame.draw.polygon(screen, (20, 20, 20),
                            [(x, y+10), (x+28, y+10), (x+14, y+26)], 1)

    def draw(self, screen, player, total):
        for i in range(player.max_hp):
            color = (220, 60, 60) if i < player.hp else (80, 30, 30)
            self._heart(screen, 20 + i*32, 20, color)
        pygame.draw.circle(screen, COLOR_CRYSTAL, (WIDTH - 130, 30), 12)
        pygame.draw.circle(screen, (100, 180, 220), (WIDTH - 130, 30), 12, 2)
        screen.blit(self.font.render(f"x {player.crystals}/{total}", True,
                                     (240, 240, 240)), (WIDTH - 110, 20))