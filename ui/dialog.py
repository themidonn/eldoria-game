import pygame
from settings import *


class Dialog:
    def __init__(self):
        self.active = False
        self.speaker = ""
        self.pages = []
        self.page = 0
        self.is_choice = False  # <-- Флаг для выбора (Да/Нет)

        # шрифты кэшируются один раз
        self.font_speaker = pygame.font.SysFont('arial', 18, bold=True)
        self.font_text = pygame.font.SysFont('arial', 22)
        self.font_hint = pygame.font.SysFont('arial', 18, bold=True)

        # бокс кэшируем один раз
        box_w, box_h = WIDTH - 80, 160
        self.box_rect = pygame.Rect(40, HEIGHT - 180, box_w, box_h)
        self.box_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        self.box_surface.fill((20, 20, 30, 230))

    def show(self, speaker, text, is_choice=False):
        self.speaker = speaker
        self.pages = self._wrap(text) or [""]
        self.page = 0
        self.active = True
        self.is_choice = is_choice  # <-- Сохраняем флаг

    def _wrap(self, text):
        max_w = WIDTH - 120
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_text.size(test)[0] > max_w:
                lines.append(cur);
                cur = w
            else:
                cur = test
        if cur: lines.append(cur)
        return ["\n".join(lines[i:i + 3]) for i in range(0, len(lines), 3)]

    def next_page(self):
        if self.is_choice: return  # При выборе нельзя листать дальше
        self.page += 1
        if self.page >= len(self.pages):
            self.active = False

    def draw(self, screen):
        if not self.active:
            return
        screen.blit(self.box_surface, self.box_rect.topleft)
        pygame.draw.rect(screen, (200, 180, 120), self.box_rect, 3, border_radius=8)
        screen.blit(self.font_speaker.render(self.speaker, True, (240, 210, 130)),
                    (self.box_rect.x + 20, self.box_rect.y + 10))
        for i, line in enumerate(self.pages[self.page].split("\n")):
            screen.blit(self.font_text.render(line, True, COLOR_UI_TEXT),
                        (self.box_rect.x + 20, self.box_rect.y + 45 + i * 30))

        # Рисуем подсказки внизу (либо [Space], либо [Y] / [N])
        if self.is_choice:
            hint_y = self.font_hint.render("[Y] Да", True, (100, 255, 100))
            hint_n = self.font_hint.render("[N] Нет", True, (255, 100, 100))
            screen.blit(hint_y, (self.box_rect.right - 200, self.box_rect.bottom - 30))
            screen.blit(hint_n, (self.box_rect.right - 80, self.box_rect.bottom - 30))
        else:
            hint = self.font_hint.render("[Space] далее", True, (150, 150, 150))
            screen.blit(hint, (self.box_rect.right - hint.get_width() - 20,
                               self.box_rect.bottom - 30))