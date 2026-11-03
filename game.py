import pygame, random, asyncio
from settings import *
from data.story import *
from world.map import World
from world.camera import Camera
from entities.player import Player
from entities.enemy import Slime
from entities.npc import NPC
from entities.pickup import Crystal
from entities.potion import Potion
from entities.boss import Boss
from ui.hud import HUD
from ui.dialog import Dialog
from ui.floating_text import FloatingText

class Game:
    TOTAL_CRYSTALS = 3

    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Хроники Эльдории")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 'title'
        # ── шрифты (кэш) ──
        self.font_title_big = pygame.font.SysFont('arial', 56, bold=True)
        self.font_title_small = pygame.font.SysFont('arial', 24)
        self.font_win_big = pygame.font.SysFont('arial', 64, bold=True)
        self.font_win_small = pygame.font.SysFont('arial', 26)
        self.font_hint_banner = pygame.font.SysFont('arial', 18, bold=True)  # баннер «Замок открыт»
        # ── оверлеи (кэш) ──
        self.overlay_black = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_black.fill((0, 0, 0, 180))
        self.overlay_red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_red.fill((40, 0, 0, 180))
        self._reset()  # ← последним

    def _reset(self):
        self.world = World()
        self.player = Player(30*TILE + 7, 38*TILE + 7)
        self.camera = Camera()
        self.dialog = Dialog()
        self.hud = HUD()
        self.enemies, self.npcs, self.crystals = [], [], []
        self.potions = []
        self.floating_texts = []
        self.boss = None
        self.boss_spawned = False
        self._spawn()
        self.win_delay = 0  # таймер задержки перед экраном победы

    def _spawn(self):
        # Старейшина
        self.npcs.append(NPC(28*TILE, 38*TILE, "Старейшина"))

        # Кристалл 1 — лес (восток)
        self.crystals.append(Crystal(50 * TILE, 20 * TILE, "Кристалл Леса"))
        for dx in (-3, 0, 3):
            tx, ty = 50 + dx, 22
            if self.world.tiles[ty][tx] == GRASS:
                self.enemies.append(Slime(tx * TILE, ty * TILE))
        # Кристалл 2 — озеро (юг)
        self.crystals.append(Crystal(43*TILE, 35*TILE, "Кристалл Воды"))
        for dx in (-2, 2):
            for dy in (-2, 2):
                self.enemies.append(Slime((43+dx)*TILE, (35+dy)*TILE))
        # Кристалл 3 — руины (запад)
        self.crystals.append(Crystal(8 * TILE, 20 * TILE, "Кристалл Руин"))
        for dx in (-3, 0, 3):
            tx, ty = 8 + dx, 22
            if self.world.tiles[ty][tx] == GRASS:
                self.enemies.append(Slime(tx * TILE, ty * TILE, hp=3))

        # Босс — ждёт за воротами
        self.boss = Boss(7*TILE, 5*TILE)

        # Случайные слизни
        rng = random.Random(99)
        for _ in range(15):
            tx, ty = rng.randint(5, self.world.w-5), rng.randint(5, self.world.h-5)
            if self.world.tiles[ty][tx] == GRASS and abs(tx-30) + abs(ty-38) > 10:
                self.enemies.append(Slime(tx*TILE, ty*TILE))

        # Зелья лечения (только на траве)
        potion_positions = [
            (31, 36),   # рядом со стартом — обучающее
            (49, 22),   # в лесу, у кристалла 1
            (9, 22),    # в руинах, у кристалла 3
            (7, 11),    # перед воротами замка — тактика перед боссом
            (44, 34),   # у озера, у кристалла 2
        ]
        for tx, ty in potion_positions:
            if self.world.tiles[ty][tx] == GRASS:
                self.potions.append(Potion(tx * TILE, ty * TILE))

    # ---------- события ----------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if self.state == 'title':
                    self.state = 'playing'; continue
                if self.state in ('win', 'lose'):
                    if e.key == pygame.K_r:
                        self._reset(); self.state = 'playing'
                    continue
                if self.dialog.active:
                    if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.dialog.next_page()
                    elif e.key == pygame.K_ESCAPE:
                        self.dialog.active = False
                    continue
                if e.key in (pygame.K_SPACE, pygame.K_j):
                    self.player.try_attack()
                elif e.key == pygame.K_e:
                    self._interact()
                elif e.key == pygame.K_ESCAPE:
                    self.running = False

    def _interact(self):
        for npc in self.npcs:
            if self.player.rect.inflate(40, 40).colliderect(npc.rect):
                n = self.player.crystals
                if n >= self.TOTAL_CRYSTALS and not self.boss_spawned:
                    self.world.gate_open = True
                    self.boss.dead = False
                    self.boss_spawned = True
                    self.dialog.show(npc.name, ELDER_READY)
                elif self.boss_spawned:  # ← добавлено
                    self.dialog.show(npc.name, ELDER_WAIT)  # ← используется константа
                elif n > 0:
                    self.dialog.show(npc.name, ELDER_PROGRESS)
                else:
                    self.dialog.show(npc.name, ELDER_INTRO)
                return

    # ---------- логика ----------
    def update(self, dt):
        if self.state != 'playing' or self.dialog.active:
            return
        self.player.update(pygame.key.get_pressed(), dt, self.world)

        # подбор кристаллов
        for c in self.crystals:
            if c.collected: continue
            c.update(dt)
            if self.player.rect.colliderect(c.rect):
                c.collected = True
                self.player.crystals += 1
                self.floating_texts.append(FloatingText(
                    self.player.x + self.player.w / 2,
                    self.player.y - 10,
                    CRYSTAL_MSG,
                    (200, 240, 255)
                ))

        # подбор зелий (только если HP не полное)
        for p in self.potions:
            if p.collected: continue
            p.update(dt)
            if self.player.rect.colliderect(p.rect):
                if self.player.hp < self.player.max_hp:
                    p.collected = True
                    self.player.hp += 1
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2,
                        self.player.y - 10,
                        POTION_MSG,
                        (100, 255, 100)          # зелёный
                    ))

        # обновление всплывающих текстов
        for ft in self.floating_texts:
            ft.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if not ft.dead]

        # враги
        hb = self.player.get_attack_hitbox()
        for e in self.enemies:
            if e.dead: continue
            e.update(self.player, self.world, dt)
            if hb and hb.colliderect(e.rect):
                e.take_damage(PLAYER_ATTACK_DAMAGE,
                              self.player.x + self.player.w/2,
                              self.player.y + self.player.h/2)
                self.player.attack_timer = 0
                hb = None
            if not e.dead and e.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):  # ← True, если урон реально прошёл (не invuln)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))

        # босс
        if self.boss and not self.boss.dead:
            self.boss.update(self.player, self.world, dt)
            hb = self.player.get_attack_hitbox()
            if hb and hb.colliderect(self.boss.rect):
                self.boss.take_damage(PLAYER_ATTACK_DAMAGE,
                                      self.player.x + self.player.w / 2,
                                      self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
            if not self.boss.dead and self.boss.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))

        # смерть босса — с задержкой перед экраном победы
        if self.boss and self.boss.dead and self.boss_spawned:  # ← фикс бага 1
            if self.win_delay == 0:
                self.floating_texts.append(FloatingText(
                    self.boss.x + self.boss.w / 2, self.boss.y - 10,
                    "МОРВЕЙН ПАЛ!", (255, 220, 100), duration=1500
                ))
                self.win_delay = 1
            elif self.win_delay > 0:
                self.win_delay += dt
                if self.win_delay >= 1500:
                    self.state = 'win'

        if (self.player.hp <= 0 and self.state != 'win'
                and self.win_delay == 0):  # ← фикс бага 2
            self.state = 'lose'

        self.camera.follow(self.player.x + self.player.w/2,
                           self.player.y + self.player.h/2,
                           self.world.w, self.world.h)

    # ---------- отрисовка ----------
    def draw(self):
        self.screen.fill(COLOR_SKY)
        if self.state == 'title':
            self._draw_title();
            pygame.display.flip();
            return

        self.world.draw(self.screen, self.camera)
        for c in self.crystals: c.draw(self.screen, self.camera)
        for p in self.potions:  p.draw(self.screen, self.camera)
        for n in self.npcs: n.draw(self.screen, self.camera)

        ents = [(e.y + e.h, e) for e in self.enemies if not e.dead]
        if self.boss and not self.boss.dead:
            ents.append((self.boss.y + self.boss.h, self.boss))
        ents.append((self.player.y + self.player.h, self.player))
        ents.sort(key=lambda p: p[0])
        for _, e in ents:
            if e is self.player:
                self.player.draw(self.screen, self.camera)
            elif e is self.boss:
                self.boss.draw(self.screen, self.camera)
            else:
                e.draw(self.screen, self.camera)

        self.dialog.draw(self.screen)

        # всплывающие тексты
        for ft in self.floating_texts:
            ft.draw(self.screen, self.camera)

        # баннер «Замок открыт»
        cx = self.player.x + self.player.w // 2
        cy = self.player.y + self.player.h // 2
        in_castle = (2 * TILE <= cx <= 13 * TILE and 2 * TILE <= cy <= 10 * TILE)
        if self.boss_spawned and not self.boss.dead and not in_castle:
            t = self.font_hint_banner.render(
                "Замок Морвейна открыт! На северо-запад!", True, (255, 200, 100)
            )
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 70))

        if self.state == 'win':   self._overlay_win()
        if self.state == 'lose':  self._overlay_lose()

        # HUD только в игре
        if self.state not in ('win', 'lose'):
            self.hud.draw(self.screen, self.player, self.TOTAL_CRYSTALS)

        pygame.display.flip()

    def _draw_title(self):
        fb = self.font_title_big
        fs = self.font_title_small
        t = fb.render("Хроники Эльдории", True, (240, 210, 130))
        s = fs.render("Тень над Священным Пламенем", True, (200, 200, 220))
        p = fs.render("Нажми любую клавишу", True, (255, 255, 255))
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 200))
        self.screen.blit(s, (WIDTH//2 - s.get_width()//2, 280))
        self.screen.blit(p, (WIDTH//2 - p.get_width()//2, 400))
        for i, line in enumerate([
            "WASD / Стрелки — движение",
            "Space — удар мечом",
            "E — взаимодействие",
            "Собери 3 Кристалла Света, найди Старейшину, победи Морвейна",
        ]):
            t = fs.render(line, True, (180, 180, 200))
            self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 460 + i*30))

    def _overlay_win(self):
        self.screen.blit(self.overlay_black, (0, 0))
        fb = self.font_win_big
        fs = self.font_win_small
        self.screen.blit(fb.render("ПОБЕДА!", True, (240, 210, 130)),
                         (WIDTH // 2 - 130, 220))
        self.screen.blit(fs.render("Священное Пламя возвращено. Эльдория спасена.",
                                   True, (220, 220, 240)), (WIDTH // 2 - 270, 310))
        self.screen.blit(fs.render("Нажми R для новой игры", True, (200, 200, 200)),
                         (WIDTH // 2 - 150, 400))

    def _overlay_lose(self):
        self.screen.blit(self.overlay_red, (0, 0))
        fb = self.font_win_big
        fs = self.font_win_small
        self.screen.blit(fb.render("ТЫ ПАЛ...", True, (200, 60, 60)),
                         (WIDTH // 2 - 140, 250))
        self.screen.blit(fs.render("Нажми R для повторной попытки",
                                   True, (220, 220, 220)), (WIDTH // 2 - 200, 350))

    # ---------- цикл ----------
    async def run(self):  # <-- ОБЯЗАТЕЛЬНО добавить async перед def
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)
        pygame.quit()