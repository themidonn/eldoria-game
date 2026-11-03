import random
from settings import WIDTH, HEIGHT, TILE

class Camera:
    def __init__(self):
        self.x = self.y = 0
        self.shake_amount = 0

    def add_shake(self, amount):
        self.shake_amount = max(self.shake_amount, amount)

    def follow(self, tx, ty, world_w, world_h):
        self.x = int(tx - WIDTH // 2)
        self.y = int(ty - HEIGHT // 2)

        # 1. Сначала применяем тряску (до ограничений)
        if self.shake_amount > 0:
            self.x += random.randint(-self.shake_amount, self.shake_amount)
            self.y += random.randint(-self.shake_amount, self.shake_amount)
            self.shake_amount -= 1  # Затухание

        # 2. Потом ограничиваем камеру краями карты
        self.x = max(0, min(self.x, world_w * TILE - WIDTH))
        self.y = max(0, min(self.y, world_h * TILE - HEIGHT))