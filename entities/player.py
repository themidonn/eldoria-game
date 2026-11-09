"""
entities/player.py — Игрок: движение, атака, здоровье, инвентарь.

Ключевые механики:
- Движение с нормализацией диагонали (не быстрее по диагонали).
- Направление взгляда: 4 стороны (не 8) — так проще для удара мечом.
- Атака: короткий таймер + кулдаун.
- Неуязвимость после урона + мигание спрайта.
"""

import pygame
from settings import *


class Player:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w = self.h = PLAYER_SIZE
        self.hp = self.max_hp = PLAYER_MAX_HP

        # Направление взгляда: (dx, dy) ∈ {(±1, 0), (0, ±1)}
        self.direction = (0, 1)

        # Таймеры (мс)
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.invuln = 0

        # Прогресс
        self.crystals = 0
        self.damage = PLAYER_ATTACK_DAMAGE
        self.weapon_upgraded = False

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, keys, dt, world):
        # --- Таймеры ---
        if self.attack_timer > 0:
            self.attack_timer -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.invuln > 0:
            self.invuln -= dt

        # --- Ввод ---
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1

        if not (dx or dy):
            return

        # --- Нормализация (диагональ не быстрее прямой) ---
        length = (dx * dx + dy * dy) ** 0.5
        dx, dy = dx / length, dy / length

        # --- Направление взгляда: 4 стороны ---
        # По большей оси; при равенстве — вертикаль
        if abs(dx) > abs(dy):
            self.direction = (1 if dx > 0 else -1, 0)
        else:
            self.direction = (0, 1 if dy > 0 else -1)

        # --- Движение с коллизиями по осям ---
        # X и Y проверяем отдельно — иначе игрок застревает в углах
        speed = PLAYER_SPEED * (dt / 16.67)
        if world.is_walkable_rect(self.x + dx * speed, self.y, self.w, self.h):
            self.x += dx * speed
        if world.is_walkable_rect(self.x, self.y + dy * speed, self.w, self.h):
            self.y += dy * speed

    def try_attack(self):
        """Запускает атаку, если кулдаун истёк."""
        if self.attack_cooldown <= 0:
            self.attack_timer = PLAYER_ATTACK_DURATION
            self.attack_cooldown = PLAYER_ATTACK_COOLDOWN

    def upgrade_weapon(self):
        """Прокачка меча: урон 1 → 2, золотой цвет в draw()."""
        self.damage = 2
        self.weapon_upgraded = True

    def get_attack_hitbox(self):
        """Возвращает pygame.Rect зоны удара или None, если атака не идёт."""
        if self.attack_timer <= 0:
            return None

        dx, dy = self.direction
        cx = self.x + self.w / 2 + dx * (PLAYER_ATTACK_RANGE / 2 + self.w / 2)
        cy = self.y + self.h / 2 + dy * (PLAYER_ATTACK_RANGE / 2 + self.h / 2)
        r = PLAYER_ATTACK_RANGE
        return pygame.Rect(int(cx - r / 2), int(cy - r / 2), int(r), int(r))

    def take_damage(self, dmg=1):
        """Возвращает True, если урон прошёл (не в invuln)."""
        if self.invuln > 0:
            return False
        # Клэмп в 0: без него HP мог уйти в минус от повторного удара
        # до того, как game.py успеет переключить state = 'lose'.
        self.hp = max(0, self.hp - dmg)
        self.invuln = PLAYER_INVULN_TIME
        return True

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        # Мигание при неуязвимости синхронизировано с началом invuln
        # (а не с глобальным временем) — первый кадр после урона игрок видим.
        if self.invuln > 0 and (self.invuln // 80) % 2 == 1:
            return

        # --- Палитра ---
        BODY_COLOR = COLOR_PLAYER
        OUTLINE    = (20, 20, 30)
        EYE_WHITE  = (255, 255, 255)
        EYE_BLACK  = (0, 0, 0)
        SWORD_EDGE = (150, 150, 160)

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)
        cx = sx + self.w // 2
        cy = sy + self.h // 2

        # --- Тело (круг + обводка) ---
        pygame.draw.circle(screen, BODY_COLOR, (cx, cy), self.w // 2)
        pygame.draw.circle(screen, OUTLINE, (cx, cy), self.w // 2, 2)

        # --- Глаз (смещён в сторону взгляда) ---
        dx, dy = self.direction
        ex = cx + dx * 6
        ey = cy + dy * 6
        pygame.draw.circle(screen, EYE_WHITE, (ex, ey), 4)
        pygame.draw.circle(screen, EYE_BLACK, (ex + dx * 2, ey + dy * 2), 2)

        # --- Меч (только во время атаки) ---
        if self.attack_timer > 0:
            hb = self.get_attack_hitbox()
            if hb:
                sr = hb.move(int(-cam.x), int(-cam.y))
                sword_color = COLOR_SWORD_UPGRADED if self.weapon_upgraded else COLOR_SWORD
                pygame.draw.rect(screen, sword_color, sr, border_radius=6)
                pygame.draw.rect(screen, SWORD_EDGE, sr, 2, border_radius=6)