# ============================================================
#   settings.py — все константы игры.
# ============================================================

# region РАЗМЕРЫ И ТАЙМИНГИ
WIDTH, HEIGHT = 960, 640
FPS = 60
TILE = 40
# endregion

# region ИГРОК
PLAYER_SPEED         = 4
PLAYER_SIZE          = 26
PLAYER_MAX_HP        = 6
PLAYER_ATTACK_COOLDOWN = 350
PLAYER_ATTACK_DURATION = 150
PLAYER_ATTACK_RANGE    = 36
PLAYER_ATTACK_DAMAGE   = 1
PLAYER_INVULN_TIME     = 800
# endregion

# region ТАЙЛЫ
GRASS, TREE, WATER, STONE, FLOOR, DARK_FLOOR, GATE, HOUSE, STAIRS_UP, STAIRS_DOWN, MOUNTAIN, SWAMP = range(12)
# endregion

# region ЗОНА СПАВНА КЛЮЧА
KEY_ZONE_X_MIN, KEY_ZONE_X_MAX = 75, 95
KEY_ZONE_Y_MIN, KEY_ZONE_Y_MAX = 20, 45
# endregion

# region ПАЛИТРА: МИР
COLOR_GRASS       = (86, 160, 70)
COLOR_GRASS_DARK  = (72, 140, 60)
COLOR_TREE        = (34, 90, 40)
COLOR_WATER       = (50, 120, 200)
COLOR_STONE       = (110, 110, 120)
COLOR_DARK_FLOOR  = (60, 40, 40)
COLOR_GATE        = (170, 140, 60)
COLOR_SKY         = (30, 30, 40)
COLOR_HOUSE       = (139, 69, 19)
COLOR_ROOF        = (100, 40, 30)
COLOR_STAIRS_UP   = (200, 100, 100)
COLOR_MOUNTAIN      = (115, 100, 85)
COLOR_MOUNTAIN_DARK = (75, 60, 45)
COLOR_MOUNTAIN_SHADOW = (50, 38, 25)
COLOR_MOUNTAIN_LIGHT  = (145, 130, 110)
COLOR_SWAMP       = (50, 80, 50)
COLOR_SWAMP_BUBBLE = (70, 110, 70)
# endregion

# region ПАЛИТРА: ИГРОК
COLOR_PLAYER         = (60, 140, 220)
COLOR_SWORD          = (220, 220, 220)
COLOR_SWORD_UPGRADED = (255, 215, 0)
# endregion

# region ПАЛИТРА: ВРАГИ И NPC
COLOR_SLIME   = (100, 200, 100)
COLOR_SLIME_D = (60, 150, 60)
COLOR_ELDER   = (200, 180, 120)
COLOR_CRYSTAL = (180, 240, 255)
COLOR_BOSS    = (150, 40, 60)
# endregion

# region ПАЛИТРА: UI
COLOR_UI_TEXT = (240, 240, 240)
# endregion