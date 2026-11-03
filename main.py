import asyncio
import pygame
from settings import WIDTH, HEIGHT  # ← Импортируем размеры из настроек

# Инициализация Pygame ДО импорта игровых модулей
pygame.init()
pygame.display.set_mode((WIDTH, HEIGHT))  # ← Используем переменные

from game import Game

async def main():
    game = Game()
    await game.run()
    await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())