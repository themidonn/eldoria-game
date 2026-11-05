import pygame
from settings import *


class Dialog:
    def __init__(self):
        self.active = False
        self.speaker = ""
        self.pages = []  # Теперь здесь будут храниться готовые Surface, а не строки
        self.page = 0
        self.is_choice = False

        # шрифты кэшируются один раз
        self.font_speaker = pygame.font.SysFont('arial', 18, bold=True)
        self.font_text = pygame.font.SysFont('arial', 22)
        self.font_hint = pygame.font.SysFont('arial', 18, bold=True)

        # бокс кэшируем один раз
        box_w, box_h = WIDTH - 80, 160
        self.box_rect = pygame.Rect(40, HEIGHT - 180, box_w, box_h)
        self.box_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        self.box_surface.fill((20, 20, 30, 230))

        # Кэшируем подсказки (они никогда не меняются)
        self.hint_space = self.font_hint.render("[Space] далее", True, (150, 150, 150))
        self.hint_yes = self.font_hint.render("[Y] Да", True, (100, 255, 100))
        self.hint_no = self.font_hint.render("[N] Нет", True, (255, 100, 100))

        self.speaker_surface = None

    def show(self, speaker, text, is_choice=False):
        self.speaker = speaker
        # Отрендерим имя спикера один раз
        self.speaker_surface = self.font_speaker.render(self.speaker, True, (240, 210, 130))

        # Защита от пустой строки: если текста нет, создаем пустую картинку
        empty_surface = self.font_text.render("", True, COLOR_UI_TEXT)
        self.pages = self._wrap(text) or [empty_surface]  # <-- ИСПРАВЛЕНО

        self.page = 0
        self.active = True
        self.is_choice = is_choice

    def _wrap(self, text):
        max_w = WIDTH - 120
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_text.size(test)[0] > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur: lines.append(cur)

        # Группируем по 3 строки и сразу рендерим в Surface
        rendered_pages = []
        for i in range(0, len(lines), 3):
            page_lines = lines[i:i + 3]
            page_text = "\n".join(page_lines)
            # Рендерим весь блок текста страницы один раз
            # (pygame.font умеет рисовать многострочный текст с \n)
            surface = self.font_text.render(page_text, True, COLOR_UI_TEXT)
            rendered_pages.append(surface)

        return rendered_pages

    def next_page(self):
        if self.is_choice: return
        self.page += 1
        if self.page >= len(self.pages):
            self.active = False

    def draw(self, screen):
        if not self.active:
            return

        screen.blit(self.box_surface, self.box_rect.topleft)
        pygame.draw.rect(screen, (200, 180, 120), self.box_rect, 3, border_radius=8)

        # Рисуем имя спикера (готовая Surface)
        screen.blit(self.speaker_surface, (self.box_rect.x + 20, self.box_rect.y + 10))

        # Рисуем текст текущей страницы (готовая Surface)
        screen.blit(self.pages[self.page], (self.box_rect.x + 20, self.box_rect.y + 45))

        # Рисуем подсказки (готовые Surface)
        if self.is_choice:
            screen.blit(self.hint_yes, (self.box_rect.right - 200, self.box_rect.bottom - 30))
            screen.blit(self.hint_no, (self.box_rect.right - 80, self.box_rect.bottom - 30))
        else:
            screen.blit(self.hint_space, (self.box_rect.right - self.hint_space.get_width() - 20,
                                          self.box_rect.bottom - 30))