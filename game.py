"""
game.py — Главный класс игры (Game).

Управляет:
  - Состояниями: 'title' → 'intro' → 'playing' ⇄ 'paused' → 'win'/'lose'
  - Переключением уровней: main_world ⇄ dungeon
  - Обновлением (update): игрок, враги, снаряды, частицы, камера
  - Отрисовкой (draw): тайлы, сущности, HUD, диалоги, оверлеи

Главный цикл — async def run(), потому что Pygbag требует
await asyncio.sleep(0) внутри while (см. ниже).

Используется в main.py:
  - from game import Game (после pygame.display.init())
  - await Game().run() (внутри async def main())

Поиск по файлу: Ctrl+F "region"
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


# region СТРАНИЦЫ ВСТУПЛЕНИЯ
# INTRO разбивается по точкам на отдельные предложения.
# Каждое — одна страница на весь экран.
INTRO_PAGES = [s.strip() + "." for s in INTRO.split(".") if s.strip()]
# endregion


# region КЛАСС: Game
class Game:

    # region КОНСТАНТЫ
    TOTAL_CRYSTALS = 3

    # Смещение подсказки «E — войти» над игроком.
    HINT_OFFSET_Y = 50

    # Границы замка для скрытия баннера «Замок открыт».
    # Внимание: X_MAX=13, Y_MAX=10 (в World — 12 и 9).
    # Сделано намеренно: баннер гаснет чуть раньше, чем игрок
    # входит в замок — чтобы не мешал в бою с боссом.
    CASTLE_X_MIN, CASTLE_X_MAX = 2, 13
    CASTLE_Y_MIN, CASTLE_Y_MAX = 2, 10
    # --- Juice: hit-stop и slow-mo ---
    # Hit-stop замораживает мир на несколько кадров при попадании — удар
    # начинает «чувствоваться». Slow-mo включается только на смерти боссов.
    HIT_STOP_MS = 60            # мс — заморозка на обычном попадании
    HIT_STOP_DEATH_MS = 120     # мс — заморозка на убийстве босса
    SLOWMO_SCALE = 0.3          # начальный time_scale при смерти босса
    SLOWMO_LERP = 1.5           # скорость возврата time_scale к 1.0 (ед/сек)
    # endregion

    # region ИНИЦИАЛИЗАЦИЯ
    def __init__(self):
        # Окно уже создано в main.py (требование Pygbag)
        self.screen = pygame.display.get_surface()
        pygame.display.set_caption("Хроники Эльдории")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 'title'

        self._init_fonts()
        self._init_cached_surfaces()

        # Наличие сохранения проверяется при старте.
        self._has_save = save.exists()

    def _init_fonts(self):
        """Загружает шрифты. При отсутствии файлов — fallback на дефолт."""
        bold_font = "assets/Tiny5-Bold.ttf"
        regular_font = "assets/Tiny5-Regular.ttf"

        try:
            self.font_title_big = pygame.font.Font(bold_font, 64)
            self.font_title_small = pygame.font.Font(regular_font, 32)
            self.font_win_big = pygame.font.Font(bold_font, 64)
            self.font_win_small = pygame.font.Font(regular_font, 32)
            self.font_hint_banner = pygame.font.Font(bold_font, 24)
            self.font_quest = pygame.font.Font(bold_font, 24)
            self.font_intro = pygame.font.Font(regular_font, 32)
        except FileNotFoundError:
            print("Шрифты не найдены, используются стандартные.")
            self.font_title_big = pygame.font.Font(None, 64)
            self.font_title_small = pygame.font.Font(None, 32)
            self.font_win_big = pygame.font.Font(None, 64)
            self.font_win_small = pygame.font.Font(None, 32)
            self.font_hint_banner = pygame.font.Font(None, 24)
            self.font_quest = pygame.font.Font(None, 24)
            self.font_intro = pygame.font.Font(None, 32)

    def _make_quest_surface(self, text):
        """Создаёт Surface для баннера задания (квест Жителя)."""
        q_text = self.font_quest.render(text, True, (255, 200, 100))
        q_w, q_h = q_text.get_width() + 20, q_text.get_height() + 10
        surf = pygame.Surface((q_w, q_h), pygame.SRCALPHA)
        surf.fill((20, 20, 30, 200))
        pygame.draw.rect(surf, (200, 180, 120), (0, 0, q_w, q_h),
                         2, border_radius=5)
        surf.blit(q_text, (10, 5))
        return surf

    def _init_cached_surfaces(self):
        """
        Создаёт все статичные Surface один раз.

        В draw() остаются только blit'ы — это важно для Pygbag/WASM:
        font.render() и pygame.Surface() дороже, чем blit().
        """
        # --- Баннеры заданий (квест Жителя) ---
        self.quest_surface_find = self._make_quest_surface(
            "Задание: Найти ключ жителя"
        )
        self.quest_surface_return = self._make_quest_surface(
            "Задание: Вернуть ключ жителю"
        )

        # --- Баннер «Замок Морвейна открыт» ---
        self.banner_text = self.font_hint_banner.render(
            "Замок Морвейна открыт! На северо-запад!", True, (255, 200, 100)
        )

        # --- Оверлеи (полупрозрачный чёрный / красный) ---
        self.overlay_black = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_black.fill((0, 0, 0, 180))
        self.overlay_red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_red.fill((40, 0, 0, 180))

        # --- Виньетка (красная рамка при низком HP) ---
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(self.vignette, (255, 0, 0),
                         (0, 0, WIDTH, HEIGHT), width=30)

        # --- Тексты экранов ---
        self.win_text_big = self.font_win_big.render(
            "ПОБЕДА!", True, (240, 210, 130)
        )
        self.win_text_small = self.font_win_small.render(
            "Священное Пламя возвращено. Эльдория спасена.",
            True, (220, 220, 240)
        )
        self.win_text_hint = self.font_win_small.render(
            "Нажми R для новой игры", True, (200, 200, 200)
        )

        self.lose_text_big = self.font_win_big.render(
            "ТЫ ПАЛ...", True, (200, 60, 60)
        )
        self.lose_text_small = self.font_win_small.render(
            "Нажми R для повторной попытки", True, (220, 220, 220)
        )

        self.pause_text_big = self.font_win_big.render(
            "ПАУЗА", True, (240, 210, 130)
        )
        self.pause_text_1 = self.font_win_small.render(
            "ESC - продолжить игру", True, (220, 220, 240)
        )
        self.pause_text_save = self.font_win_small.render(
            "F5 - сохранить игру", True, (150, 200, 255)
        )
        self.pause_text_2 = self.font_win_small.render(
            "Q - выйти из игры", True, (200, 200, 200)
        )

        # --- Подсказки взаимодействия (E) ---
        self.hint_enter = self._make_hint("E - войти в подземелье")
        self.hint_exit = self._make_hint("E - выйти на поверхность")
        self.hint_chest = self._make_hint("E - открыть сундук")

        # --- Страницы вступления (уже готовые Surface) ---
        self.intro_pages = [self._wrap_intro_page(p) for p in INTRO_PAGES]

        # --- Текст титульного экрана (кэш) ---
        self.title_big = self.font_title_big.render(
            "Хроники Эльдории", True, (240, 210, 130)
        )
        self.title_sub = self.font_title_small.render(
            "Тень над Священным Пламенем", True, (200, 200, 220)
        )
        self.title_continue = self.font_title_small.render(
            "Enter - Продолжить", True, (100, 255, 100)
        )
        self.title_newgame = self.font_title_small.render(
            "N - Новая игра", True, (255, 200, 100)
        )
        self.title_anykey = self.font_title_small.render(
            "Нажми любую клавишу", True, (255, 255, 255)
        )
        self.title_controls = [
            self.font_title_small.render(line, True, (180, 180, 200))
            for line in [
                "WASD / Стрелки - движение",
                "Space - удар мечом",
                "E - взаимодействие",
                "Собери 3 Кристалла Света, найди Старейшину, победи Морвейна",
            ]
        ]

        # --- Текст экрана вступления (кэш) ---
        self.intro_title = self.font_title_small.render(
            "Хроники Эльдории", True, (240, 210, 130)
        )
        self.intro_sub = self.font_hint_banner.render(
            "Тень над Священным Пламенем", True, (160, 160, 190)
        )
        self.intro_hint_next = self.font_hint_banner.render(
            "[Space] далее    [Esc] пропустить", True, (150, 150, 170)
        )
        self.intro_hint_last = self.font_hint_banner.render(
            "[Space] начать игру    [Esc] пропустить", True, (150, 150, 170)
        )

        # --- Оверлей болота (кэш) ---
        # Зелёный круг вокруг игрока, когда он в болоте.
        # SRCALPHA + alpha в цвете — Pygbag-safe (не используем set_alpha).
        size = PLAYER_SIZE + 16
        self.swamp_overlay = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(
            self.swamp_overlay,
            (50, 80, 50, 110),   # тот же оттенок, что COLOR_SWAMP, но полупрозрачный
            (size // 2, size // 2),
            size // 2
        )

    def _wrap_intro_page(self, text):
        """Рендерит страницу вступления: центрированные строки в Surface."""
        max_w = WIDTH - 200
        words = text.split()

        # --- Разбиение на строки по ширине ---
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
        """Создаёт Surface для подсказки взаимодействия (E)."""
        text_surf = self.font_hint_banner.render(text, True, (255, 255, 150))
        w, h = text_surf.get_width() + 20, text_surf.get_height() + 10
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((20, 20, 30, 200))
        pygame.draw.rect(surf, (200, 200, 100), (0, 0, w, h),
                         1, border_radius=4)
        surf.blit(text_surf, (10, 5))
        return surf
    # endregion

    # region СБРОС И СПАВН
    def _reset(self):
        """Сбрасывает всё состояние игры к началу новой партии."""
        # --- Карты ---
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

        # --- Основные объекты ---
        self.minimap = MiniMap(self.main_world)
        self.particles = ParticleManager()
        self.player = Player(50 * TILE + 7, 65 * TILE + 7)
        self.camera = Camera()
        self.dialog = Dialog()
        self.hud = HUD()

        # --- Коллекции сущностей ---
        self.enemies, self.npcs, self.crystals = [], [], []
        self.potions, self.lore_stones, self.floating_texts = [], [], []
        self.boss = None  # будет создан в _spawn()

        # --- Прогресс ---
        self.boss_spawned = False
        self.win_delay = 0
        self.villager_met = False
        self.villager_refused = False
        self.has_key = False
        self.key = None
        self.quest_completed = False
        self.lore_reward_given = False
        self.banner_timer = 0
        # --- Juice: hit-stop и slow-mo ---
        self.hit_stop = 0
        self.time_scale = 1.0

        # --- Вступление ---
        self.intro_page = 0
        self.intro_page_changed_at = pygame.time.get_ticks()

        # --- Спавн ---
        self._spawn()

    def _spawn(self):
        """Создаёт NPC, кристаллы, врагов, зелья, ключ, камни лора, босса."""
        # --- NPC ---
        self.npcs.append(NPC(48 * TILE, 65 * TILE, "Старейшина"))
        self.npcs.append(NPC(55 * TILE, 48 * TILE, "Житель"))

        # --- Кристаллы + их охрана ---
        # Замечание: некоторые offset'ы выходят за CLEAR_ZONES в map.py —
        # страж может не заспавниться, если там дерево (см. review).
        self._spawn_crystal_and_guards(
            85, 30, "Кристалл Леса",
            [(-3, 2), (0, 2), (3, 2)], hp=2
        )
        self._spawn_crystal_and_guards(
            72, 50, "Кристалл Воды",
            [(-2, -2), (-2, 2), (2, -2), (2, 2)], hp=2
        )
        self._spawn_crystal_and_guards(
            15, 40, "Кристалл Руин",
            [(-3, 2), (0, 2), (3, 2)], hp=3
        )

        # --- Босс (создаётся «мёртвым», активируется в диалоге) ---
        self.boss = Boss(7 * TILE, 5 * TILE)

        # --- Случайные слизни по карте (детерминированно) ---
        rng = random.Random(99)
        for _ in range(30):
            tx = rng.randint(5, self.world.w - 5)
            ty = rng.randint(5, self.world.h - 5)
            # Не спавним рядом со стартом (|tx-50| + |ty-65| > 10)
            if self.world.tiles[ty][tx] == GRASS and abs(tx - 50) + abs(ty - 65) > 10:
                self.enemies.append(Slime(tx * TILE, ty * TILE))

        # --- Зелья в фиксированных точках ---
        potion_positions = [(51, 63), (84, 32), (16, 42), (7, 11), (72, 48)]
        for tx, ty in potion_positions:
            if self.world.tiles[ty][tx] == GRASS:
                self.potions.append(Potion(tx * TILE, ty * TILE))

        # --- Ключ в зоне KEY_ZONE (случайная точка) ---
        # random.Random() без seed — каждый раз новое место.
        # Игрок должен исследовать лес, а не запоминать точку.
        rng_key = random.Random()
        for _ in range(100):
            tx = rng_key.randint(KEY_ZONE_X_MIN, KEY_ZONE_X_MAX)
            ty = rng_key.randint(KEY_ZONE_Y_MIN, KEY_ZONE_Y_MAX)
            if self.world.tiles[ty][tx] == GRASS:
                self.key = Key(tx * TILE, ty * TILE)
                break
        else:
            # Fallback: если за 100 попыток не нашли траву — ставим рядом с кристаллом леса.
            self.key = Key(85 * TILE, 30 * TILE)

        # --- Камни лора (5 штук на карте) ---
        self.lore_stones.append(
            LoreStone(53 * TILE, 63 * TILE, "Древний камень", LORE_START)
        )
        self.lore_stones.append(
            LoreStone(14 * TILE, 40 * TILE, "Камень Аэтельгарда", LORE_RUINS)
        )
        self.lore_stones.append(
            LoreStone(71 * TILE, 50 * TILE, "Камень Озера", LORE_LAKE)
        )
        self.lore_stones.append(
            LoreStone(58 * TILE, 50 * TILE, "Камень деревни", LORE_VILLAGE)
        )
        self.lore_stones.append(
            LoreStone(6 * TILE, 12 * TILE, "Камень у врат", LORE_CASTLE)
        )

    def _spawn_crystal_and_guards(self, cx, cy, name, offsets, hp):
        """
        Создаёт кристалл и слизней-охранников в заданных смещениях.

        Если тайл охранника не GRASS (дерево/стена), страж не спавнится.
        Это может привести к «неполной охране», если offset выходит
        за CLEAR_ZONES в map.py.
        """
        self.crystals.append(Crystal(cx * TILE, cy * TILE, name))
        for dx, dy in offsets:
            tx, ty = cx + dx, cy + dy
            if self.world.tiles[ty][tx] == GRASS:
                self.enemies.append(Slime(tx * TILE, ty * TILE, hp=hp))
    # endregion

    # region ПЕРЕКЛЮЧЕНИЕ УРОВНЕЙ
    @property
    def world(self):
        """Текущая карта (main_world или dungeon)."""
        return self.current_map

    def _ensure_dungeon(self):
        """Ленивая инициализация подземелья и его сущностей."""
        if self.dungeon is None:
            self.dungeon = Dungeon()

        # --- Мыши (создаются один раз) ---
        if not self.dungeon_bats:
            bat_positions = [(8, 8), (13, 13), (18, 8), (23, 18), (33, 13)]
            for tx, ty in bat_positions:
                px = tx * TILE + TILE // 2
                py = ty * TILE + TILE // 2
                if self.dungeon.is_walkable_px(px, py):
                    self.dungeon_bats.append(Bat(tx * TILE, ty * TILE))

        # --- Сундук (один) ---
        if self.dungeon_chest is None:
            self.dungeon_chest = Chest(35 * TILE, 4 * TILE)

        # --- Скелеты ---
        if not self.dungeon_skeletons:
            skeleton_positions = [(31, 11), (39, 11), (31, 15), (39, 15)]
            for tx, ty in skeleton_positions:
                px = tx * TILE + TILE // 2
                py = ty * TILE + TILE // 2
                if self.dungeon.is_walkable_px(px, py):
                    self.dungeon_skeletons.append(Skeleton(tx * TILE, ty * TILE))

        # --- Король Скелетов ---
        if self.dungeon_boss is None:
            self.dungeon_boss = SkeletonKing(35 * TILE, 7 * TILE)

        # --- Камни лора в подземелье ---
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
        """Переход в подземелье (с сохранением позиции на поверхности)."""
        self._ensure_dungeon()
        self.saved_position = (self.player.x, self.player.y)
        self.current_map = self.dungeon
        self.level = 2
        # Спавн у лестницы: (6, h-4) — рядом с STAIRS_UP в (4, h-4)
        self.player.x = 6 * TILE + 7
        self.player.y = (self.dungeon.h - 4) * TILE + 7
        self.camera = Camera()
        self.particles = ParticleManager()
        self.floating_texts = []
        self.dungeon_projectiles = []
        self.save_progress()

    def exit_dungeon(self):
        """Возврат на поверхность (в точку входа)."""
        self.current_map = self.main_world
        self.level = 1
        if self.saved_position:
            self.player.x, self.player.y = self.saved_position
        self.camera = Camera()
        self.particles = ParticleManager()
        self.floating_texts = []
        self.dungeon_projectiles = []
        self.save_progress()
    # endregion

    # region СОХРАНЕНИЕ / ЗАГРУЗКА
    def save_progress(self):
        """
        Сохраняет текущее состояние.

        Не сохраняет, если:
          - игрок ещё не создан (вызов до _reset)
          - состояние не 'playing' / 'paused' (на титуле, вступлении,
            win/lose сохранять нечего)
        """
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
                # win_delay: если сохранились в 1500-мс окне между смертью
                # босса и переходом в state='win', при загрузке эффект
                # смерти не повторится (иначе частицы спавнились бы заново).
                'win_delay': self.win_delay,
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
                # Позиция сохраняется: иначе при загрузке посреди боя
                # босс «телепортировался» бы на арену у (7, 5).
                # Защита от «босс на игроке» — в load_progress, после
                # того как позиция игрока уже установлена (порядок важен:
                # в load_progress секция босса идёт ДО позиции игрока).
                'x': self.boss.x if self.boss else 0.0,
                'y': self.boss.y if self.boss else 0.0,
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
        """Загружает сохранение. Если его нет — просто _reset()."""
        data = save.read()
        if not data:
            self._reset()
            return

        # Сброс в дефолтное состояние, затем поверх накатываем сохранение.
        self._reset()

        # --- Игрок ---
        p = data.get('player', {})
        self.player.max_hp = max(1, int(p.get('max_hp', self.player.max_hp)))
        self.player.hp = max(1, min(self.player.max_hp,
                                    int(p.get('hp', self.player.max_hp))))
        self.player.damage = int(p.get('damage', 1))
        self.player.weapon_upgraded = bool(p.get('weapon_upgraded', False))
        self.player.crystals = int(p.get('crystals', 0))

        # --- Прогресс квестов ---
        pr = data.get('progress', {})
        self.boss_spawned = bool(pr.get('boss_spawned', False))
        self.villager_met = bool(pr.get('villager_met', False))
        self.villager_refused = bool(pr.get('villager_refused', False))
        self.has_key = bool(pr.get('has_key', False))
        self.quest_completed = bool(pr.get('quest_completed', False))
        self.lore_reward_given = bool(pr.get('lore_reward_given', False))
        self.win_delay = float(pr.get('win_delay', 0))

        # Защита: win_delay > 0 имеет смысл только если босс уже мёртв.
        # ВАЖНО: проверяем dead из save-данных напрямую, а не
        # self.boss.dead — секция босса загружается НИЖЕ, и на этом
        # этапе self.boss.dead ещё дефолтный (True из Boss.__init__),
        # из-за чего проверка «not self.boss.dead» никогда не сработала
        # бы. См. историю правок.
        _boss_dead_in_save = bool(data.get('boss', {}).get('dead', True))
        if self.win_delay > 0 and not _boss_dead_in_save:
            self.win_delay = 0

        # --- Мир ---
        w = data.get('world', {})
        self.main_world.gate_open = bool(w.get('gate_open', False))

        # Ключ (позиция + собран ли)
        kd = w.get('key', {})
        if self.key:
            if kd.get('collected', False):
                self.key.collected = True
            else:
                self.key.x = kd.get('x', self.key.x)
                self.key.y = kd.get('y', self.key.y)

        # Мёртвые враги / собранное / прочитанное
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

        # --- Босс ---
        b = data.get('boss', {})
        if self.boss:
            # Позиция — восстанавливаем ДО проверки «босс на игроке»
            # (она будет в самом конце функции, после позиции игрока).
            self.boss.x = float(b.get('x', self.boss.x))
            self.boss.y = float(b.get('y', self.boss.y))
            self.boss.dead = bool(b.get('dead', True))
            self.boss.hp = int(b.get('hp', self.boss.max_hp))
            self.boss.phase = b.get('phase', 'idle')
            self.boss.charge_timer = float(b.get('charge_timer', 3.0))
            self.boss.windup_timer = float(b.get('windup_timer', 0.0))
            # Если сохранились в момент charge/windup — при загрузке
            # босс «спокойно стоит», у игрока есть 1 сек на реакцию.
            if self.boss.phase in ('charge', 'windup'):
                self.boss.phase = 'idle'
                self.boss.charge_timer = 1.0

        # --- Подземелье ---
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

        # --- Позиция игрока и уровень ---
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

        # --- Защита от «босс на игроке» ---
        # Если сохранённая позиция босса оказалась вплотную к игроку
        # (например, сохранились в момент, когда босс настиг игрока
        # вплотную), после загрузки игрок мгновенно получил бы удар
        # без шанса среагировать. Отодвигаем босса на безопасное
        # расстояние. Проверка ПОСЛЕ установки позиции игрока —
        # иначе сравнение было бы некорректным.
        if (self.level == 1
                and self.boss
                and not self.boss.dead
                and self.boss_spawned):
            dx = self.boss.x - self.player.x
            dy = self.boss.y - self.player.y
            dist = (dx * dx + dy * dy) ** 0.5
            safe_dist = 150.0   # ~3.75 тайла — босс не достанет одним ударом
            if dist < safe_dist:
                if dist < 0.01:
                    # Босс и игрок в одной точке — отодвигаем вправо
                    dx, dy, dist = 1.0, 0.0, 1.0
                nx = self.player.x + dx / dist * safe_dist
                ny = self.player.y + dy / dist * safe_dist
                if self.world.is_walkable_rect(
                        nx, ny, self.boss.w, self.boss.h):
                    self.boss.x, self.boss.y = nx, ny
                else:
                    # Новая позиция не проходима — возвращаем на арену
                    self.boss.x = 7 * TILE
                    self.boss.y = 5 * TILE
                # Сбрасываем рывок, чтобы не «достал» игрока сразу после
                # отодвигания.
                self.boss.phase = 'idle'
                self.boss.charge_timer = 1.0
    # endregion

    # region СОБЫТИЯ
    def handle_events(self):
        """Обрабатывает события Pygame (QUIT, KEYDOWN)."""
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.save_progress()
                self.running = False
            elif e.type == pygame.KEYDOWN:
                self._handle_keydown(e.key)

    def _handle_keydown(self, key):
        """Диспетчеризация нажатий клавиш по состояниям."""
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
                # Прочие клавиши игнорируются
            else:
                # Нет сохранения — любая клавиша начинает новую игру
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
                # Пропустить вступление
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

        # --- Диалог (перехватывает ввод) ---
        if self.dialog.active:
            self._handle_dialog_input(key)
            return

        # --- Пауза (ESC в игре → пауза; ESC в паузе → игра) ---
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

        # --- Ручное сохранение (F5 в игре) ---
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
        """Обрабатывает ввод во время открытого диалога."""
        if self.dialog.is_choice:
            # --- Выбор [Y] / [N] ---
            # Esc во время выбора не обрабатывается осознанно —
            # игрок обязан выбрать Y или N.
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
            # --- Обычный диалог: Space / Enter — листать, Esc — закрыть ---
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.dialog.next_page()
            elif key == pygame.K_ESCAPE:
                self.dialog.active = False
    # endregion

    # region ВЗАИМОДЕЙСТВИЕ (E)
    def _interact(self):
        """Диспетчер взаимодействий по клавише E."""
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
        """Использовать лестницу (вход/выход из подземелья)."""
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
        """Открыть сундук (только после смерти Короля Скелетов)."""
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
        """Прочитать камень лора в подземелье."""
        for stone in self.dungeon_lore_stones:
            if self.player.rect.inflate(40, 40).colliderect(stone.rect):
                self.dialog.show(stone.title, stone.text)
                stone.is_read = True
                self.save_progress()
                return True
        return False

    def _try_read_lore_stone(self):
        """Прочитать камень лора на поверхности (+1 макс. HP за все 5)."""
        for stone in self.lore_stones:
            if self.player.rect.inflate(40, 40).colliderect(stone.rect):
                self.dialog.show(stone.title, stone.text)
                stone.is_read = True

                # Награда за все 5 камней — один раз
                if (not self.lore_reward_given
                        and all(s.is_read for s in self.lore_stones)):
                    self.lore_reward_given = True
                    self.player.max_hp += 1
                    self.player.hp = self.player.max_hp
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "Знание предков! +1 Макс. HP",
                        (180, 220, 255), duration=2500
                    ))
                self.save_progress()
                return True
        return False

    def _try_talk_to_npc(self):
        """Поговорить с NPC (Житель или Старейшина)."""
        for npc in self.npcs:
            if not self.player.rect.inflate(40, 40).colliderect(npc.rect):
                continue

            # --- Житель ---
            if npc.name == "Житель":
                if self.villager_refused:
                    return  # отказал — NPC больше не заговорит
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

            # --- Старейшина (главный квест) ---
            n = self.player.crystals
            if n >= self.TOTAL_CRYSTALS and not self.boss_spawned:
                # Собраны все кристаллы → открываем врата, активируем босса
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
    # endregion

    # region ЛОГИКА (UPDATE)
    def update(self, dt):
        """
        Обновляет состояние, если игра не на паузе и не в диалоге.

        Слой juice:
          - time_scale (slow-mo) плавно возвращается к 1.0 каждый кадр.
          - При hit_stop > 0 игровой мир замирает, но time_scale
            продолжает тикать (чтобы после заморозки не было рывка).
        """
        if self.state != 'playing' or self.dialog.active:
            return

        # --- Slow-mo: плавный возврат time_scale к 1.0 ---
        # Работает и во время hit-stop — bookkeeping, не влияет на картинку.
        if self.time_scale < 1.0:
            self.time_scale = min(
                1.0, self.time_scale + dt * self.SLOWMO_LERP / 1000.0
            )

        # --- Hit-stop: заморозка мира ---
        # handle_events() и draw() продолжают работать — только update мира
        # пропускается. dt_eff здесь не нужен: таймер hit_stop идёт
        # в реальном времени, а не в игровом.
        if self.hit_stop > 0:
            self.hit_stop = max(0, self.hit_stop - dt)
            return

        # --- Игровое время с учётом slow-mo ---
        dt_eff = dt * self.time_scale

        self.player.update(pygame.key.get_pressed(), dt_eff, self.world)

        if self.level == 1:
            self._update_level_1(dt_eff)
        else:
            self._update_level_2(dt_eff)

        self._update_common(dt_eff)

    def _update_level_1(self, dt):
        """Обновление уровня 1: кристаллы, зелья, ключ, враги, босс."""
        # --- Кристаллы ---
        for c in self.crystals:
            if c.collected:
                continue
            c.update(dt)
            if self.player.rect.colliderect(c.rect):
                c.collected = True
                self.player.crystals += 1
                self.floating_texts.append(FloatingText(
                    self.player.x + self.player.w / 2, self.player.y - 10,
                    CRYSTAL_MSG, (200, 240, 255)
                ))
                self.save_progress()

        # --- Зелья (только если HP не полное) ---
        for p in self.potions:
            if p.collected:
                continue
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
                self.save_progress()

        # --- Враги (слизни) ---
        hb = self.player.get_attack_hitbox()
        for e in self.enemies:
            if e.dead:
                continue
            e.update(self.player, self.world, dt)
            if hb and hb.colliderect(e.rect):
                e.take_damage(
                    self.player.damage,
                    self.player.x + self.player.w / 2,
                    self.player.y + self.player.h / 2
                )
                self.player.attack_timer = 0  # один удар — один враг
                hb = None
                self.camera.add_shake(2)
                self.floating_texts.append(FloatingText(
                    e.x + e.w / 2, e.y - 10,
                    f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
                # Hit-stop только на нелетальном ударе. На убийстве
                # заморозка не нужна — смерть и так заметна.
                if not e.dead:
                    self.hit_stop = self.HIT_STOP_MS

            if not e.dead and e.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
            if e.dead:
                self.particles.spawn_burst(
                    e.x + e.w / 2, e.y + e.h / 2, COLOR_SLIME
                )

        # --- Босс ---
        if self.boss and not self.boss.dead:
            self.boss.update(self.player, self.world, dt)
            hb = self.player.get_attack_hitbox()
            if hb and hb.colliderect(self.boss.rect):
                self.boss.take_damage(
                    self.player.damage,
                    self.player.x + self.player.w / 2,
                    self.player.y + self.player.h / 2
                )
                self.player.attack_timer = 0
                self.camera.add_shake(3)
                self.floating_texts.append(FloatingText(
                    self.boss.x + self.boss.w / 2, self.boss.y - 10,
                    f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
                if not self.boss.dead:
                    self.hit_stop = self.HIT_STOP_MS
            if not self.boss.dead and self.boss.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))

        # --- Смерть босса → win через 1.5 сек ---
        if self.boss and self.boss.dead and self.boss_spawned:
            if self.win_delay == 0:
                # Первый кадр после смерти — эффект + hit-stop + slow-mo
                self.particles.spawn_burst(
                    self.boss.x + self.boss.w / 2,
                    self.boss.y + self.boss.h / 2,
                    COLOR_BOSS, count=40
                )
                self.camera.add_shake(10)
                self.floating_texts.append(FloatingText(
                    self.boss.x + self.boss.w / 2, self.boss.y - 10,
                    "МОРВЕЙН ПАЛ!", (255, 220, 100), duration=1500
                ))
                # Death hit-stop: длиннее обычного, чтобы удар «запомнился»,
                # затем slow-mo. win_delay стартует после заморозки.
                self.hit_stop = self.HIT_STOP_DEATH_MS
                self.time_scale = self.SLOWMO_SCALE
                self.win_delay = 1
            else:
                self.win_delay += dt
                if self.win_delay >= 1500:
                    self.state = 'win'
                    save.delete()
                    self._has_save = False

    def _update_level_2(self, dt):
        """Обновление уровня 2: подземелье, мыши, скелеты, босс, снаряды."""
        self.dungeon.update(dt)

        # --- Мыши ---
        hb = self.player.get_attack_hitbox()
        for bat in self.dungeon_bats:
            if bat.dead:
                continue
            bat.update(self.player, self.dungeon, dt)
            if hb and hb.colliderect(bat.rect):
                bat.take_damage(
                    self.player.damage,
                    self.player.x + self.player.w / 2,
                    self.player.y + self.player.h / 2
                )
                self.player.attack_timer = 0
                hb = None
                self.camera.add_shake(2)
                self.floating_texts.append(FloatingText(
                    bat.x + bat.w / 2, bat.y - 10,
                    f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
                if not bat.dead:
                    self.hit_stop = self.HIT_STOP_MS
            if not bat.dead and bat.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
            if bat.dead:
                self.particles.spawn_burst(
                    bat.x + bat.w / 2, bat.y + bat.h / 2, (80, 60, 120)
                )

        # --- Скелеты ---
        hb = self.player.get_attack_hitbox()
        for sk in self.dungeon_skeletons:
            if sk.dead:
                continue
            sk.update(self.player, self.dungeon, dt)
            if hb and hb.colliderect(sk.rect):
                sk.take_damage(
                    self.player.damage,
                    self.player.x + self.player.w / 2,
                    self.player.y + self.player.h / 2
                )
                self.player.attack_timer = 0
                hb = None
                self.camera.add_shake(2)
                self.floating_texts.append(FloatingText(
                    sk.x + sk.w / 2, sk.y - 10,
                    f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
                if not sk.dead:
                    self.hit_stop = self.HIT_STOP_MS
            if not sk.dead and sk.rect.colliderect(self.player.rect):
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
            if sk.dead:
                self.particles.spawn_burst(
                    sk.x + sk.w / 2, sk.y + sk.h / 2, (200, 200, 180)
                )

        # --- Король Скелетов ---
        if self.dungeon_boss and not self.dungeon_boss.dead:
            self.dungeon_boss.update(
                self.player, self.dungeon, dt, self.dungeon_projectiles
            )
            hb = self.player.get_attack_hitbox()
            if hb and hb.colliderect(self.dungeon_boss.rect):
                self.dungeon_boss.take_damage(
                    self.player.damage,
                    self.player.x + self.player.w / 2,
                    self.player.y + self.player.h / 2
                )
                self.player.attack_timer = 0
                self.camera.add_shake(3)
                self.floating_texts.append(FloatingText(
                    self.dungeon_boss.x + self.dungeon_boss.w / 2,
                    self.dungeon_boss.y - 10,
                    f"-{self.player.damage}", (255, 255, 100), duration=600
                ))
                if not self.dungeon_boss.dead:
                    self.hit_stop = self.HIT_STOP_MS
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
                # Death hit-stop + slow-mo — как у Морвейна,
                # но без перехода в state='win' (босс подземелья).
                self.hit_stop = self.HIT_STOP_DEATH_MS
                self.time_scale = self.SLOWMO_SCALE
                self.save_progress()

        # --- Снаряды босса ---
        for proj in self.dungeon_projectiles:
            if proj.dead:
                continue
            proj.update(self.dungeon, dt)
            if not proj.dead and proj.rect.colliderect(self.player.rect):
                proj.dead = True
                if self.player.take_damage(1):
                    self.camera.add_shake(5)
                    self.floating_texts.append(FloatingText(
                        self.player.x + self.player.w / 2, self.player.y - 10,
                        "-1 HP", (255, 100, 100)
                    ))
        # Убираем мёртвые снаряды
        self.dungeon_projectiles = [
            p for p in self.dungeon_projectiles if not p.dead
        ]

    def _update_common(self, dt):
        """Обновление, общее для обоих уровней."""
        # --- Всплывающие тексты ---
        for ft in self.floating_texts:
            ft.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if not ft.dead]

        # --- Баннер «Замок открыт» ---
        if self.banner_timer > 0:
            self.banner_timer -= dt
            if self.banner_timer < 0:
                self.banner_timer = 0

        # --- Проверка поражения ---
        # win_delay > 0 — босс только что умер, не переключаем в lose.
        if self.player.hp <= 0 and self.state != 'win' and self.win_delay == 0:
            self.state = 'lose'

        # --- Частицы и камера ---
        self.particles.update(dt)
        self.camera.follow(
            self.player.x + self.player.w / 2,
            self.player.y + self.player.h / 2,
            self.world.w, self.world.h,
            dt  # ← передаём dt: тряска затухает frame-independent
        )
    # endregion

    # region ОТРИСОВКА
    def draw(self):
        """Главный метод отрисовки: диспетчеризация по состоянию."""
        self.screen.fill(COLOR_SKY)

        if self.state == 'title':
            self._draw_title()
            pygame.display.flip()
            return

        if self.state == 'intro':
            self._draw_intro()
            pygame.display.flip()
            return

        # --- Игровой мир ---
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
        """Отрисовка сущностей уровня 1 (с сортировкой по Y)."""
        for stone in self.lore_stones:
            stone.draw(self.screen, self.camera)
        for c in self.crystals:
            c.draw(self.screen, self.camera)
        if self.key and not self.key.collected:
            self.key.draw(self.screen, self.camera)
        for p in self.potions:
            p.draw(self.screen, self.camera)
        for n in self.npcs:
            n.draw(self.screen, self.camera)

        # Сортировка по y + h: дальние (выше) — рисуются первыми
        ents = [(e.y + e.h, e) for e in self.enemies if not e.dead]
        if self.boss and not self.boss.dead:
            ents.append((self.boss.y + self.boss.h, self.boss))
        ents.append((self.player.y + self.player.h, self.player))
        ents.sort(key=lambda p: p[0])

        for _, e in ents:
            if e is self.player:
                # Оверлей болота рисуется ПОД игроком,
                # чтобы мигание при invuln не оставляло «пустую ауру».
                self._draw_swamp_effect()
                self.player.draw(self.screen, self.camera)
            elif e is self.boss:
                self.boss.draw(self.screen, self.camera)
            else:
                e.draw(self.screen, self.camera)

    def _draw_swamp_effect(self):
        """
        Зелёный ореол вокруг игрока, если он стоит на тайле болота.

        Проверяем тайл под ЦЕНТРОМ игрока — та же логика, что
        в player.py (замедление скорости). Это гарантирует,
        что «вязнет» и визуально, и по скорости одновременно.
        """
        cx = self.player.x + self.player.w / 2
        cy = self.player.y + self.player.h / 2
        tx, ty = int(cx // TILE), int(cy // TILE)

        # Защита от выхода за границы карты
        if not (0 <= ty < self.world.h and 0 <= tx < self.world.w):
            return

        if self.world.tiles[ty][tx] != SWAMP:
            return

        # Смещение: оверлей на 8 px больше игрока с каждой стороны
        ox = int(self.player.x - self.camera.x) - 8
        oy = int(self.player.y - self.camera.y) - 8
        self.screen.blit(self.swamp_overlay, (ox, oy))

    def _draw_level_2(self):
        """Отрисовка сущностей уровня 2."""
        for stone in self.dungeon_lore_stones:
            stone.draw(self.screen, self.camera)
        if self.dungeon_chest:
            self.dungeon_chest.draw(self.screen, self.camera)
        for proj in self.dungeon_projectiles:
            proj.draw(self.screen, self.camera)

        ents = [(b.y + b.h, b) for b in self.dungeon_bats if not b.dead]
        ents += [(s.y + s.h, s) for s in self.dungeon_skeletons if not s.dead]
        if self.dungeon_boss and not self.dungeon_boss.dead:
            ents.append((
                self.dungeon_boss.y + self.dungeon_boss.h,
                self.dungeon_boss
            ))
        ents.append((self.player.y + self.player.h, self.player))
        ents.sort(key=lambda p: p[0])

        for _, e in ents:
            if e is self.player:
                self.player.draw(self.screen, self.camera)
            else:
                e.draw(self.screen, self.camera)

    def _draw_hints(self):
        """Подсказки над игроком (E — войти/выйти, E — сундук)."""
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
                hx = (int(self.player.x - self.camera.x + self.player.w / 2)
                      - hint.get_width() // 2)
                hy = int(self.player.y - self.camera.y) - self.HINT_OFFSET_Y
                self.screen.blit(hint, (hx, hy))

        # --- Подсказка сундука (только после босса) ---
        if (self.level == 2
                and self.dungeon_chest
                and not self.dungeon_chest.opened
                and self.dungeon_boss
                and self.dungeon_boss.dead
                and self.player.rect.inflate(40, 40).colliderect(
                    self.dungeon_chest.rect)):
            chest = self.dungeon_chest
            hx = (int(chest.x - self.camera.x + chest.w // 2)
                  - self.hint_chest.get_width() // 2)
            hy = (int(chest.y - self.camera.y)
                  - self.hint_chest.get_height() - 4)
            self.screen.blit(self.hint_chest, (hx, hy))

    def _draw_ui(self):
        """HUD, диалог, частицы, всплывающие тексты, баннер, виньетка."""
        self.dialog.draw(self.screen)
        self.particles.draw(self.screen, self.camera)

        for ft in self.floating_texts:
            ft.draw(self.screen, self.camera)

        # --- Баннер «Замок Морвейна открыт» (исчезает, если игрок в замке) ---
        if (self.level == 1
                and self.boss_spawned
                and not self.boss.dead
                and self.banner_timer > 0):
            cx = self.player.x + self.player.w // 2
            cy = self.player.y + self.player.h // 2
            in_castle = (
                self.CASTLE_X_MIN * TILE <= cx <= self.CASTLE_X_MAX * TILE
                and self.CASTLE_Y_MIN * TILE <= cy <= self.CASTLE_Y_MAX * TILE
            )
            if not in_castle:
                # Плавное затухание: последние 1000 мс alpha 255 → 0.
                # set_alpha вызывается каждый кадр заново, поэтому
                # мутация кэшированного Surface безопасна — значение
                # пересчитывается из banner_timer.
                fade = min(1.0, self.banner_timer / 1000.0)
                self.banner_text.set_alpha(int(255 * fade))
                self.screen.blit(
                    self.banner_text,
                    (WIDTH // 2 - self.banner_text.get_width() // 2, 70)
                )

        # --- HUD (только в игре, не в win/lose/paused) ---
        if self.state not in ('win', 'lose', 'paused'):
            self.hud.draw(self.screen, self.player, self.TOTAL_CRYSTALS)

            if self.level == 1:
                self.minimap.draw(self.screen, self)
                # Баннер квеста Жителя (слева)
                if (self.villager_met
                        and not self.villager_refused
                        and not self.quest_completed):
                    surf = (self.quest_surface_return
                            if self.has_key else self.quest_surface_find)
                    self.screen.blit(surf, (20, 60))

        # --- Виньетка при низком HP (пульсирует) ---
        if self.player.hp <= 2 and self.state == 'playing':
            pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 100) + 50
            self.vignette.set_alpha(pulse)
            self.screen.blit(self.vignette, (0, 0))

    def _draw_overlays(self):
        """Полноэкранные оверлеи (win/lose/paused) поверх всего."""
        if self.state == 'win':
            self._overlay_win()
        if self.state == 'lose':
            self._overlay_lose()
        if self.state == 'paused':
            self._overlay_pause()
    # endregion

    # region ЭКРАНЫ (title / intro / win / lose / paused)
    def _draw_intro(self):
        """Экран вступления: фон, заголовок, страница, индикатор, подсказки."""
        # --- Фон ---
        self.screen.blit(self.overlay_black, (0, 0))

        # --- Заголовок (из кэша) ---
        self.screen.blit(
            self.intro_title,
            (WIDTH // 2 - self.intro_title.get_width() // 2, 100)
        )
        self.screen.blit(
            self.intro_sub,
            (WIDTH // 2 - self.intro_sub.get_width() // 2, 140)
        )

        # --- Страница текста (плавное появление 0 → 255 за 300 мс) ---
        if 0 <= self.intro_page < len(self.intro_pages):
            page = self.intro_pages[self.intro_page]

            elapsed = pygame.time.get_ticks() - self.intro_page_changed_at
            alpha = min(255, int(255 * elapsed / 300))
            page.set_alpha(alpha)

            px = WIDTH // 2 - page.get_width() // 2
            py = 280
            self.screen.blit(page, (px, py))

        # --- Индикатор страниц ([X] [ ] [ ]) ---
        dots = ""
        for i in range(len(self.intro_pages)):
            dots += "[X] " if i == self.intro_page else "[ ] "
        dots_surf = self.font_title_small.render(
            dots.strip(), True, (180, 180, 200)
        )
        self.screen.blit(
            dots_surf,
            (WIDTH // 2 - dots_surf.get_width() // 2, HEIGHT - 160)
        )

        # --- Подсказки внизу (из кэша) ---
        is_last = self.intro_page >= len(self.intro_pages) - 1
        hint = self.intro_hint_last if is_last else self.intro_hint_next
        self.screen.blit(
            hint,
            (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 80)
        )

    def _draw_title(self):
        """Титульный экран (все тексты — из кэша)."""
        self.screen.blit(
            self.title_big,
            (WIDTH // 2 - self.title_big.get_width() // 2, 200)
        )
        self.screen.blit(
            self.title_sub,
            (WIDTH // 2 - self.title_sub.get_width() // 2, 280)
        )

        if self._has_save:
            self.screen.blit(
                self.title_continue,
                (WIDTH // 2 - self.title_continue.get_width() // 2, 380)
            )
            self.screen.blit(
                self.title_newgame,
                (WIDTH // 2 - self.title_newgame.get_width() // 2, 410)
            )
        else:
            self.screen.blit(
                self.title_anykey,
                (WIDTH // 2 - self.title_anykey.get_width() // 2, 400)
            )

        # --- Управление (из кэша) ---
        for i, txt in enumerate(self.title_controls):
            self.screen.blit(
                txt,
                (WIDTH // 2 - txt.get_width() // 2, 470 + i * 28)
            )

    def _overlay_win(self):
        """Экран победы."""
        self.screen.blit(self.overlay_black, (0, 0))
        self.screen.blit(
            self.win_text_big,
            (WIDTH // 2 - self.win_text_big.get_width() // 2, 220)
        )
        self.screen.blit(
            self.win_text_small,
            (WIDTH // 2 - self.win_text_small.get_width() // 2, 310)
        )
        self.screen.blit(
            self.win_text_hint,
            (WIDTH // 2 - self.win_text_hint.get_width() // 2, 400)
        )

    def _overlay_lose(self):
        """Экран поражения."""
        self.screen.blit(self.overlay_red, (0, 0))
        self.screen.blit(
            self.lose_text_big,
            (WIDTH // 2 - self.lose_text_big.get_width() // 2, 250)
        )
        self.screen.blit(
            self.lose_text_small,
            (WIDTH // 2 - self.lose_text_small.get_width() // 2, 350)
        )

    def _overlay_pause(self):
        """Экран паузы."""
        self.screen.blit(self.overlay_black, (0, 0))
        self.screen.blit(
            self.pause_text_big,
            (WIDTH // 2 - self.pause_text_big.get_width() // 2, 180)
        )
        self.screen.blit(
            self.pause_text_1,
            (WIDTH // 2 - self.pause_text_1.get_width() // 2, 280)
        )
        self.screen.blit(
            self.pause_text_save,
            (WIDTH // 2 - self.pause_text_save.get_width() // 2, 320)
        )
        self.screen.blit(
            self.pause_text_2,
            (WIDTH // 2 - self.pause_text_2.get_width() // 2, 360)
        )
    # endregion

    # region ГЛАВНЫЙ ЦИКЛ
    async def run(self):
        """
        Главный цикл. Async, потому что Pygbag требует
        await asyncio.sleep(0) внутри while — иначе браузер зависнет.
        """
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)
        pygame.quit()
    # endregion
# endregion (Game)