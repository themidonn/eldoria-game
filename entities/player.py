"""
entities/player.py — Игрок: движение, атака, здоровье, инвентарь.

Ключевые механики:
- Движение с нормализацией диагонали (не быстрее по диагонали).
- Направление взгляда: 4 стороны (не 8) — так проще для удара мечом.
- Атака: короткий таймер + кулдаун.
- Неуязвимость после урона + мигание спрайта.
- Замедление в болоте (тайл SWAMP под центром игрока).

Используется в game.py:
  - _reset() — создаёт экземпляр
  - update() — движение, таймеры
  - try_attack() — по Space / J
  - get_attack_hitbox() — проверка попадания по врагам
  - take_damage() — при контакте с врагом / снарядом
  - upgrade_weapon() — после квеста Жителя
  - draw() — отрисовка
  - save_progress() / load_progress() — сохраняет hp, max_hp, damage,
    weapon_upgraded, crystals

Поиск по файлу: Ctrl+F "region"
"""

import pygame
from settings import *


class Player:

    # region ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    BODY_COLOR = COLOR_PLAYER           # тело
    OUTLINE    = (20, 20, 30)           # обводка
    EYE_WHITE  = (255, 255, 255)        # белок глаза
    EYE_BLACK  = (0, 0, 0)              # зрачок
    SWORD_EDGE = (150, 150, 160)        # обводка меча
    # endregion

    # region КОНСТРУКТОР
    def __init__(self, x, y):
        # --- Позиция и размеры ---
        self.x, self.y = float(x), float(y)
        self.w = self.h = PLAYER_SIZE

        # --- Здоровье ---
        self.hp = self.max_hp = PLAYER_MAX_HP

        # --- Направление взгляда: (dx, dy) ∈ {(±1, 0), (0, ±1)} ---
        # Стартовое — вниз (игрок появляется лицом к камере).
        self.direction = (0, 1)

        # --- Таймеры (мс) ---
        self.attack_timer = 0           # сколько ещё длится удар
        self.attack_cooldown = 0        # сколько ещё нельзя бить
        self.invuln = 0                 # сколько ещё неуязвим после урона

        # --- Прогресс ---
        self.crystals = 0               # сколько кристаллов собрано (0..3)
        self.damage = PLAYER_ATTACK_DAMAGE
        self.weapon_upgraded = False    # True после квеста Жителя
    # endregion

    # region СВОЙСТВА
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    # endregion

    # region ЛОГИКА

    # region update (движение, таймеры, болото)
    def update(self, keys, dt, world):
        # --- Таймеры ---
        # max(0, ...) — защита от отрицательных значений при большом dt.
        # Проверки > 0 / <= 0 работают и с отрицательными, но так
        # значения читаемее при отладке (как в bat.py / boss.py / enemy.py).
        if self.attack_timer > 0:
            self.attack_timer = max(0, self.attack_timer - dt)
        if self.attack_cooldown > 0:
            self.attack_cooldown = max(0, self.attack_cooldown - dt)
        if self.invuln > 0:
            self.invuln = max(0, self.invuln - dt)

        # --- Ввод (WASD + стрелки) ---
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1

        if not (dx or dy):
            return

        # --- Нормализация (диагональ не быстрее прямой) ---
        length = (dx * dx + dy * dy) ** 0.5
        dx, dy = dx / length, dy / length

        # --- Направление взгляда: 4 стороны ---
        if abs(dx) > abs(dy):
            self.direction = (1 if dx > 0 else -1, 0)
        else:
            self.direction = (0, 1 if dy > 0 else -1)

        # --- Скорость с учётом болота ---
        # dt в миллисекундах, делим на 16.67 (кадр при 60 FPS) —
        # скорость одинаковая при любом FPS.
        speed = PLAYER_SPEED * (dt / 16.67)

        # Проверяем тайл под ЦЕНТРОМ игрока: если болото — замедляем.
        # Центр, а не угол — так игрок «проваливается» в болото,
        # когда входит в него больше, чем наполовину. Это ощущается
        # естественнее, чем «замедление при касании края».
        # В подземелье SWAMP нет, поэтому проверка безопасна
        # для обоих уровней (Dungeon.tiles тоже есть).
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        tx, ty = int(cx // TILE), int(cy // TILE)
        if (0 <= ty < world.h and 0 <= tx < world.w
                and world.tiles[ty][tx] == SWAMP):
            speed *= SWAMP_SLOWDOWN_FACTOR

        # --- Движение с коллизиями по осям ---
        # X и Y проверяем отдельно — иначе игрок застревает в углах.
        if world.is_walkable_rect(self.x + dx * speed, self.y, self.w, self.h):
            self.x += dx * speed
        if world.is_walkable_rect(self.x, self.y + dy * speed, self.w, self.h):
            self.y += dy * speed
    # endregion

    # region try_attack
    def try_attack(self):
        """
        Запускает атаку, если кулдаун истёк.

        Не срабатывает, если игрок уже мёртв (hp <= 0): в game.py
        state переключается в 'lose' в том же кадре, но защита
        от случайного вызова не помешает.
        """
        if self.hp <= 0:
            return
        if self.attack_cooldown <= 0:
            self.attack_timer = PLAYER_ATTACK_DURATION
            self.attack_cooldown = PLAYER_ATTACK_COOLDOWN
    # endregion

    # region upgrade_weapon
    def upgrade_weapon(self):
        """
        Прокачка меча: урон 1 → 2, золотой цвет в draw().

        Идемпотентно по задумке: вызывается один раз после квеста
        Жителя (см. game.py, _try_talk_to_npc → VILLAGER_THANKS).
        Повторный вызов не сделает урон 3 — это сознательно.
        """
        self.damage = 2
        self.weapon_upgraded = True
    # endregion

    # region get_attack_hitbox
    def get_attack_hitbox(self):
        """
        Возвращает pygame.Rect зоны удара или None, если атака не идёт.

        Зона удара — квадрат PLAYER_ATTACK_RANGE × PLAYER_ATTACK_RANGE,
        центр которого смещён от центра игрока в сторону взгляда
        на PLAYER_ATTACK_RANGE/2 + PLAYER_SIZE/2.
        """
        if self.attack_timer <= 0:
            return None

        dx, dy = self.direction
        cx = self.x + self.w / 2 + dx * (PLAYER_ATTACK_RANGE / 2 + self.w / 2)
        cy = self.y + self.h / 2 + dy * (PLAYER_ATTACK_RANGE / 2 + self.h / 2)
        r = PLAYER_ATTACK_RANGE
        return pygame.Rect(int(cx - r / 2), int(cy - r / 2), int(r), int(r))
    # endregion

    # region take_damage
    def take_damage(self, dmg=1):
        """
        Возвращает True, если урон прошёл (не в invuln).

        Защита от dmg <= 0: нулевой/отрицательный урон не должен
        лечить игрока и не должен давать бесплатный invuln.
        """
        if dmg <= 0:
            return False
        if self.invuln > 0:
            return False

        # Клэмп в 0: без него HP мог уйти в минус от повторного удара
        # до того, как game.py успеет переключить state = 'lose'.
        self.hp = max(0, self.hp - dmg)
        self.invuln = PLAYER_INVULN_TIME
        return True
    # endregion

    # endregion (ЛОГИКА)

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        # --- Мигание при неуязвимости ---
        # Синхронизировано с началом invuln (а не с глобальным временем) —
        # первый кадр после урона игрок видим, чтобы понять, что попал.
        # 80 мс — половина периода мигания (160 мс).
        if self.invuln > 0 and (self.invuln // 80) % 2 == 1:
            return

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)
        cx = sx + self.w // 2
        cy = sy + self.h // 2

        # --- Тело (круг + обводка) ---
        pygame.draw.circle(screen, self.BODY_COLOR, (cx, cy), self.w // 2)
        pygame.draw.circle(screen, self.OUTLINE, (cx, cy), self.w // 2, 2)

        # --- Глаз (смещён в сторону взгляда) ---
        # Смещение 6 px от центра — примерно треть радиуса (при w = 20..24).
        # Зрачок смещён ещё на 2 px в ту же сторону — «смотрит» вперёд.
        dx, dy = self.direction
        ex = cx + dx * 6
        ey = cy + dy * 6
        pygame.draw.circle(screen, self.EYE_WHITE, (ex, ey), 4)
        pygame.draw.circle(screen, self.EYE_BLACK, (ex + dx * 2, ey + dy * 2), 2)

        # --- Меч (только во время атаки) ---
        if self.attack_timer > 0:
            hb = self.get_attack_hitbox()
            if hb:
                # hb в мировых координатах — сдвигаем на камеру,
                # чтобы получить экранные.
                sr = hb.move(int(-cam.x), int(-cam.y))
                sword_color = (COLOR_SWORD_UPGRADED
                               if self.weapon_upgraded else COLOR_SWORD)
                pygame.draw.rect(screen, sword_color, sr, border_radius=6)
                pygame.draw.rect(screen, self.SWORD_EDGE, sr, 2, border_radius=6)
    # endregion