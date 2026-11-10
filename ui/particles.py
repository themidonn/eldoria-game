"""
ui/particles.py — Система частиц.

Particle        — одна частица (квадратик, летит вверх, падает под гравитацией).
ParticleManager — пул частиц: спавн, обновление, отрисовка.

Параметры эффекта (скорость, время жизни, размер) — в константах
модуля, чтобы легко настраивать «взрыв» в одном месте.

Используется в game.py:
  - _reset() — создаёт экземпляр (в _reset и при смене уровня)
  - _update_level_1() / _update_level_2() — spawn_burst при смертях
    (слизни, мыши, скелеты, боссы)
  - _try_open_chest() — spawn_burst при открытии сундука
  - _update_common() — update (фильтрация мёртвых)
  - _draw_ui() — draw

ВАЖНО: draw() рисует частицы через pygame.draw.rect, а не через
Surface — это критично для Pygbag: создание Surface на каждую
частицу каждый кадр приводит к утечкам памяти в WASM.

Поиск по файлу: Ctrl+F "region"
"""

import random
import pygame


# region КОНСТАНТЫ (настройки эффекта)
# Все диапазоны — рандом внутри [min, max] на момент спавна.
SPEED_X_RANGE = (-4, 4)        # px/кадр — горизонтальная скорость
SPEED_Y_RANGE = (-6, -1)       # px/кадр — вертикальная (отрицательная = вверх)
LIFE_RANGE    = (300, 600)     # мс — время жизни частицы
SIZE_RANGE    = (2, 4)         # px — сторона квадратика
GRAVITY       = 0.3            # px/кадр² — ускорение вниз
DEFAULT_COUNT = 12             # частиц в одном взрыве по умолчанию

# Максимум частиц в пуле. При превышении дропаются самые старые
# (они всё равно умрут через несколько кадров), новые остаются.
# Защита от просадки FPS в WASM при массовых взрывах.
MAX_PARTICLES = 200
# endregion


# region КЛАСС: Particle
class Particle:
    """Одна частица: квадратик, летит вверх, падает под гравитацией."""

    # region КОНСТРУКТОР
    def __init__(self, x, y, color):
        # --- Позиция (float — для плавного движения) ---
        self.x = float(x)
        self.y = float(y)

        # --- Скорость (рандом в диапазонах из констант) ---
        self.vx = random.uniform(*SPEED_X_RANGE)
        self.vy = random.uniform(*SPEED_Y_RANGE)   # отрицательная = вверх

        # --- Жизнь и внешний вид ---
        self.life = random.randint(*LIFE_RANGE)
        self.color = color
        self.size = random.randint(*SIZE_RANGE)
    # endregion

    # region ЛОГИКА
    def update(self, dt):
        """
        Обновляет позицию и время жизни.

        Возвращает True, если частица жива (используется в
        ParticleManager.update для фильтрации мёртвых).
        """
        # k — множитель к 1 кадру при 60 FPS. Все изменения
        # умножаются на k — движение frame-independent.
        k = dt / 16.67

        # --- Движение (по текущей скорости) ---
        self.x += self.vx * k
        self.y += self.vy * k

        # --- Гравитация (увеличивает vy на следующий кадр) ---
        # Порядок важен: сначала движение, потом гравитация —
        # explicit Euler, для частиц достаточно.
        self.vy += GRAVITY * k

        # --- Время жизни (dt в мс, life в мс) ---
        self.life -= dt
        return self.life > 0
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        # Мёртвые частицы отфильтрованы в ParticleManager.update —
        # здесь проверка не нужна. (Если draw когда-нибудь вызовут
        # напрямую, верните `if self.life <= 0: return` в начало.)
        #
        # Квадрат вместо Surface — критично для Pygbag (без утечек памяти).
        # int() для совместимости с WebAssembly (Pygbag не принимает float).
        pygame.draw.rect(screen, self.color, (
            int(self.x - cam.x), int(self.y - cam.y),
            self.size, self.size,
        ))
    # endregion
# endregion


# region КЛАСС: ParticleManager
class ParticleManager:
    """Пул частиц: спавн, обновление (с удалением мёртвых), отрисовка."""

    # region КОНСТРУКТОР
    def __init__(self):
        self.particles = []
    # endregion

    # region ЛОГИКА
    def spawn_burst(self, x, y, color, count=DEFAULT_COUNT):
        """
        Создаёт взрыв из `count` частиц в точке (x, y).

        count <= 0 — защита от бессмысленных вызовов.
        """
        if count <= 0:
            return

        for _ in range(count):
            self.particles.append(Particle(x, y, color))

        # --- Кэп: дропаем самые старые ---
        # Список упорядочен по времени создания, старые — в начале.
        # del [:excess] работает корректно при любом MAX_PARTICLES >= 0
        # (в отличие от срезов [-MAX_PARTICLES:], которые ломаются
        # при MAX_PARTICLES = 0).
        excess = len(self.particles) - MAX_PARTICLES
        if excess > 0:
            del self.particles[:excess]

    def update(self, dt):
        """
        Обновляет все частицы и удаляет мёртвые.

        p.update(dt) возвращает bool (жива ли), его результат
        используется в фильтре list comprehension.
        """
        self.particles = [p for p in self.particles if p.update(dt)]
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        """Рисует все живые частицы."""
        for p in self.particles:
            p.draw(screen, cam)
    # endregion
# endregion