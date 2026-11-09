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
import save
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
from entities.bat import Bat
from entities.chest import Chest
from entities.skeleton import Skeleton
from entities.skeleton_king import SkeletonKing, BoneProjectile
from ui.hud import HUD
from ui.dialog import Dialog
from ui.floating_text import FloatingText
from ui.minimap import MiniMap
from ui.particles import ParticleManager

# Страницы вступления — разбиваем INTRO по точкам на отдельные предложения.
# Показываем по одной за раз на весь экран.
INTRO_PAGES = [s.strip() + "." for s in INTRO.split(".") if s.strip()]

class Game:
    TOTAL_CRYSTALS = 3
    HINT_OFFSET_Y = 50
    CASTLE_X_MIN, CASTLE_X_MAX = 2, 13
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

        self._has_save = save.exists()

    def _init_fonts(self):
        self.font_title_big = pygame.font.Font('arial', 56)
        self.font_title_small = pygame.font.Font('arial', 24)
        self.font_win_big = pygame.font.Font('arial', 64)
        self.font_win_small = pygame.font.Font('arial', 26)
        self.font_hint_banner = pygame.font.Font('arial', 18)
        self.font_quest = pygame.font.Font('arial', 16)
        self.font_intro = pygame.font.Font('arial', 28)

    def _make_quest_surface(self, text):
        q_text = self.font_quest.render(text, True, (255, 200, 100))
        q_w, q_h = q_text.get_width() + 20, q_text.get_height() + 10
        surf = pygame.Surface((q_w, q_h), pygame.SRCALPHA)
        surf.fill((20, 20, 30, 200))
        pygame.draw.rect(surf, (200, 180, 120), (0, 0, q_w, q_h), 2, border_radius=5)
        surf.blit(q_text, (10, 5))
        return surf

    def _init_cached_surfaces(self):
        self.quest_surface_find = self._make_quest_surface("Задание: Найти ключ жителя")
        self.quest_surface_return = self._make_quest_surface("Задание: Вернуть ключ жителю")

        self.banner_text = self.font_hint_banner.render(
            "Замок Морвейна открыт! На северо-запад!", True, (255, 200, 100)
        )

        self.overlay_black = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_black.fill((0, 0, 0, 180))
        self.overlay_red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_red.fill((40, 0, 0, 180))

        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(self.vignette, (255, 0, 0), (0, 0, WIDTH, HEIGHT), width=30)

        self.win_text_big = self.font_win_big.render("ПОБЕДА!", True, (240, 210, 130))
        self.win_text_small = self.font_win_small.render(
            "Священное Пламя возвращено. Эльдория спасена.", True, (220, 220, 240)
        )
        self.win_text_hint = self.font_win_small.render("Нажми R для новой игры", True, (200, 200, 200))

        self.lose_text_big = self.font_win_big.render("ТЫ ПАЛ...", True, (200, 60, 60))
        self.lose_text_small = self.font_win_small.render("Нажми R для повторной попытки", True, (220, 220, 220))

        self.pause_text_big = self.font_win_big.render("ПАУЗА", True, (240, 210, 130))
        self.pause_text_1 = self.font_win_small.render("ESC — продолжить игру", True, (220, 220, 240))
        self.pause_text_save = self.font_win_small.render("F5 — сохранить игру", True, (150, 200, 255))
        self.pause_text_2 = self.font_win_small.render("Q — выйти из игры", True, (200, 200, 200))

        self.hint_enter = self._make_hint("E — войти в подземелье")
        self.hint_exit = self._make_hint("E — выйти на поверхность")
        self.hint_chest = self._make_hint("E — открыть сундук")

        # Страницы вступления — каждая отрендерена в готовый Surface
        self.intro_pages = [self._wrap_intro_page(p) for p in INTRO_PAGES]

    def _wrap_intro_page(self, text):
        """Рендерит страницу вступления: центрированные строки в Surface."""
        max_w = WIDTH - 200
        words = text.split()

        # --- Разбиение на строки ---
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_intro.size(test)[0] > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)

        # --- Рендер в Surface (строки центрированы) ---
        line_height = self.font_intro.get_linesize()
        surf_h = line_height * len(lines)
        page_surf = pygame.Surface((max_w, surf_h), pygame.SRCALPHA)

        for j, line in enumerate(lines):
            line_surf = self.font_intro.render(line, True, (220, 220, 240))
            lx = (max_w - line_surf.get_width()) // 2
            page_surf.blit(line_surf, (lx, j * line_height))

        return page_surf

    def _make_hint(self, text):
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
        self.dungeon_bats = []
        self.dungeon_chest = None
        self.dungeon_lore_stones = []
        self.dungeon_skeletons = []
        self.dungeon_boss = None
        self.dungeon_projectiles = []
        self.current_map = self.main_world
        self.level = 1
        self.saved_position = None

        self.minimap = MiniMap(self.main_world)
        self.particles = ParticleManager()
        self.player = Player(50 * TILE + 7, 65 * TILE + 7)
        self.camera = Camera()
        self.dialog = Dialog()
        self.hud = HUD()

        self.enemies, self.npcs, self.crystals = [], [], []
        self.potions, self.lore_stones, self.floating_texts = [], [], []
        self.boss = None

        self.boss_spawned = False
        self.win_delay = 0
        self.villager_met = False
        self.villager_refused = False
        self.has_key = False
        self.key = None
        self.quest_completed = False
        self.lore_reward_given = False
        self.banner_timer = 0

        # Вступление
        self.intro_page = 0
        self.intro_page_changed_at = pygame.time.get_ticks()

        self._spawn()

    def _spawn(self):
        self.npcs.append(NPC(48 * TILE, 65 * TILE, "Старейшина"))
        self.npcs.append(NPC(55 * TILE, 48 * TILE, "Житель"))

        self._spawn_crystal_and_guards(85, 30, "Кристалл Леса", [(-3, 2), (0, 2), (3, 2)], hp=2)
        self._spawn_crystal_and_guards(72, 50, "Кристалл Воды", [(-2, -2), (-2, 2), (2, -2), (2, 2)], hp=2)
        self._spawn_crystal_and_guards(15, 40, "Кристалл Руин", [(-3, 2), (0, 2), (3, 2)], hp=3)

        self.boss = Boss(7 * TILE, 5 * TILE)

        rng = random.Random(99)
        for _ in range(30):
            tx = rng.randint(5, self.world.w - 5)
            ty = rng.randint(5, self.world.h - 5)
            if self.world.tiles[ty][tx] == GRASS and abs(tx - 50) + abs(ty - 65) > 10:
                self.enemies.append(Slime(tx * TILE, ty * TILE))

        potion_positions = [(51, 63), (84, 32), (16, 42), (7, 11), (72, 48)]
        for tx, ty in potion_positions:
            if self.world.tiles[ty][tx] == GRASS:
                self.potions.append(Potion(tx * TILE, ty * TILE))

        rng_key = random.Random()
        for _ in range(100):
            tx = rng_key.randint(KEY_ZONE_X_MIN, KEY_ZONE_X_MAX)
            ty = rng_key.randint(KEY_ZONE_Y_MIN, KEY_ZONE_Y_MAX)
            if self.world.tiles[ty][tx] == GRASS:
                self.key = Key(tx * TILE, ty * TILE)
                break
        else:
            self.key = Key(85 * TILE, 30 * TILE)

        self.lore_stones.append(LoreStone(53 * TILE, 63 * TILE, "Древний камень", LORE_START))
        self.lore_stones.append(LoreStone(14 * TILE, 40 * TILE, "Камень Аэтельгарда", LORE_RUINS))
        self.lore_stones.append(LoreStone(71 * TILE, 50 * TILE, "Камень Озера", LORE_LAKE))
        self.lore_stones.append(LoreStone(58 * TILE, 50 * TILE, "Камень деревни", LORE_VILLAGE))
        self.lore_stones.append(LoreStone(6 * TILE, 12 * TILE, "Камень у врат", LORE_CASTLE))

    def _spawn_crystal_and_guards(self, cx, cy, name, offsets, hp):
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
        return self.current_map

    def _ensure_dungeon(self):
        if self.dungeon is None:
            self.dungeon = Dungeon()

        if not self.dungeon_bats:
            bat_positions = [(8, 8), (13, 13), (18, 8), (23, 18), (33, 13)]
            for tx, ty in bat_positions:
                px = tx * TILE + TILE // 2
                py = ty * TILE + TILE // 2
                if self.dungeon.is_walkable_px(px, py):
                    self.dungeon_bats.append(Bat(tx * TILE, ty * TILE))

        if self.dungeon_chest is None:
            self.dungeon_chest = Chest(35 * TILE, 4 * TILE)

        if not self.dungeon_skeletons:
            skeleton_positions = [(31, 11), (39, 11), (31, 15), (39, 15)]
            for tx, ty in skeleton_positions:
                px = tx * TILE + TILE // 2
                py = ty * TILE + TILE // 2
                if self.dungeon.is_walkable_px(px, py):
                    self.dungeon_skeletons.append(Skeleton(tx * TILE, ty * TILE))

        if self.dungeon_boss is None:
            self.dungeon_boss = SkeletonKing(35 * TILE, 7 * TILE)

        if not self.dungeon_lore_stones:
            lore_positions = [
                (7,  20, "Камень у входа",   LORE_DUNGEON_ENTRY),
                (15, 7,  "Камень с фреской", LORE_DUNGEON_MIDDLE),
                (32, 20, "Камень у алтаря",  LORE_DUNGEON_DEEP),
            ]
            for tx, ty, title, text in lore_positions:
                px = tx * TILE + TILE // 2
                py = ty * TILE + TILE // 2
                if self.dungeon.is_walkable_px(px, py):
                    self.dungeon_lore_stones.append(
                        LoreStone(tx * TILE, ty * TILE, title, text)
                    )

    def enter_dungeon(self):
        self._ensure_dungeon()
        self.saved_position = (self.player.x, self.player.y)
        self.current_map = self.dungeon
        self.level = 2
        self.player.x = 6 * TILE + 7
        self.player.y = (self.dungeon.h - 4) * TILE + 7
        self.camera = Camera()
        self.particles = ParticleManager()
        self.floating_texts = []
        self.dungeon_projectiles = []
        self.save_progress()

    def exit_dungeon(self):
        self.current_map = self.main_world
        self.level = 1
        if self.saved_position:
            self.player.x, self.player.y = self.saved_position
        self.camera = Camera()
        self.particles = ParticleManager()
        self.floating_texts = []
        self.dungeon_projectiles = []
        self.save_progress()

    # ============================================================
    #   СОХРАНЕНИЕ / ЗАГРУЗКА
    # ============================================================
    def save_progress(self):
        if not hasattr(self, 'player'):
            return
        if self.state not in ('playing', 'paused'):
            return

        data = {
            'version': 1,
            'level': self.level,
            'saved_position': self.saved_position,
            'player': {
                'x': self.player.x,
                'y': self.player.y,
                'hp': self.player.hp,
                'max_hp': self.player.max_hp,
                'damage': self.player.damage,
                'weapon_upgraded': self.player.weapon_upgraded,
                'crystals': self.player.crystals,
            },
            'progress': {
                'boss_spawned': self.boss_spawned,
                'villager_met': self.villager_met,
                'villager_refused': self.villager_refused,
                'has_key': self.has_key,
                'quest_completed': self.quest_completed,
                'lore_reward_given': self.lore_reward_given,
            },
            'world': {
                'gate_open': self.main_world.gate_open,
                'key': {
                    'collected': self.key.collected if self.key else False,
                    'x': self.key.x if self.key else 0,
                    'y': self.key.y if self.key else 0,
                },
                'dead_enemies': [i for i, e in enumerate(self.enemies) if e.dead],
                'collected_crystals': [i for i, c in enumerate(self.crystals) if c.collected],
                'collected_potions': [i for i, p in enumerate(self.potions) if p.collected],
                'read_lore': [i for i, s in enumerate(self.lore_stones) if s.is_read],
            },
            'dungeon': {
                'has_dungeon': self.dungeon is not None,
                'chest_opened': self.dungeon_chest.opened if self.dungeon_chest else False,
                'dead_bats': [i for i, b in enumerate(self.dungeon_bats) if b.dead],
                'dead_skeletons': [i for i, s in enumerate(self.dungeon_skeletons) if s.dead],
                'boss_dead': self.dungeon_boss.dead if self.dungeon_boss else False,
                'read_lore': [i for i, s in enumerate(self.dungeon_lore_stones) if s.is_read],
            },
            'boss': {
                'dead': self.boss.dead if self.boss else True,
                'hp': self.boss.hp if self.boss else 0,
                'phase': self.boss.phase if self.boss else 'idle',
                'charge_timer': self.boss.charge_timer if self.boss else 3.0,
                'windup_timer': self.boss.windup_timer if self.boss else 0.0,
            },
        }
        if save.write(data):
            self._has_save = True

    def load_progress(self):
        data = save.read()
        if not data:
            self._reset()
            return

        self._reset()

        p = data.get('player', {})
        self.player.max_hp = max(1, int(p.get('max_hp', self.player.max_hp)))
        self.player.hp = max(1, min(self.player.max_hp, int(p.get('hp', self.player.max_hp))))
        self.player.damage = int(p.get('damage', 1))
        self.player.weapon_upgraded = bool(p.get('weapon_upgraded', False))
        self.player.crystals = int(p.get('crystals', 0))

        pr = data.get('progress', {})
        self.boss_spawned = bool(pr.get('boss_spawned', False))
        self.villager_met = bool(pr.get('villager_met', False))
        self.villager_refused = bool(pr.get('villager_refused', False))
        self.has_key = bool(pr.get('has_key', False))
        self.quest_completed = bool(pr.get('quest_completed', False))
        self.lore_reward_given = bool(pr.get('lore_reward_given', False))

        w = data.get('world', {})
        self.main_world.gate_open = bool(w.get('gate_open', False))

        kd = w.get('key', {})
        if self.key:
            if kd.get('collected', False):
                self.key.collected = True
            else:
                self.key.x = kd.get('x', self.key.x)
                self.key.y = kd.get('y', self.key.y)

        for i in w.get('dead_enemies', []):
            if 0 <= i < len(self.enemies):
                self.enemies[i].dead = True
        for i in w.get('collected_crystals', []):
            if 0 <= i < len(self.crystals):
                self.crystals[i].collected = True
        for i in w.get('collected_potions', []):
            if 0 <= i < len(self.potions):
                self.potions[i].collected = True
        for i in w.get('read_lore', []):
            if 0 <= i < len(self.lore_stones):
                self.lore_stones[i].is_read = True

        b = data.get('boss', {})
        if self.boss:
            self.boss.dead = bool(b.get('dead', True))
            self.boss.hp = int(b.get('hp', self.boss.max_hp))
            self.boss.phase = b.get('phase', 'idle')
            self.boss.charge_timer = float(b.get('charge_timer', 3.0))
            self.boss.windup_timer = float(b.get('windup_timer', 0.0))
            # Защита: не даём боссу «мгновенно выстрелить» после загрузки.
            # Если сохранились в момент windup/charge — при загрузке
            # босс спокойно стоит, и у игрока есть 1 сек на реакцию.
            if self.boss.phase in ('charge', 'windup'):
                self.boss.phase = 'idle'
                self.boss.charge_timer = 1.0

        d = data.get('dungeon', {})
        if d.get('has_dungeon', False):
            self._ensure_dungeon()
            for i in d.get('dead_bats', []):
                if 0 <= i < len(self.dungeon_bats):
                    self.dungeon_bats[i].dead = True
            for i in d.get('dead_skeletons', []):
                if 0 <= i < len(self.dungeon_skeletons):
                    self.dungeon_skeletons[i].dead = True
            for i in d.get('read_lore', []):
                if 0 <= i < len(self.dungeon_lore_stones):
                    self.dungeon_lore_stones[i].is_read = True
            if self.dungeon_chest and d.get('chest_opened', False):
                self.dungeon_chest.opened = True
            if self.dungeon_boss and d.get('boss_dead', False):
                self.dungeon_boss.dead = True

        sp = data.get('saved_position')
        if sp and isinstance(sp, (list, tuple)) and len(sp) == 2:
            self.saved_position = (float(sp[0]), float(sp[1]))

        level = int(data.get('level', 1))
        if level == 2 and self.dungeon is not None:
            self.current_map = self.dungeon
            self.level = 2
            self.player.x = float(p.get('x', 6 * TILE + 7))
            self.player.y = float(p.get('y', (self.dungeon.h - 4) * TILE + 7))
            self.camera = Camera()
        else:
            self.level = 1
            self.player.x = float(p.get('x', 50 * TILE + 7))
            self.player.y = float(p.get('y', 65 * TILE + 7))

    # ============================================================
    #   СОБЫТИЯ
    # ============================================================
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.save_progress()
                self.running = False
            elif e.type == pygame.KEYDOWN:
                self._handle_keydown(e.key)

    def _handle_keydown(self, key):
        # --- Титульный экран ---
        if self.state == 'title':
            if self._has_save:
                if key == pygame.K_RETURN:
                    self.load_progress()
                    self.state = 'playing'
                elif key == pygame.K_n:
                    save.delete()
                    self._has_save = False
                    self._reset()
                    self.state = 'intro'
            else:
                self._reset()
                self.state = 'intro'
            return

        # --- Экран вступления ---
        if self.state == 'intro':
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.intro_page += 1
                self.intro_page_changed_at = pygame.time.get_ticks()
                if self.intro_page >= len(self.intro_pages):
                    self.state = 'playing'
                    self.intro_page = 0
            elif key == pygame.K_ESCAPE:
                self.state = 'playing'
                self.intro_page = 0
            return

        # --- Победа / поражение ---
        if self.state in ('win', 'lose'):
            if key == pygame.K_r:
                save.delete()
                self._has_save = False
                self._reset()
                self.state = 'playing'  # без вступления — уже видел
            return

        # --- Диалог ---
        if self.dialog.active:
            self._handle_dialog_input(key)
            return

        # --- Пауза ---
        if key == pygame.K_ESCAPE:
            self.state = 'paused' if self.state == 'playing' else 'playing'
            return

        if self.state == 'paused':
            if key == pygame.K_q:
                self.save_progress()
                self.running = False
            elif key == pygame.K_F5:
                self.save_progress()
            return

        # --- Ручное сохранение ---
        if key == pygame.K_F5:
            self.save_progress()
            self.floating_texts.append(FloatingText(
                self.player.x + self.player.w / 2, self.player.y - 30,
                "Сохранено", (180, 220, 255), duration=1000
            ))
            return

        # --- Атака / взаимодействие ---
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
                self.save_progress()
            elif key == pygame.K_n:
                self.dialog.active = False
                self.villager_refused = True
                self.dialog.show("Житель", VILLAGER_NO)
                self.save_progress()
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

        if self.level == 1:
            if self._try_read_lore_stone():
                return
            self._try_talk_to_npc()
        else:
            if self._try_open_chest():
                return
            self._try_read_dungeon_lore()

    def _try_use_stairs(self):
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

    def _try_open_chest(self):
        chest = self.dungeon_chest
        if not chest or chest.opened:
            return False
        if not (self.dungeon_boss and self.dungeon_boss.dead):
            return False
        if not self.player.rect.inflate(40, 40).colliderect(chest.rect):
            return False

        chest.opened = True
        self.player.hp = self.player.max_hp
        self.floating_texts.append(FloatingText(
            self.player.x + self.player.w / 2, self.player.y - 10,
            "Сокровище найдено! Полное лечение", (255, 220, 100), duration=2500
        ))
        self.particles.spawn_burst(
            chest.x + chest.w / 2, chest.y + chest.h / 2,
            (255, 220, 100), count=20
        )
        self.save_progress()
        return True

    def _try_read_dungeon_lore(self):
        for stone in self.dungeon_lore_stones:
            if self.player.rect.inflate(40, 40).colliderect(stone.rect):
                self.dialog.show(stone.title, stone.text)
                stone.is_read = True
                self.save_progress()
                return True
        return False

    def _try_read_lore_stone(self):
        for stone in self.lore_stones:
            if self.player.rect.inflate(40, 40).colliderect(stone.rect):
                self.dialog.show(stone.title, stone.text)
                stone.is_read = True

                if not self.lore_reward_given and all(s.is_read for s in self.lore_stones):
                    self.lore_reward_given = True
                    self.player.max_hp += 1
                    self.player.hp = self.player.max_hp
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "Знание предков! +1 Макс. HP", (180, 220, 255), duration=2500
                    ))
                self.save_progress()
                return True
        return False

    def _try_talk_to_npc(self):
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
                    self.save_progress()
                else:
                    self.dialog.show(npc.name, VILLAGER_WAIT)
                return

            n = self.player.crystals
            if n >= self.TOTAL_CRYSTALS and not self.boss_spawned:
                self.world.gate_open = True
                self.boss.dead = False
                self.boss_spawned = True
                self.banner_timer = 3000
                self.dialog.show(npc.name, ELDER_READY)
                self.save_progress()
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
            self._update_level_2(dt)

        self._update_common(dt)

    def _update_level_1(self, dt):
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
                self.save_progress()

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

        if self.key and not self.key.collected:
            self.key.update(dt)
            if self.player.rect.colliderect(self.key.rect):
                self.key.collected = True
                self.has_key = True
                self.floating_texts.append(FloatingText(
                    self.player.x + self.player.w / 2, self.player.y - 10,
                    KEY_MSG, (255, 215, 0)
                ))
                self.save_progress()

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
                    e.x + e.w / 2, e.y - 10, f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
            if not e.dead and e.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10, "-1 HP", (255, 100, 100)
                    ))
            if e.dead:
                self.particles.spawn_burst(e.x + e.w / 2, e.y + e.h / 2, COLOR_SLIME)

        if self.boss and not self.boss.dead:
            self.boss.update(self.player, self.world, dt)
            hb = self.player.get_attack_hitbox()
            if hb and hb.colliderect(self.boss.rect):
                self.boss.take_damage(self.player.damage, self.player.x + self.player.w / 2, self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
                self.camera.add_shake(3)
                self.floating_texts.append(FloatingText(
                    self.boss.x + self.boss.w / 2, self.boss.y - 10, f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
            if not self.boss.dead and self.boss.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10, "-1 HP", (255, 100, 100)
                    ))

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
                    save.delete()
                    self._has_save = False

    def _update_level_2(self, dt):
        self.dungeon.update(dt)

        hb = self.player.get_attack_hitbox()
        for bat in self.dungeon_bats:
            if bat.dead: continue
            bat.update(self.player, self.dungeon, dt)
            if hb and hb.colliderect(bat.rect):
                bat.take_damage(self.player.damage,
                                self.player.x + self.player.w / 2,
                                self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
                hb = None
                self.camera.add_shake(2)
                self.floating_texts.append(FloatingText(
                    bat.x + bat.w / 2, bat.y - 10, f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
            if not bat.dead and bat.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
            if bat.dead:
                self.particles.spawn_burst(bat.x + bat.w / 2, bat.y + bat.h / 2, (80, 60, 120))

        hb = self.player.get_attack_hitbox()
        for sk in self.dungeon_skeletons:
            if sk.dead: continue
            sk.update(self.player, self.dungeon, dt)
            if hb and hb.colliderect(sk.rect):
                sk.take_damage(self.player.damage,
                               self.player.x + self.player.w / 2,
                               self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
                hb = None
                self.camera.add_shake(2)
                self.floating_texts.append(FloatingText(
                    sk.x + sk.w / 2, sk.y - 10, f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
            if not sk.dead and sk.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
            if sk.dead:
                self.particles.spawn_burst(sk.x + sk.w / 2, sk.y + sk.h / 2, (200, 200, 180))

        if self.dungeon_boss and not self.dungeon_boss.dead:
            self.dungeon_boss.update(self.player, self.dungeon, dt,
                                     self.dungeon_projectiles)
            hb = self.player.get_attack_hitbox()
            if hb and hb.colliderect(self.dungeon_boss.rect):
                self.dungeon_boss.take_damage(self.player.damage,
                                              self.player.x + self.player.w / 2,
                                              self.player.y + self.player.h / 2)
                self.player.attack_timer = 0
                self.camera.add_shake(3)
                self.floating_texts.append(FloatingText(
                    self.dungeon_boss.x + self.dungeon_boss.w / 2,
                    self.dungeon_boss.y - 10,
                    f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
            if (not self.dungeon_boss.dead
                    and self.dungeon_boss.rect.colliderect(self.player.rect)):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
            if self.dungeon_boss.dead:
                self.particles.spawn_burst(
                    self.dungeon_boss.x + self.dungeon_boss.w / 2,
                    self.dungeon_boss.y + self.dungeon_boss.h / 2,
                    (240, 200, 80), count=40
                )
                self.camera.add_shake(10)
                self.floating_texts.append(FloatingText(
                    self.dungeon_boss.x + self.dungeon_boss.w / 2,
                    self.dungeon_boss.y - 20,
                    "Король Скелетов пал!", (255, 220, 100), duration=2000
                ))
                self.save_progress()

        for proj in self.dungeon_projectiles:
            if proj.dead: continue
            proj.update(self.dungeon, dt)
            if not proj.dead and proj.rect.colliderect(self.player.rect):
                proj.dead = True
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
        self.dungeon_projectiles = [p for p in self.dungeon_projectiles if not p.dead]

    def _update_common(self, dt):
        for ft in self.floating_texts:
            ft.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if not ft.dead]

        if self.banner_timer > 0:
            self.banner_timer -= dt
            if self.banner_timer < 0:
                self.banner_timer = 0

        if self.player.hp <= 0 and self.state != 'win' and self.win_delay == 0:
            self.state = 'lose'

        self.particles.update(dt)
        self.camera.follow(self.player.x + self.player.w / 2, self.player.y + self.player.h / 2, self.world.w, self.world.h)

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self):
        self.screen.fill(COLOR_SKY)
        if self.state == 'title':
            self._draw_title()
            pygame.display.flip()
            return

        if self.state == 'intro':
            self._draw_intro()
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
        for stone in self.dungeon_lore_stones:
            stone.draw(self.screen, self.camera)
        if self.dungeon_chest:
            self.dungeon_chest.draw(self.screen, self.camera)
        for proj in self.dungeon_projectiles:
            proj.draw(self.screen, self.camera)

        ents = [(b.y + b.h, b) for b in self.dungeon_bats if not b.dead]
        ents += [(s.y + s.h, s) for s in self.dungeon_skeletons if not s.dead]
        if self.dungeon_boss and not self.dungeon_boss.dead:
            ents.append((self.dungeon_boss.y + self.dungeon_boss.h, self.dungeon_boss))
        ents.append((self.player.y + self.player.h, self.player))
        ents.sort(key=lambda p: p[0])

        for _, e in ents:
            if e is self.player:
                self.player.draw(self.screen, self.camera)
            else:
                e.draw(self.screen, self.camera)

    def _draw_hints(self):
        if self.state != 'playing' or self.dialog.active:
            return

        cx = int((self.player.x + self.player.w / 2) // TILE)
        cy = int((self.player.y + self.player.h / 2) // TILE)
        if 0 <= cy < self.world.h and 0 <= cx < self.world.w:
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

        if (self.level == 2
                and self.dungeon_chest
                and not self.dungeon_chest.opened
                and self.dungeon_boss
                and self.dungeon_boss.dead
                and self.player.rect.inflate(40, 40).colliderect(self.dungeon_chest.rect)):
            chest = self.dungeon_chest
            hx = int(chest.x - self.camera.x + chest.w // 2) - self.hint_chest.get_width() // 2
            hy = int(chest.y - self.camera.y) - self.hint_chest.get_height() - 4
            self.screen.blit(self.hint_chest, (hx, hy))

    def _draw_ui(self):
        self.dialog.draw(self.screen)
        self.particles.draw(self.screen, self.camera)

        for ft in self.floating_texts:
            ft.draw(self.screen, self.camera)

        if (self.level == 1
                and self.boss_spawned
                and not self.boss.dead
                and self.banner_timer > 0):
            cx = self.player.x + self.player.w // 2
            cy = self.player.y + self.player.h // 2
            in_castle = (self.CASTLE_X_MIN * TILE <= cx <= self.CASTLE_X_MAX * TILE and
                         self.CASTLE_Y_MIN * TILE <= cy <= self.CASTLE_Y_MAX * TILE)
            if not in_castle:
                # Плавное затухание в последнюю секунду:
                # 3000..1000 мс → alpha 255, 1000..0 мс → 255..0
                fade = min(1.0, self.banner_timer / 1000.0)
                self.banner_text.set_alpha(int(255 * fade))
                self.screen.blit(
                    self.banner_text,
                    (WIDTH // 2 - self.banner_text.get_width() // 2, 70)
                )

        if self.state not in ('win', 'lose', 'paused'):
            self.hud.draw(self.screen, self.player, self.TOTAL_CRYSTALS)

            if self.level == 1:
                self.minimap.draw(self.screen, self)
                if self.villager_met and not self.villager_refused and not self.quest_completed:
                    surf = self.quest_surface_return if self.has_key else self.quest_surface_find
                    self.screen.blit(surf, (20, 60))

        if self.player.hp <= 2 and self.state == 'playing':
            pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 100) + 50
            self.vignette.set_alpha(pulse)
            self.screen.blit(self.vignette, (0, 0))

    def _draw_overlays(self):
        if self.state == 'win':   self._overlay_win()
        if self.state == 'lose':  self._overlay_lose()
        if self.state == 'paused': self._overlay_pause()

    # ============================================================
    #   ЭКРАНЫ
    # ============================================================
    def _draw_intro(self):
        # --- Фон ---
        self.screen.blit(self.overlay_black, (0, 0))

        # --- Заголовок ---
        title = self.font_title_small.render("Хроники Эльдории", True, (240, 210, 130))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        subtitle = self.font_hint_banner.render(
            "Тень над Священным Пламенем", True, (160, 160, 190)
        )
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 140))

        # --- Страница текста ---
        if 0 <= self.intro_page < len(self.intro_pages):
            page = self.intro_pages[self.intro_page]

            # Плавное появление: alpha 0 → 255 за 300 мс
            elapsed = pygame.time.get_ticks() - self.intro_page_changed_at
            alpha = min(255, int(255 * elapsed / 300))
            page.set_alpha(alpha)

            px = WIDTH // 2 - page.get_width() // 2
            py = 280
            self.screen.blit(page, (px, py))

        # --- Индикатор страниц (●○○○) ---
        dots = ""
        for i in range(len(self.intro_pages)):
            dots += "●  " if i == self.intro_page else "○  "
        dots_surf = self.font_title_small.render(dots.strip(), True, (180, 180, 200))
        self.screen.blit(dots_surf, (WIDTH // 2 - dots_surf.get_width() // 2, HEIGHT - 160))

        # --- Подсказки внизу ---
        is_last = self.intro_page >= len(self.intro_pages) - 1
        if is_last:
            hint_text = "[Space] начать игру    [Esc] пропустить"
        else:
            hint_text = "[Space] далее    [Esc] пропустить"
        hint = self.font_hint_banner.render(hint_text, True, (150, 150, 170))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 80))

    def _draw_title(self):
        t = self.font_title_big.render("Хроники Эльдории", True, (240, 210, 130))
        s = self.font_title_small.render("Тень над Священным Пламенем", True, (200, 200, 220))
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 200))
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 280))

        if self._has_save:
            p1 = self.font_title_small.render("Enter — Продолжить", True, (100, 255, 100))
            p2 = self.font_title_small.render("N — Новая игра", True, (255, 200, 100))
            self.screen.blit(p1, (WIDTH // 2 - p1.get_width() // 2, 380))
            self.screen.blit(p2, (WIDTH // 2 - p2.get_width() // 2, 410))
        else:
            p = self.font_title_small.render("Нажми любую клавишу", True, (255, 255, 255))
            self.screen.blit(p, (WIDTH // 2 - p.get_width() // 2, 400))

        for i, line in enumerate([
            "WASD / Стрелки — движение",
            "Space — удар мечом",
            "E — взаимодействие",
            "Собери 3 Кристалла Света, найди Старейшину, победи Морвейна",
        ]):
            txt = self.font_title_small.render(line, True, (180, 180, 200))
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 470 + i * 28))

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
        self.screen.blit(self.pause_text_big, (WIDTH // 2 - self.pause_text_big.get_width() // 2, 180))
        self.screen.blit(self.pause_text_1, (WIDTH // 2 - self.pause_text_1.get_width() // 2, 280))
        self.screen.blit(self.pause_text_save, (WIDTH // 2 - self.pause_text_save.get_width() // 2, 320))
        self.screen.blit(self.pause_text_2, (WIDTH // 2 - self.pause_text_2.get_width() // 2, 360))

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