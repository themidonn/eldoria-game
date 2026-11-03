import pygame
from settings import *

class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w = self.h = PLAYER_SIZE
        self.hp = self.max_hp = PLAYER_MAX_HP
        self.direction = (0, 1)
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.invuln = 0
        self.crystals = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, keys, dt, world):
        if self.attack_timer > 0:   self.attack_timer -= dt
        if self.attack_cooldown > 0: self.attack_cooldown -= dt
        if self.invuln > 0:         self.invuln -= dt

        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1

        if dx or dy:
            length = (dx*dx + dy*dy) ** 0.5
            dx, dy = dx / length, dy / length
            self.direction = (1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) \
                             else (0, 1 if dy > 0 else -1)
            speed = PLAYER_SPEED * (dt / 16.67)
            if world.is_walkable_rect(self.x + dx*speed, self.y, self.w, self.h):
                self.x += dx * speed
            if world.is_walkable_rect(self.x, self.y + dy*speed, self.w, self.h):
                self.y += dy * speed

    def try_attack(self):
        if self.attack_cooldown <= 0:
            self.attack_timer = PLAYER_ATTACK_DURATION
            self.attack_cooldown = PLAYER_ATTACK_COOLDOWN

    def get_attack_hitbox(self):
        if self.attack_timer <= 0:
            return None
        dx, dy = self.direction
        cx = self.x + self.w/2 + dx * (PLAYER_ATTACK_RANGE/2 + self.w/2)
        cy = self.y + self.h/2 + dy * (PLAYER_ATTACK_RANGE/2 + self.h/2)
        r = PLAYER_ATTACK_RANGE
        return pygame.Rect(int(cx - r/2), int(cy - r/2), int(r), int(r))

    def take_damage(self, dmg=1):
        if self.invuln > 0:
            return False
        self.hp -= dmg
        self.invuln = PLAYER_INVULN_TIME
        return True

    def draw(self, screen, cam):
        if self.invuln > 0 and (pygame.time.get_ticks() // 80) % 2 == 0:
            return
        sx, sy = self.x - cam.x, self.y - cam.y
        c = (int(sx + self.w/2), int(sy + self.h/2))
        pygame.draw.circle(screen, COLOR_PLAYER, c, self.w // 2)
        pygame.draw.circle(screen, (20, 20, 30), c, self.w // 2, 2)
        dx, dy = self.direction
        ex, ey = c[0] + dx*6, c[1] + dy*6
        pygame.draw.circle(screen, (255, 255, 255), (int(ex), int(ey)), 4)
        pygame.draw.circle(screen, (0, 0, 0), (int(ex + dx*2), int(ey + dy*2)), 2)
        if self.attack_timer > 0:
            hb = self.get_attack_hitbox()
            if hb:
                sr = hb.move(int(-cam.x), int(-cam.y))
                pygame.draw.rect(screen, COLOR_SWORD, sr, border_radius=6)
                pygame.draw.rect(screen, (150, 150, 160), sr, 2, border_radius=6)