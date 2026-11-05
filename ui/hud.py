import pygame
from settings import *


class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont('arial', 20, bold=True)
        self._last_text = None
        self._text_surf = None

    def _heart(self, screen, x, y, color):
        outline = (20, 20, 20)

        # 1. Заливка (рисуем фигуры)
        pygame.draw.circle(screen, color, (x + 8, y + 8), 8)
        pygame.draw.circle(screen, color, (x + 20, y + 8), 8)
        pygame.draw.polygon(screen, color, [(x, y + 10), (x + 28, y + 10), (x + 14, y + 26)])

        # 2. Идеальный контур (обводим только внешние края)
        # Круги
        pygame.draw.circle(screen, outline, (x + 8, y + 8), 8, 1)
        pygame.draw.circle(screen, outline, (x + 20, y + 8), 8, 1)

        # Боковые и нижняя линии треугольника
        pygame.draw.line(screen, outline, (x, y + 10), (x + 14, y + 26), 1)
        pygame.draw.line(screen, outline, (x + 28, y + 10), (x + 14, y + 26), 1)

        # Замыкающие линии (маленькие стыки между кругами и треугольником)
        pygame.draw.line(screen, outline, (x, y + 8), (x, y + 10), 1)
        pygame.draw.line(screen, outline, (x + 28, y + 8), (x + 28, y + 10), 1)

    def draw(self, screen, player, total):
        for i in range(player.max_hp):
            color = (220, 60, 60) if i < player.hp else (80, 30, 30)
            self._heart(screen, 20 + i * 32, 20, color)

        pygame.draw.circle(screen, COLOR_CRYSTAL, (WIDTH - 130, 30), 12)
        pygame.draw.circle(screen, (100, 180, 220), (WIDTH - 130, 30), 12, 2)

        # ОПТИМИЗАЦИЯ: Рендерим текст только если количество кристаллов изменилось
        current_text = f"x {player.crystals}/{total}"
        if current_text != self._last_text:
            self._last_text = current_text
            self._text_surf = self.font.render(current_text, True, (240, 240, 240))

        screen.blit(self._text_surf, (WIDTH - 110, 20))