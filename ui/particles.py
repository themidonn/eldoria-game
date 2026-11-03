import pygame, random
from settings import *

class Particle:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-6, -1) # Разлетаются вверх
        self.life = random.randint(300, 600) # Время жизни (мс)
        self.color = color
        self.size = random.randint(2, 4)

    def update(self, dt):
        self.x += self.vx * (dt / 16.67)
        self.y += self.vy * (dt / 16.67)
        self.vy += 0.3 * (dt / 16.67) # Гравитация
        self.life -= dt
        return self.life > 0

    def draw(self, screen, cam):
        if self.life <= 0: return
        # ОПТИМИЗАЦИЯ: Рисуем обычный квадрат, чтобы не создавать Surface каждый кадр!
        rect = (int(self.x - cam.x), int(self.y - cam.y), self.size, self.size)
        pygame.draw.rect(screen, self.color, rect)

class ParticleManager:
    def __init__(self):
        self.particles = []

    def spawn_burst(self, x, y, color, count=12):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, screen, cam):
        for p in self.particles:
            p.draw(screen, cam)