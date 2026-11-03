import pygame
from settings import *

class Boss:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w, self.h = 60, 70
        self.hp = self.max_hp = 20
        self.speed = 1.0
        self.hit_flash = 0
        self.phase = 'idle'
        self.charge_timer = 3.0
        self.charge_dir = (0, 0)
        self.dead = True  # активируется после сбора кристаллов

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, player, world, dt):
        if self.dead:
            return
        if self.hit_flash > 0:
            self.hit_flash -= dt
        dt_s = dt / 1000.0
        if self.charge_timer > 0:
            self.charge_timer -= dt_s

        dx, dy = player.x - self.x, player.y - self.y
        dist = (dx*dx + dy*dy) ** 0.5 or 1

        if self.phase == 'charge':
            step = 8 * min(dt / 16.67, 3.0)
            nx = self.x + self.charge_dir[0] * step
            ny = self.y + self.charge_dir[1] * step
            moved = False
            if world.is_walkable_rect(nx, self.y, self.w, self.h):
                self.x = nx; moved = True
            if world.is_walkable_rect(self.x, ny, self.w, self.h):
                self.y = ny; moved = True
            if not moved:
                self.phase = 'idle'
        elif 40 < dist < 400:
            dx, dy = dx/dist, dy/dist
            s = self.speed * (dt/16.67)
            if world.is_walkable_rect(self.x + dx*s, self.y, self.w, self.h):
                self.x += dx*s
            if world.is_walkable_rect(self.x, self.y + dy*s, self.w, self.h):
                self.y += dy*s
            if self.charge_timer <= 0:
                self.phase = 'charge'
                self.charge_dir = (dx, dy)
                self.charge_timer = 3.0

    def take_damage(self, dmg, fx, fy):
        self.hp -= dmg
        self.hit_flash = 200
        if self.hp <= 0:
            self.dead = True

    def draw(self, screen, cam):
        if self.dead:
            return
        sx, sy = int(self.x - cam.x), int(self.y - cam.y)
        color = (255, 100, 100) if self.hit_flash > 0 else COLOR_BOSS
        pygame.draw.ellipse(screen, color, (sx, sy+10, self.w, self.h-10))
        pygame.draw.ellipse(screen, (50, 10, 20), (sx, sy+10, self.w, self.h-10), 3)
        pygame.draw.circle(screen, (255, 240, 100), (sx+18, sy+30), 5)
        pygame.draw.circle(screen, (255, 240, 100), (sx+self.w-18, sy+30), 5)
        pygame.draw.circle(screen, (0, 0, 0), (sx+18, sy+30), 2)
        pygame.draw.circle(screen, (0, 0, 0), (sx+self.w-18, sy+30), 2)

        # HP-бар — только когда босс на экране
        if -self.w < sx < WIDTH and -self.h < sy < HEIGHT:
            bw = 200
            bx = WIDTH // 2 - bw // 2
            by = HEIGHT - 50
            pygame.draw.rect(screen, (50, 20, 30), (bx, by, bw, 18), border_radius=4)
            fill = int(bw * self.hp / self.max_hp)
            pygame.draw.rect(screen, (200, 40, 60), (bx, by, fill, 18), border_radius=4)
            pygame.draw.rect(screen, (240, 200, 100), (bx, by, bw, 18), 2, border_radius=4)