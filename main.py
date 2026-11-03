import asyncio
import pygame

# Инициализация Pygame ДО импорта игровых модулей
pygame.init()
pygame.display.set_mode((960, 640))  # Ширина и высота из settings.py

from game import Game

async def main():
    game = Game()
    await game.run()
    await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())