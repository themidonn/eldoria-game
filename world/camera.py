from settings import WIDTH, HEIGHT, TILE

class Camera:
    def __init__(self):
        self.x = self.y = 0

    def follow(self, tx, ty, world_w, world_h):
        # Используем // вместо /, чтобы избежать создания float
        self.x = int(tx - WIDTH // 2)
        self.y = int(ty - HEIGHT // 2)
        self.x = max(0, min(self.x, world_w * TILE - WIDTH))
        self.y = max(0, min(self.y, world_h * TILE - HEIGHT))