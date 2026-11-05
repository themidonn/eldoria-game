"""
ui/floating_text.py — Всплывающий текст над игроком.

Используется для коротких сообщений: «-1», «+1 HP»,
«Кристалл Света!», «Морвейн пал!» и т.п.

Поднимается вверх ~40 px/сек. Первые 60% жизни полностью
виден, последние 40% — плавно тает (alpha 255 → 0).
"""

import pygame
from settings import *


class FloatingText:

    # ============================================================
    #   КЛАССОВЫЙ КЭШ (общий для всех экземпляров)
    # ============================================================
    # Шрифт создаётся один раз — при первом создании объекта.
    # Все экземпляры используют его совместно.
    _font = None

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, text, color=COLOR_UI_TEXT, duration=1200):
        # Ленивая инициализация шрифта
        if FloatingText._font is None:
            FloatingText._font = pygame.font.SysFont('arial', 22, bold=True)

        self.x = float(x)
        self.y = float(y)
        self.duration = duration              # мс — общая жизнь
        self.elapsed = 0                      # мс — сколько уже прожил
        self.dead = False

        # Две поверхности: цветной текст + чёрная тень.
        # У каждого объекта свои — поэтому set_alpha в draw()
        # не влияет на другие тексты.
        self.text_surf   = FloatingText._font.render(text, True, color)
        self.shadow_surf = FloatingText._font.render(text, True, (0, 0, 0))

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, dt):
        self.elapsed += dt
        self.y -= dt * 0.04                   # подъём вверх ~40 px/сек

        if self.elapsed >= self.duration:
            self.dead = True

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        if self.dead:
            return

        # --- Затухание в последние 40% жизни ---
        FADE_START = 0.6                      # 60% — виден полностью
        if self.elapsed > self.duration * FADE_START:
            # p = 0 в начале затухания, 1 в конце
            p = (self.elapsed - self.duration * FADE_START) / (self.duration * (1 - FADE_START))
            alpha = max(0, int(255 * (1 - p)))
            self.text_surf.set_alpha(alpha)
            self.shadow_surf.set_alpha(alpha)

        # int() для WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x) - self.text_surf.get_width() // 2
        sy = int(self.y - cam.y)

        # --- Тень (1 px смещена) + основной текст ---
        screen.blit(self.shadow_surf, (sx + 1, sy + 1))
        screen.blit(self.text_surf,   (sx, sy))