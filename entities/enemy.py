import pygame
from settings import *

class Slime:
    def __init__(self, x, y, hp=2):
        self.x, self.y = float(x), float(y)
        self.w = self.h = 28
        self.hp = self.max_hp = hp
        self.speed = 1.3
        self.hit_flash = 0
        self.knockback = [0.0, 0.0]
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, player, world, dt):
        if self.dead:
            return
        if self.hit_flash > 0:
            self.hit_flash -= dt

        if self.knockback[0] or self.knockback[1]:
            k = dt / 16.67
            nx = self.x + self.knockback[0] * k
            ny = self.y + self.knockback[1] * k
            if world.is_walkable_rect(nx, self.y, self.w, self.h):
                self.x = nx
            if world.is_walkable_rect(self.x, ny, self.w, self.h):
                self.y = ny
            self.knockback[0] *= 0.85
            self.knockback[1] *= 0.85
            if abs(self.knockback[0]) < 0.1: self.knockback[0] = 0
            if abs(self.knockback[1]) < 0.1: self.knockback[1] = 0

        dx, dy = player.x - self.x, player.y - self.y
        dist = (dx*dx + dy*dy) ** 0.5
        if 20 < dist < 250:
            dx, dy = dx/dist, dy/dist
            s = self.speed * (dt / 16.67)
            if world.is_walkable_rect(self.x + dx*s, self.y, self.w, self.h):
                self.x += dx*s
            if world.is_walkable_rect(self.x, self.y + dy*s, self.w, self.h):
                self.y += dy*s

    def take_damage(self, dmg, fx, fy):
        self.hp -= dmg
        self.hit_flash = 200
        dx, dy = self.x - fx, self.y - fy
        d = (dx*dx + dy*dy) ** 0.5 or 1
        self.knockback = [dx/d * 8, dy/d * 8]
        if self.hp <= 0:
            self.dead = True

    def draw(self, screen, cam):
        if self.dead:
            return
        sx, sy = int(self.x - cam.x), int(self.y - cam.y)
        color = (255, 100, 100) if self.hit_flash > 0 else COLOR_SLIME
        pygame.draw.ellipse(screen, color, (sx, sy+4, self.w, self.h-4))
        pygame.draw.ellipse(screen, COLOR_SLIME_D, (sx, sy+4, self.w, self.h-4), 2)
        pygame.draw.circle(screen, (255, 255, 255), (sx+8, sy+12), 3)
        pygame.draw.circle(screen, (255, 255, 255), (sx+self.w-8, sy+12), 3)
        pygame.draw.circle(screen, (0, 0, 0), (sx+8, sy+12), 1)
        pygame.draw.circle(screen, (0, 0, 0), (sx+self.w-8, sy+12), 1)