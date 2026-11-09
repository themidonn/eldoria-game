"""
entities/key.py — Золотой ключ жителя.

Спавнится в случайном месте в лесу (зона задаётся в settings.py:
KEY_ZONE_X_MIN..MAX, KEY_ZONE_Y_MIN..MAX).
Покачивается вверх-вниз, светится золотым, исчезает после подбора.

Используется в game.py:
  - _spawn() — создаёт экземпляр в случайной точке KEY_ZONE
  - _update_level_1() — update + проверка коллизии с игроком
  - _draw_level_1() — draw (только если не собран)
  - save_progress() / load_progress() — сохраняет collected, x, y

ВАЖНО: конструктор создаёт pygame.Surface для свечения —
перед созданием Key должен быть вызван pygame.display.init().
В main.py это гарантировано: init до импорта Game.
"""

import math
import pygame


class Key:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        # float() — для консистентности с bat.py / boss.py / enemy.py.
        self.x = float(x)
        self.y = float(y)

        self.w = self.h = 24
        self.collected = False
        self.bob = 0                          # фаза покачивания

        # Кэшируем свечение один раз (60×60 с альфа-каналом).
        # Создаётся в конструкторе, чтобы не пересоздавать каждый кадр.
        # SRCALPHA + цвет (255, 215, 0, 80) — Pygbag-safe:
        # альфа задаётся через цвет, а не через Surface.set_alpha().
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255, 215, 0, 80), (30, 30), 30)

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, dt):
        # Собранный ключ не анимируется — экономим вычисления.
        if self.collected:
            return

        # bob крутится в цикле, чтобы float не терял точность
        # при очень долгой игре (как в bat.py).
        self.bob = (self.bob + dt * 0.005) % (2 * math.pi * 1000)

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        if self.collected:
            return

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 4)

        GOLD = (255, 215, 0)

        # --- Свечение (готовый Surface) ---
        # glow 60×60, центр в (30, 30). Смещение (-18, -18) даёт
        # центр свечения на (sx + 12, sy + 12) — примерно центр ключа.
        screen.blit(self.glow, (sx - 18, sy - 18))

        # --- Кольцо ключа (головка) ---
        pygame.draw.circle(screen, GOLD, (sx + 8, sy + 8), 5, 2)

        # --- Стержень (диагональ от кольца вниз-вправо) ---
        pygame.draw.line(screen, GOLD,
                         (sx + 11, sy + 11), (sx + 18, sy + 18), 3)

        # --- Зубчики (два маленьких отрезка от стержня) ---
        pygame.draw.line(screen, GOLD,
                         (sx + 15, sy + 15), (sx + 18, sy + 12), 2)
        pygame.draw.line(screen, GOLD,
                         (sx + 18, sy + 18), (sx + 20, sy + 16), 2)