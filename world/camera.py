"""
world/camera.py — Камера, следящая за игроком.

Камера центрируется на целевой точке (обычно — центр игрока),
применяет опциональную тряску и затем ограничивает себя
краями карты, чтобы не показывать пустоту за границей мира.

Используется в game.py:
  - _reset() — создаёт экземпляр
  - enter_dungeon() / exit_dungeon() — новый экземпляр (сброс позиции)
  - _update_level_1() / _update_level_2() — add_shake при уроне/смертях
  - _update_common() — follow (каждый кадр)

Поиск по файлу: Ctrl+F "region"
"""

import random
from settings import WIDTH, HEIGHT, TILE


# region КЛАСС: Camera
class Camera:

    # region КОНСТРУКТОР
    def __init__(self):
        self.x = 0
        self.y = 0
        # float — потому что после `-= dt / 16.67` значение дробное.
        # random.randint требует int, поэтому int() — на месте применения.
        self.shake_amount = 0.0
    # endregion

    # region ПУБЛИЧНЫЕ МЕТОДЫ

    # region add_shake
    def add_shake(self, amount):
        """
        Добавляет тряску. Если тряска уже идёт — берём максимум,
        а не сумму: два одновременных события (урон + удар)
        не должны давать двойной эффект.
        """
        self.shake_amount = max(self.shake_amount, float(amount))
    # endregion

    # region follow
    def follow(self, tx, ty, world_w, world_h, dt=None):
        """
        Центрируется на точке (tx, ty), применяет тряску и кламп.

        Параметры:
          tx, ty           — координаты цели (обычно центр игрока)
          world_w, world_h — размеры мира в тайлах
          dt               — мс с прошлого кадра (необязательно).
                             Если передан — затухание тряски
                             frame-independent (как в остальном
                             проекте: bat.py, boss.py, player.py).
                             Если None — старое поведение (затухание
                             на 1 px за кадр, зависит от FPS).

        Обратная совместимость: game.py вызывает follow(x, y, w, h)
        без dt — работает как раньше.
        """
        # --- Позиция относительно центра экрана ---
        # WIDTH // 2 — int, int(tx - ...) отрезает дробную часть:
        # камера не должна «дрожать» на субпикселях при движении игрока.
        self.x = int(tx - WIDTH // 2)
        self.y = int(ty - HEIGHT // 2)

        # --- Тряска (ДО ограничений!) ---
        # Порядок важен: если сначала зажать камеру, а потом тряхнуть —
        # у края карты камера покажет пустоту за границей мира.
        if self.shake_amount > 0:
            # int() — потому что shake_amount float после dt-ветки,
            # а random.randint принимает только int.
            # При shake_amount < 1 — int() даёт 0, тряска визуально
            # не заметна (субпиксельный сдвиг), это нормально.
            shake_px = int(self.shake_amount)
            if shake_px > 0:
                self.x += random.randint(-shake_px, shake_px)
                self.y += random.randint(-shake_px, shake_px)

            # --- Затухание ---
            # dt=None — 1 px за кадр (старое поведение, FPS-зависимо).
            # dt передан — масштабируем к 1 кадру при 60 FPS:
            # при 30 FPS затухает в 2 раза больше за кадр,
            # при 120 FPS — в 2 раза меньше. По времени — одинаково.
            # Раньше было `max(1, int(dt / 16.67))`, из-за чего
            # на 120 FPS затухание шло ровно в 2 раза быстрее.
            if dt is None:
                self.shake_amount -= 1
            else:
                self.shake_amount -= dt / 16.67

            # Защита от отрицательных значений.
            self.shake_amount = max(0.0, self.shake_amount)

        # --- Ограничение краями карты ---
        # Если мир меньше экрана (world_w * TILE < WIDTH), выражение
        # max(0, min(self.x, отрицательное)) даст 0 — камера застрянет
        # в левом верхнем углу. Это осознанно: лучше показать угол
        # карты, чем пустоту сбоку. Для реальных карт (180×130 тайлов
        # при WIDTH=960, HEIGHT=640) это условие не выполняется.
        self.x = max(0, min(self.x, world_w * TILE - WIDTH))
        self.y = max(0, min(self.y, world_h * TILE - HEIGHT))
    # endregion

    # endregion (ПУБЛИЧНЫЕ МЕТОДЫ)
# endregion (Camera)