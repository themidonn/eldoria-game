"""
game.py — Главный класс игры (Game).

Управляет состояниями (меню, игра, пауза, победа, поражение),
переключением уровней (мир ↔ подземелье), обновлением (update)
и отрисовкой (draw).
"""

import asyncio
import math
import random

import pygame

from settings import *
from data.story import *
from world.map import World
from world.dungeon import Dungeon
from world.camera import Camera
from entities.player import Player
from entities.enemy import Slime
from entities.npc import NPC
from entities.pickup import Crystal
from entities.key import Key
from entities.potion import Potion
from entities.boss import Boss
from entities.lore_stone import LoreStone
from ui.hud import HUD
from ui.dialog import Dialog
from ui.floating_text import FloatingText
from ui.minimap import MiniMap
from ui.particles import ParticleManager


class Game:
    TOTAL_CRYSTALS = 3
    HINT_OFFSET_Y = 50                 # на сколько пикселей выше игрока рисовать подсказку
    CASTLE_X_MIN, CASTLE_X_MAX = 2, 13 # границы замка на карте (для баннера)
    CASTLE_Y_MIN, CASTLE_Y_MAX = 2, 10

    # ============================================================
    #   ИНИЦИАЛИЗАЦИЯ
    # ============================================================
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Хроники Эльдории")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 'title'

        self._init_fonts()
        self._init_cached_surfaces()
        self._reset()

    def _init_fonts(self):
        self.font_title_big = pygame.font.SysFont('arial', 56, bold=True)
        self.font_title_small = pygame.font.SysFont('arial', 24)
        self.font_win_big = pygame.font.SysFont('arial', 64, bold=True)
        self.font_win_small = pygame.font.SysFont('arial', 26)
        self.font_hint_banner = pygame.font.SysFont('arial', 18, bold=True)
        self.font_quest = pygame.font.SysFont('arial', 16, bold=True)

    def _init_cached_surfaces(self):
        # Плашка квеста
        q_text = self.font_quest.render("Задание: Найти ключ жителя", True, (255, 200, 100))
        q_w, q_h = q_text.get_width() + 20, q_text.get_height() + 10
        self.quest_surface = pygame.Surface((q_w, q_h), pygame.SRCALPHA)
        self.quest_surface.fill((20, 20, 30, 200))
        pygame.draw.rect(self.quest_surface, (200, 180, 120), (0, 0, q_w, q_h), 2, border_radius=5)
        self.quest_surface.blit(q_text, (10, 5))

        # Баннер «Замок открыт»
        self.banner_text = self.font_hint_banner.render(
            "Замок Морвейна открыт! На северо-запад!", True, (255, 200, 100)
        )

        # Оверлеи
        self.overlay_black = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_black.fill((0, 0, 0, 180))
        self.overlay_red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_red.fill((40, 0, 0, 180))

        # Виньетка (красная рамка)
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(self.vignette, (255, 0, 0), (0, 0, WIDTH, HEIGHT), width=30)

        # Экраны победы / поражения / паузы
        self.win_text_big = self.font_win_big.render("ПОБЕДА!", True, (240, 210, 130))
        self.win_text_small = self.font_win_small.render(
            "Священное Пламя возвращено. Эльдория спасена.", True, (220, 220, 240)
        )
        self.win_text_hint = self.font_win_small.render("Нажми R для новой игры", True, (200, 200, 200))

        self.lose_text_big = self.font_win_big.render("ТЫ ПАЛ...", True, (200, 60, 60))
        self.lose_text_small = self.font_win_small.render("Нажми R для повторной попытки", True, (220, 220, 220))

        self.pause_text_big = self.font_win_big.render("ПАУЗА", True, (240, 210, 130))
        self.pause_text_1 = self.font_win_small.render("ESC — продолжить игру", True, (220, 220, 240))
        self.pause_text_2 = self.font_win_small.render("Q — выйти из игры", True, (200, 200, 200))

        # Подсказки для лестниц
        self.hint_enter = self._make_hint("E — войти в подземелье")
        self.hint_exit = self._make_hint("E — выйти на поверхность")

    def _make_hint(self, text):
        """Создаёт полупрозрачную плашку с текстом."""
        text_surf = self.font_hint_banner.render(text, True, (255, 255, 150))
        w, h = text_surf.get_width() + 20, text_surf.get_height() + 10
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((20, 20, 30, 200))
        pygame.draw.rect(surf, (200, 200, 100), (0, 0, w, h), 1, border_radius=4)
        surf.blit(text_surf, (10, 5))
        return surf

    # ============================================================
    #   СБРОС И СПАВН
    # ============================================================
    def _reset(self):
        self.main_world = World()
        self.dungeon = None
        self.current_map = self.main_world
        self.level = 1
        self.saved_position = None

        self.minimap = MiniMap(self.main_world)
        self.particles = ParticleManager()
        self.player = Player(50 * TILE + 7, 65 * TILE + 7)
        self.camera = Camera()
        self.dialog = Dialog()
        self.hud = HUD()

        # Списки сущностей
        self.enemies, self.npcs, self.crystals = [], [], []
        self.potions, self.lore_stones, self.floating_texts = [], [], []
        self.boss = None

        # Флаги прогресса
        self.boss_spawned = False
        self.win_delay = 0
        self.villager_met = False
        self.villager_refused = False
        self.has_key = False
        self.key = None
        self.quest_completed = False
        self.lore_reward_given = False

        self._spawn()

    def _spawn(self):
        # --- NPC ---
        self.npcs.append(NPC(48 * TILE, 65 * TILE, "Старейшина"))
        self.npcs.append(NPC(55 * TILE, 48 * TILE, "Житель"))

        # --- Кристаллы и их охрана ---
        self._spawn_crystal_and_guards(85, 30, "Кристалл Леса", [(-3, 2), (0, 2), (3, 2)], hp=2)
        self._spawn_crystal_and_guards(72, 50, "Кристалл Воды", [(-2, -2), (-2, 2), (2, -2), (2, 2)], hp=2)
        self._spawn_crystal_and_guards(15, 40, "Кристалл Руин", [(-3, 2), (0, 2), (3, 2)], hp=3)

        # --- Босс ---
        self.boss = Boss(7 * TILE, 5 * TILE)

        # --- Случайные слизни ---
        rng = random.Random(99)
        for _ in range(30):
            tx = rng.randint(5, self.world.w - 5)
            ty = rng.randint(5, self.world.h - 5)
            # Не спавним слишком близко к старту
            if self.world.tiles[ty][tx] == GRASS and abs(tx - 50) + abs(ty - 65) > 10:
                self.enemies.append(Slime(tx * TILE, ty * TILE))

        # --- Зелья ---
        potion_positions = [(51, 63), (84, 32), (16, 42), (7, 11), (72, 48)]
        for tx, ty in potion_positions:
            if self.world.tiles[ty][tx] == GRASS:
                self.potions.append(Potion(tx * TILE, ty * TILE))

        # --- Ключ (рандом в зоне из settings.py) ---
        rng_key = random.Random()
        for _ in range(100):
            tx = rng_key.randint(KEY_ZONE_X_MIN, KEY_ZONE_X_MAX)
            ty = rng_key.randint(KEY_ZONE_Y_MIN, KEY_ZONE_Y_MAX)
            if self.world.tiles[ty][tx] == GRASS:
                self.key = Key(tx * TILE, ty * TILE)
                break
        else:
            # Fallback: если 100 попыток не нашли траву — ставим ключ у кристалла леса
            self.key = Key(85 * TILE, 30 * TILE)

        # --- Лор-камни ---
        self.lore_stones.append(LoreStone(53 * TILE, 63 * TILE, "Древний камень", LORE_START))
        self.lore_stones.append(LoreStone(14 * TILE, 40 * TILE, "Камень Аэтельгарда", LORE_RUINS))
        self.lore_stones.append(LoreStone(71 * TILE, 50 * TILE, "Камень Озера", LORE_LAKE))
        self.lore_stones.append(LoreStone(58 * TILE, 50 * TILE, "Камень деревни", LORE_VILLAGE))
        self.lore_stones.append(LoreStone(6 * TILE, 12 * TILE, "Камень у врат", LORE_CASTLE))

    def _spawn_crystal_and_guards(self, cx, cy, name, offsets, hp):
        """Хелпер: ставит кристалл и слизней вокруг него (только на траве)."""
        self.crystals.append(Crystal(cx * TILE, cy * TILE, name))
        for dx, dy in offsets:
            tx, ty = cx + dx, cy + dy
            if self.world.tiles[ty][tx] == GRASS:
                self.enemies.append(Slime(tx * TILE, ty * TILE, hp=hp))

    # ============================================================
    #   ПЕРЕКЛЮЧЕНИЕ УРОВНЕЙ
    # ============================================================
    @property
    def world(self):
        """Активная карта (World или Dungeon)."""
        return self.current_map

    def enter_dungeon(self):
        if self.dungeon is None:
            self.dungeon = Dungeon()
        self.saved_position = (self.player.x, self.player.y)
        self.current_map = self.dungeon
        self.level = 2
        self.player.x = 6 * TILE + 7
        self.player.y = (self.dungeon.h - 4) * TILE + 7
        self.camera = Camera()
        self.particles = ParticleManager()
        self.floating_texts = []

    def exit_dungeon(self):
        self.current_map = self.main_world
        self.level = 1
        if self.saved_position:
            self.player.x, self.player.y = self.saved_position
        self.camera = Camera()
        self.particles = ParticleManager()
        self.floating_texts = []

    # ============================================================
    #   СОБЫТИЯ
    # ============================================================
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                self._handle_keydown(e.key)

    def _handle_keydown(self, key):
        if self.state == 'title':
            self.state = 'playing'
            return

        if self.state in ('win', 'lose'):
            if key == pygame.K_r:
                self._reset()
                self.state = 'playing'
            return

        if self.dialog.active:
            self._handle_dialog_input(key)
            return

        if key == pygame.K_ESCAPE:
            self.state = 'paused' if self.state == 'playing' else 'playing'
            return

        if self.state == 'paused':
            if key == pygame.K_q:
                self.running = False
            return

        if key in (pygame.K_SPACE, pygame.K_j):
            self.player.try_attack()
        elif key == pygame.K_e:
            self._interact()

    def _handle_dialog_input(self, key):
        if self.dialog.is_choice:
            if key == pygame.K_y:
                self.dialog.active = False
                self.villager_met = True
                self.dialog.show("Житель", VILLAGER_YES)
            elif key == pygame.K_n:
                self.dialog.active = False
                self.villager_refused = True
                self.dialog.show("Житель", VILLAGER_NO)
        else:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.dialog.next_page()
            elif key == pygame.K_ESCAPE:
                self.dialog.active = False

    # ============================================================
    #   ВЗАИМОДЕЙСТВИЕ (E)
    # ============================================================
    def _interact(self):
        if self._try_use_stairs():
            return
        if self.level != 1:
            return

        if self._try_read_lore_stone():
            return
        self._try_talk_to_npc()

    def _try_use_stairs(self):
        """Проверяет, стоит ли игрок на лестнице. Возвращает True, если сработало."""
        cx = int((self.player.x + self.player.w / 2) // TILE)
        cy = int((self.player.y + self.player.h / 2) // TILE)

        if not (0 <= cy < self.world.h and 0 <= cx < self.world.w):
            return False

        tile = self.world.tiles[cy][cx]
        if tile == STAIRS_DOWN and self.level == 1:
            self.enter_dungeon()
            return True
        if tile == STAIRS_UP and self.level == 2:
            self.exit_dungeon()
            return True
        return False

    def _try_read_lore_stone(self):
        """Проверяет лор-камни. Возвращает True, если прочитали."""
        for stone in self.lore_stones:
            if self.player.rect.inflate(40, 40).colliderect(stone.rect):
                self.dialog.show(stone.title, stone.text)
                stone.is_read = True

                # Награда: +1 HP за все 5 камней
                if not self.lore_reward_given and all(s.is_read for s in self.lore_stones):
                    self.lore_reward_given = True
                    self.player.max_hp += 1
                    self.player.hp = self.player.max_hp
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "Знание предков! +1 Макс. HP", (180, 220, 255), duration=2500
                    ))
                return True
        return False

    def _try_talk_to_npc(self):
        """Проверяет NPC и запускает диалог."""
        for npc in self.npcs:
            if not self.player.rect.inflate(40, 40).colliderect(npc.rect):
                continue

            if npc.name == "Житель":
                if self.villager_refused:
                    return
                if not self.villager_met:
                    self.dialog.show(npc.name, VILLAGER_INTRO, is_choice=True)
                elif self.has_key:
                    self.dialog.show(npc.name, VILLAGER_THANKS)
                    self.has_key = False
                    self.quest_completed = True
                    self.player.upgrade_weapon()
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "Стальной клинок!", (255, 215, 0), duration=2000
                    ))
                else:
                    self.dialog.show(npc.name, VILLAGER_WAIT)
                return

            # Старейшина
            n = self.player.crystals
            if n >= self.TOTAL_CRYSTALS and not self.boss_spawned:
                self.world.gate_open = True
                self.boss.dead = False
                self.boss_spawned = True
                self.dialog.show(npc.name, ELDER_READY)
            elif self.boss_spawned:
                self.dialog.show(npc.name, ELDER_WAIT)
            elif n > 0:
                self.dialog.show(npc.name, ELDER_PROGRESS)
            else:
                self.dialog.show(npc.name, ELDER_INTRO)
            return

    # ============================================================
    #   ЛОГИКА (UPDATE)
    # ============================================================
    def update(self, dt):
        if self.state != 'playing' or self.dialog.active:
            return

        self.player.update(pygame.key.get_pressed(), dt, self.world)

        if self.level == 1:
            self._update_level_1(dt)
        else:
            self.dungeon.update(dt)

        self._update_common(dt)

    def _update_level_1(self, dt):
        # --- Кристаллы ---
        for c in self.crystals:
            if c.collected: continue
            c.update(dt)
            if self.player.rect.colliderect(c.rect):
                c.collected = True
                self.player.crystals += 1
                self.floating_texts.append(FloatingText(
                    self.player.x + self.player.w / 2, self.player.y - 10,
                    CRYSTAL_MSG, (200, 240, 255)
                ))

        # --- Зелья ---
        for p in self.potions:
            if p.collected: continue
            p.update(dt)
            if self.player.rect.colliderect(p.rect):
                if self.player.hp < self.player.max_hp:
                    p.collected = True
                    self.player.hp += 1
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        POTION_MSG, (100, 255, 100)
                    ))

        # --- Ключ ---
        if self.key and not self.key.collected:
            self.key.update(dt)
            if self.player.rect.colliderect(self.key.rect):
                self.key.collected = True
                self.has_key = True
                self.floating_texts.append(FloatingText(
                    self.player.x + self.player.w / 2, self.player.y - 10,
                    KEY_MSG, (255, 215, 0)
                ))

        # --- Враги ---
        hb = self.player.get_attack_hitbox()
        for e in self.enemies:
            if e.dead: continue
            e.update(self.player, self.world, dt)
            if hb and hb.colliderect(e.rect):
                e.take_damage(self.player.damage, self.player.x + self.player.w / 2, self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
                hb = None
                self.camera.add_shake(2)
                self.floating_texts.append(FloatingText(
                    e.x + e.w / 2, e.y - 10, "-1", (255, 255, 100), duration=600
                ))
            if not e.dead and e.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10, "-1 HP", (255, 100, 100)
                    ))
            if e.dead:
                self.particles.spawn_burst(e.x + e.w / 2, e.y + e.h / 2, COLOR_SLIME)

        # --- Босс ---
        if self.boss and not self.boss.dead:
            self.boss.update(self.player, self.world, dt)
            hb = self.player.get_attack_hitbox()
            if hb and hb.colliderect(self.boss.rect):
                self.boss.take_damage(self.player.damage, self.player.x + self.player.w / 2, self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
                self.camera.add_shake(3)
                self.floating_texts.append(FloatingText(
                    self.boss.x + self.boss.w / 2, self.boss.y - 10, "-1", (255, 255, 100), duration=600
                ))
            if not self.boss.dead and self.boss.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10, "-1 HP", (255, 100, 100)
                    ))

        # --- Смерть босса ---
        if self.boss and self.boss.dead and self.boss_spawned:
            if self.win_delay == 0:
                self.particles.spawn_burst(self.boss.x + self.boss.w / 2, self.boss.y + self.boss.h / 2, COLOR_BOSS, count=40)
                self.camera.add_shake(10)
                self.floating_texts.append(FloatingText(
                    self.boss.x + self.boss.w / 2, self.boss.y - 10, "МОРВЕЙН ПАЛ!", (255, 220, 100), duration=1500
                ))
                self.win_delay = 1
            else:
                self.win_delay += dt
                if self.win_delay >= 1500:
                    self.state = 'win'

    def _update_common(self, dt):
        for ft in self.floating_texts:
            ft.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if not ft.dead]

        if self.player.hp <= 0 and self.state != 'win' and self.win_delay == 0:
            self.state = 'lose'

        self.particles.update(dt)
        self.camera.follow(self.player.x + self.player.w / 2, self.player.y + self.player.h / 2, self.world.w, self.world.h)

    # ============================================================
    #   ОТРИСОВКА (DRAW)
    # ============================================================
    def draw(self):
        self.screen.fill(COLOR_SKY)
        if self.state == 'title':
            self._draw_title()
            pygame.display.flip()
            return

        self.world.draw(self.screen, self.camera)

        if self.level == 1:
            self._draw_level_1()
        else:
            self._draw_level_2()

        self._draw_hints()
        self._draw_ui()
        self._draw_overlays()

        pygame.display.flip()

    def _draw_level_1(self):
        for stone in self.lore_stones: stone.draw(self.screen, self.camera)
        for c in self.crystals: c.draw(self.screen, self.camera)
        if self.key and not self.key.collected:
            self.key.draw(self.screen, self.camera)
        for p in self.potions: p.draw(self.screen, self.camera)
        for n in self.npcs: n.draw(self.screen, self.camera)

        # Сортировка сущностей по Y для правильного перекрытия
        ents = [(e.y + e.h, e) for e in self.enemies if not e.dead]
        if self.boss and not self.boss.dead:
            ents.append((self.boss.y + self.boss.h, self.boss))
        ents.append((self.player.y + self.player.h, self.player))
        ents.sort(key=lambda p: p[0])

        for _, e in ents:
            if e is self.player: self.player.draw(self.screen, self.camera)
            elif e is self.boss: self.boss.draw(self.screen, self.camera)
            else: e.draw(self.screen, self.camera)

    def _draw_level_2(self):
        self.player.draw(self.screen, self.camera)

    def _draw_hints(self):
        if self.state != 'playing' or self.dialog.active:
            return

        cx = int((self.player.x + self.player.w / 2) // TILE)
        cy = int((self.player.y + self.player.h / 2) // TILE)
        if not (0 <= cy < self.world.h and 0 <= cx < self.world.w):
            return

        tile = self.world.tiles[cy][cx]
        hint = None
        if tile == STAIRS_DOWN and self.level == 1:
            hint = self.hint_enter
        elif tile == STAIRS_UP and self.level == 2:
            hint = self.hint_exit

        if hint:
            hx = int(self.player.x - self.camera.x + self.player.w / 2) - hint.get_width() // 2
            hy = int(self.player.y - self.camera.y) - self.HINT_OFFSET_Y
            self.screen.blit(hint, (hx, hy))

    def _draw_ui(self):
        self.dialog.draw(self.screen)
        self.particles.draw(self.screen, self.camera)

        for ft in self.floating_texts:
            ft.draw(self.screen, self.camera)

        # Баннер «Замок открыт» (только в мире, только после активации, только снаружи)
        if self.level == 1 and self.boss_spawned and not self.boss.dead:
            cx = self.player.x + self.player.w // 2
            cy = self.player.y + self.player.h // 2
            in_castle = (self.CASTLE_X_MIN * TILE <= cx <= self.CASTLE_X_MAX * TILE and
                         self.CASTLE_Y_MIN * TILE <= cy <= self.CASTLE_Y_MAX * TILE)
            if not in_castle:
                self.screen.blit(self.banner_text, (WIDTH // 2 - self.banner_text.get_width() // 2, 70))

        # HUD и миникарта
        if self.state not in ('win', 'lose', 'paused'):
            self.hud.draw(self.screen, self.player, self.TOTAL_CRYSTALS)

            if self.level == 1:
                self.minimap.draw(self.screen, self)
                if self.villager_met and not self.villager_refused and not self.has_key and not self.quest_completed:
                    self.screen.blit(self.quest_surface, (20, 60))

        # Красная виньетка при низком HP
        if self.player.hp <= 2 and self.state == 'playing':
            pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 100) + 50
            self.vignette.set_alpha(pulse)
            self.screen.blit(self.vignette, (0, 0))

    def _draw_overlays(self):
        if self.state == 'win':   self._overlay_win()
        if self.state == 'lose':  self._overlay_lose()
        if self.state == 'paused': self._overlay_pause()

    # ============================================================
    #   ЭКРАНЫ (ТИТУЛЬНИК, ОВЕРЛЕИ)
    # ============================================================
    def _draw_title(self):
        t = self.font_title_big.render("Хроники Эльдории", True, (240, 210, 130))
        s = self.font_title_small.render("Тень над Священным Пламенем", True, (200, 200, 220))
        p = self.font_title_small.render("Нажми любую клавишу", True, (255, 255, 255))
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 200))
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 280))
        self.screen.blit(p, (WIDTH // 2 - p.get_width() // 2, 400))
        for i, line in enumerate([
            "WASD / Стрелки — движение",
            "Space — удар мечом",
            "E — взаимодействие",
            "Собери 3 Кристалла Света, найди Старейшину, победи Морвейна",
        ]):
            txt = self.font_title_small.render(line, True, (180, 180, 200))
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 460 + i * 30))

    def _overlay_win(self):
        self.screen.blit(self.overlay_black, (0, 0))
        self.screen.blit(self.win_text_big, (WIDTH // 2 - self.win_text_big.get_width() // 2, 220))
        self.screen.blit(self.win_text_small, (WIDTH // 2 - self.win_text_small.get_width() // 2, 310))
        self.screen.blit(self.win_text_hint, (WIDTH // 2 - self.win_text_hint.get_width() // 2, 400))

    def _overlay_lose(self):
        self.screen.blit(self.overlay_red, (0, 0))
        self.screen.blit(self.lose_text_big, (WIDTH // 2 - self.lose_text_big.get_width() // 2, 250))
        self.screen.blit(self.lose_text_small, (WIDTH // 2 - self.lose_text_small.get_width() // 2, 350))

    def _overlay_pause(self):
        self.screen.blit(self.overlay_black, (0, 0))
        self.screen.blit(self.pause_text_big, (WIDTH // 2 - self.pause_text_big.get_width() // 2, 200))
        self.screen.blit(self.pause_text_1, (WIDTH // 2 - self.pause_text_1.get_width() // 2, 300))
        self.screen.blit(self.pause_text_2, (WIDTH // 2 - self.pause_text_2.get_width() // 2, 350))

    # ============================================================
    #   ГЛАВНЫЙ ЦИКЛ
    # ============================================================
    async def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)
        pygame.quit()