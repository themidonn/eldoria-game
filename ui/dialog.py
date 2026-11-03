import pygame
from settings import *

class Dialog:
    def __init__(self):
        self.active = False
        self.speaker = ""
        self.pages = []
        self.page = 0
        # шрифты кэшируются один раз
        self.font_speaker = pygame.font.SysFont('arial', 18, bold=True)
        self.font_text    = pygame.font.SysFont('arial', 22)
        self.font_hint    = pygame.font.SysFont('arial', 18, bold=True)

        # бокс кэшируем один раз
        box_w, box_h = WIDTH - 80, 160
        self.box_rect = pygame.Rect(40, HEIGHT - 180, box_w, box_h)
        self.box_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        self.box_surface.fill((20, 20, 30, 230))

    def show(self, speaker, text):
        self.speaker = speaker
        self.pages = self._wrap(text) or [""]
        self.page = 0
        self.active = True

    def _wrap(self, text):
        # тот же шрифт, что и в draw → нет переполнения
        max_w = WIDTH - 120
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_text.size(test)[0] > max_w:
                lines.append(cur); cur = w
            else:
                cur = test
        if cur: lines.append(cur)
        return ["\n".join(lines[i:i+3]) for i in range(0, len(lines), 3)]

    def next_page(self):
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
        hint = self.font_hint.render("[Space] далее", True, (150, 150, 150))
        screen.blit(hint, (self.box_rect.right - hint.get_width() - 20,
                           self.box_rect.bottom - 30))