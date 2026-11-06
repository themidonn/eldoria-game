"""
ui/dialog.py — Диалоговое окно.

Показывает речь NPC (с именем спикера сверху). Поддерживает:
- Пагинацию по 3 строки: [Space] — следующая.
- Выбор [Y] / [N] (is_choice=True): страницы не листаются.

Все поверхности (шрифты, бокс, подсказки, страницы текста)
кэшируются — в draw() только blit'ы, ни одного .render().
"""

import pygame
from settings import *


class Dialog:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self):
        # Состояние
        self.active = False
        self.speaker = ""
        self.pages = []                  # готовые Surface страниц (не строки!)
        self.page = 0
        self.is_choice = False

        # --- Шрифты (кэш) ---
        self.font_speaker = pygame.font.SysFont('arial', 18, bold=True)
        self.font_text    = pygame.font.SysFont('arial', 22)
        self.font_hint    = pygame.font.SysFont('arial', 18, bold=True)

        # --- Бокс (кэш) ---
        box_w, box_h = WIDTH - 80, 210
        self.box_rect = pygame.Rect(40, HEIGHT - 230, box_w, box_h)
        self.box_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        self.box_surface.fill((20, 20, 30, 230))

        # --- Три подсказки кэшируются один раз (они статичны) ---
        self.hint_space = self.font_hint.render("[Space] далее", True, (150, 150, 150))
        self.hint_yes   = self.font_hint.render("[Y] Да",       True, (100, 255, 100))
        self.hint_no    = self.font_hint.render("[N] Нет",      True, (255, 100, 100))

        # Пустая страница — на случай пустого текста в show()
        self.empty_surface = self.font_text.render("", True, COLOR_UI_TEXT)

        # Имя спикера (рендерится в show(), храним здесь для порядка)
        self.speaker_surface = None

    # ============================================================
    #   ПУБЛИЧНЫЕ МЕТОДЫ
    # ============================================================
    def show(self, speaker, text, is_choice=False):
        """Открывает диалог. Если text пуст — покажет пустую страницу."""
        self.speaker = speaker
        self.speaker_surface = self.font_speaker.render(
            self.speaker, True, (240, 210, 130)
        )

        self.pages = self._wrap(text) or [self.empty_surface]
        self.page = 0
        self.active = True
        self.is_choice = is_choice

    def next_page(self):
        """Переход к следующей странице. При выборе [Y]/[N] — не работает."""
        if self.is_choice:
            return

        self.page += 1
        if self.page >= len(self.pages):
            self.active = False

    # ============================================================
    #   ВНУТРЕННИЕ МЕТОДЫ
    # ============================================================
    def _wrap(self, text):
        """
        Разбивает текст на строки по ширине бокса,
        группирует по 3 строки на страницу
        и рендерит каждую страницу в готовый Surface.
        """
        max_w = WIDTH - 120
        words = text.split()

        # --- Разбиение на строки ---
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

            # Создаём пустую поверхность под всю страницу
            surf_h = line_height * len(page_lines)
            page_surf = pygame.Surface((max_w, surf_h), pygame.SRCALPHA)

            # Рендерим каждую строку отдельно и блитим на страницу
            for j, line in enumerate(page_lines):
                line_surf = self.font_text.render(line, True, COLOR_UI_TEXT)
                page_surf.blit(line_surf, (0, j * line_height))

            rendered_pages.append(page_surf)

        return rendered_pages

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen):
        if not self.active or not self.pages:
            return

        # --- Палитра ---
        BORDER_COLOR = (200, 180, 120)

        # --- Фон + рамка бокса ---
        screen.blit(self.box_surface, self.box_rect.topleft)
        pygame.draw.rect(screen, BORDER_COLOR, self.box_rect, 3, border_radius=8)

        # --- Имя спикера ---
        screen.blit(self.speaker_surface,
                    (self.box_rect.x + 20, self.box_rect.y + 10))

        # --- Текущая страница текста ---
        screen.blit(self.pages[self.page],
                    (self.box_rect.x + 20, self.box_rect.y + 45))

        # --- Подсказки внизу ---
        if self.is_choice:
            screen.blit(self.hint_yes, (self.box_rect.right - 200, self.box_rect.bottom - 30))
            screen.blit(self.hint_no,  (self.box_rect.right - 80,  self.box_rect.bottom - 30))
        else:
            screen.blit(self.hint_space,
                        (self.box_rect.right - self.hint_space.get_width() - 20,
                         self.box_rect.bottom - 30))