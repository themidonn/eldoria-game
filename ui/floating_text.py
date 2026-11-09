"""
ui/floating_text.py — Всплывающий текст над игроком.

Используется для коротких сообщений: «-1», «+1 HP»,
«Кристалл Света!», «Морвейн пал!» и т.п.

Поднимается вверх ~40 px/сек. Первые 60% жизни полностью
виден, последние 40% — плавно тает (alpha 255 → 0).

Используется в game.py:
  - _update_level_1() / _update_level_2() — при уроне, подборе, лечении
  - _try_read_lore_stone() — «Знание предков! +1 Макс. HP»
  - _try_open_chest() — «Сокровище найдено!»
  - _handle_keydown() — «Сохранено»
  - _update_common() — update + фильтрация мёртвых
  - _draw_ui() — draw

ВАЖНО: конструктор вызывает pygame.font.Font() —
перед созданием FloatingText должен быть вызван pygame.font.init().
В main.py это гарантировано: init до импорта Game.
"""

import pygame
from settings import *


class FloatingText:

    # ============================================================
    #   КЛАССОВЫЙ КЭШ (общий для всех экземпляров)
    # ============================================================
    # Шрифт один на все всплывающие тексты — ленивая инициализация
    # при создании первого экземпляра.
    _font = None

    # Доля жизни, после которой начинается затухание.
    # 0.6 = первые 60% жизни текст полностью виден.
    FADE_START = 0.6

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, text, color=COLOR_UI_TEXT, duration=1200):
        # --- Ленивая инициализация шрифта ---
        # Один раз на весь класс — не грузим ttf для каждого текста.
        if FloatingText._font is None:
            try:
                FloatingText._font = pygame.font.Font(
                    "assets/Tiny5-Bold.ttf", 24
                )
            except FileNotFoundError:
                FloatingText._font = pygame.font.Font(None, 24)

        # --- Позиция и таймеры ---
        # float(x) для консистентности с entity.
        self.x = float(x)
        self.y = float(y)
        self.duration = duration              # мс — общая жизнь
        self.elapsed = 0                      # мс — сколько уже прожил
        self.dead = False

        # --- Две поверхности: цветной текст + чёрная тень ---
        # Обе рендерятся один раз в конструкторе.
        # В draw() только set_alpha + blit.
        self.text_surf   = FloatingText._font.render(text, True, color)
        self.shadow_surf = FloatingText._font.render(text, True, (0, 0, 0))

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, dt):
        # Мёртвый текст не двигается — game.py отфильтрует его
        # в _update_common сразу после вызова update.
        if self.dead:
            return

        self.elapsed += dt
        # 0.04 px/мс = 40 px/сек — плавный подъём.
        self.y -= dt * 0.04

        if self.elapsed >= self.duration:
            self.dead = True

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        if self.dead:
            return

        # --- Затухание в последние 40% жизни ---
        # duration <= 0 — защита от деления на ноль. Такого не должно
        # случаться (default=1200, вызовы с 600..2500), но защита есть.
        if self.duration > 0 and self.elapsed > self.duration * self.FADE_START:
            # p = 0 в начале затухания, 1 в конце
            p = ((self.elapsed - self.duration * self.FADE_START)
                 / (self.duration * (1 - self.FADE_START)))
            alpha = max(0, int(255 * (1 - p)))

            # set_alpha на текстовых поверхностях — Pygbag-safe:
            # font.render с antialias в pygame-ce 2.5+ корректно
            # поддерживает per-surface alpha в WASM.
            # (Это отличается от glow-поверхностей в key/pickup/potion —
            # там SRCALPHA с per-pixel alpha, и там безопаснее
            # задавать alpha через цвет.)
            self.text_surf.set_alpha(alpha)
            self.shadow_surf.set_alpha(alpha)

        # int() для WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x) - self.text_surf.get_width() // 2
        sy = int(self.y - cam.y)

        # --- Тень (1 px смещена) + основной текст ---
        # Тень даёт читаемость на любом фоне (трава, камень, тёмная мантия).
        screen.blit(self.shadow_surf, (sx + 1, sy + 1))
        screen.blit(self.text_surf,   (sx, sy))