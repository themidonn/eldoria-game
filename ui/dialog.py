"""
ui/dialog.py — Диалоговое окно.

Показывает речь NPC (с именем спикера сверху). Поддерживает:
- Пагинацию по 3 строки: [Space] — следующая.
- Выбор [Y] / [N] (is_choice=True): страницы не листаются.

Все поверхности (шрифты, бокс, подсказки, страницы текста)
кэшируются — в draw() только blit'ы, ни одного .render().

Используется в game.py:
  - _reset() — создаёт экземпляр
  - _try_talk_to_npc(), _try_read_lore_stone(), _try_read_dungeon_lore()
  - _handle_dialog_input() — Y/N или Space
  - update() — блокирует движение, пока активен
  - _draw_ui() — draw

ВАЖНО: конструктор вызывает pygame.font.Font() —
перед созданием Dialog должен быть вызван pygame.font.init().
В main.py это гарантировано: init до импорта Game.

Поиск по файлу: Ctrl+F "region"
"""

import pygame
from settings import *


class Dialog:

    # region ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    BORDER_COLOR    = (200, 180, 120)   # рамка бокса
    SPEAKER_COLOR   = (240, 210, 130)   # имя спикера
    HINT_COLOR      = (150, 150, 150)   # [Space] далее
    HINT_YES_COLOR  = (100, 255, 100)   # [Y] Да
    HINT_NO_COLOR   = (255, 100, 100)   # [N] Нет
    BOX_FILL        = (20, 20, 30, 230) # фон бокса (alpha в цвете)
    # endregion

    # region КОНСТРУКТОР
    def __init__(self):
        # --- Состояние ---
        self.active = False
        self.speaker = ""
        self.pages = []                  # готовые Surface страниц (не строки!)
        self.page = 0
        self.is_choice = False

        # --- Шрифты ---
        try:
            self.font_speaker = pygame.font.Font("assets/Tiny5-Bold.ttf", 24)
            self.font_text    = pygame.font.Font("assets/Tiny5-Regular.ttf", 24)
            self.font_hint    = pygame.font.Font("assets/Tiny5-Bold.ttf", 16)
        except FileNotFoundError:
            self.font_speaker = pygame.font.Font(None, 24)
            self.font_text    = pygame.font.Font(None, 24)
            self.font_hint    = pygame.font.Font(None, 16)

        # --- Бокс (кэш) ---
        # Ширина: WIDTH - 80 (по 40 px отступа слева и справа).
        # Высота: 210 px, прижата к низу (HEIGHT - 230 — верх бокса,
        # снизу остаётся 20 px отступа от низа экрана).
        box_w, box_h = WIDTH - 80, 210
        self.box_rect = pygame.Rect(40, HEIGHT - 230, box_w, box_h)
        self.box_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        self.box_surface.fill(self.BOX_FILL)

        # --- Подсказки кэшируются один раз (они статичны) ---
        # Текст подсказок не меняется — рендерим в конструкторе,
        # в draw() только blit.
        self.hint_space = self.font_hint.render(
            "[Space] далее", True, self.HINT_COLOR
        )
        self.hint_yes = self.font_hint.render(
            "[Y] Да", True, self.HINT_YES_COLOR
        )
        self.hint_no = self.font_hint.render(
            "[N] Нет", True, self.HINT_NO_COLOR
        )

        # Пустая страница — на случай пустого текста в show().
        # Переиспользуется между диалогами (не мутируется).
        self.empty_surface = self.font_text.render("", True, COLOR_UI_TEXT)

        # Имя спикера (рендерится в show(), храним здесь для порядка)
        self.speaker_surface = None
    # endregion

    # region ПУБЛИЧНЫЕ МЕТОДЫ

    # region show
    def show(self, speaker, text, is_choice=False):
        """
        Открывает диалог. Если text пуст — покажет пустую страницу.

        Параметры:
          speaker — имя NPC ("Старейшина", "Житель", ...)
          text — содержимое (лор / реплика)
          is_choice — True для вопроса с выбором [Y]/[N]
        """
        self.speaker = speaker
        self.speaker_surface = self.font_speaker.render(
            self.speaker, True, self.SPEAKER_COLOR
        )

        # _wrap вернёт [] для пустого текста — fallback на empty_surface
        self.pages = self._wrap(text) or [self.empty_surface]
        self.page = 0
        self.active = True
        self.is_choice = is_choice
    # endregion

    # region next_page
    def next_page(self):
        """
        Переход к следующей странице.

        При is_choice=True — не работает: игрок должен нажать Y или N,
        game.py (_handle_dialog_input) сам закроет диалог и покажет
        ответную реплику.
        """
        if self.is_choice:
            return

        self.page += 1
        if self.page >= len(self.pages):
            self.active = False
    # endregion

    # endregion (ПУБЛИЧНЫЕ МЕТОДЫ)

    # region ВНУТРЕННИЕ МЕТОДЫ

    # region _wrap
    def _wrap(self, text):
        """
        Разбивает текст на строки по ширине бокса,
        группирует по 3 строки на страницу
        и рендерит каждую страницу в готовый Surface.

        Возвращает список pygame.Surface (по одной на страницу).

        Ограничение: если одно слово длиннее max_w, оно не разобьётся
        и вылезет за границу. Для русского текста в игре это
        не встречается (самые длинные слова — «Священное», «странник»).
        """
        max_w = WIDTH - 120
        words = text.split()

        # --- Разбиение на строки по ширине ---
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_text.size(test)[0] > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)

        # --- Группировка по 3 строки + рендер в Surface ---
        rendered_pages = []
        line_height = self.font_text.get_linesize()

        for i in range(0, len(lines), 3):
            page_lines = lines[i:i+3]

            # Создаём пустую поверхность под всю страницу.
            # Ширина фиксированная (max_w), высота — по числу строк.
            surf_h = line_height * len(page_lines)
            page_surf = pygame.Surface((max_w, surf_h), pygame.SRCALPHA)

            # Рендерим каждую строку отдельно и блитим на страницу
            for j, line in enumerate(page_lines):
                line_surf = self.font_text.render(line, True, COLOR_UI_TEXT)
                page_surf.blit(line_surf, (0, j * line_height))

            rendered_pages.append(page_surf)

        return rendered_pages
    # endregion

    # endregion (ВНУТРЕННИЕ МЕТОДЫ)

    # region ОТРИСОВКА
    def draw(self, screen):
        if not self.active or not self.pages:
            return

        # Параноидальная защита: page может выйти за len(pages)
        # только при баге в next_page(), но пусть лучше не рисует,
        # чем упадёт с IndexError.
        if self.page >= len(self.pages):
            return

        # --- Фон + рамка бокса ---
        screen.blit(self.box_surface, self.box_rect.topleft)
        pygame.draw.rect(screen, self.BORDER_COLOR, self.box_rect, 3,
                         border_radius=8)

        # --- Имя спикера ---
        screen.blit(self.speaker_surface,
                    (self.box_rect.x + 20, self.box_rect.y + 10))

        # --- Текущая страница текста ---
        screen.blit(self.pages[self.page],
                    (self.box_rect.x + 20, self.box_rect.y + 45))

        # --- Подсказки внизу ---
        hint_y = self.box_rect.bottom - 30

        if self.is_choice:
            # Позиционируем через get_width() — устойчиво к смене шрифта.
            # hint_no ближе к правому краю (20 px отступ),
            # hint_yes левее с зазором 40 px.
            no_x = self.box_rect.right - self.hint_no.get_width() - 20
            yes_x = no_x - self.hint_yes.get_width() - 40
            screen.blit(self.hint_yes, (yes_x, hint_y))
            screen.blit(self.hint_no,  (no_x,  hint_y))
        else:
            screen.blit(self.hint_space,
                        (self.box_rect.right - self.hint_space.get_width() - 20,
                         hint_y))
    # endregion