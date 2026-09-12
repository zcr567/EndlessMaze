import os
import random
from enum import IntEnum

import pygame
import pygame as pg
from pygame.draw import line

from maze import Maze
from vectors import Vector, Cell

# executable generating command
# pyinstaller -F --add-data "resource;resource" -w -i project_icon.ico main.py

window_pos = (0, 30)
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"

pg.init()
clock = pg.time.Clock()
INIT_SCREEN_SIZE = (600, 800)

screen = pg.display.set_mode(INIT_SCREEN_SIZE, pygame.RESIZABLE)
pg.display.set_caption('Maze')

window_size = (0, 0)


class PlayerType(IntEnum):
    SINGLE = 0
    PREDATOR = 1
    prey = 2


class GameMode(IntEnum):
    SINGLE = 0
    DOUBLE = 1


game_mode = GameMode.SINGLE


class Player:
    """Base class for players, implemented basic display and move functions."""

    def __new__(cls, *args, **kwargs):
        raise NotImplementedError

    def __init__(self, game, x0=0, y0=0, heading=Cell.GO_UP, player_type: int = 0):
        self.game = game
        self.player_type = player_type
        self.x = x0
        self.y = y0
        self.heading = heading
        self.player_type = player_type
        pass

    def move(self):
        self.game.maze.get_p()

    def draw(self):
        if game_mode == GameMode.SINGLE:
            pass
        (int(self.game.region[0] + self.game.cell_width * (self.x + 0.5) + 1),
         int(self.game.region[1] + self.game.cell_width * (self.y + 0.5)) + 1)


class MazeGame:
    MAZE_EDGE_COLOR = (255, 255, 255)
    BG_COLORS = ((204, 128, 204), (108, 150, 200), (200, 175, 64), (100, 204, 100))

    def __init__(self, surf: pygame.Surface):

        # common
        self.field_width = random.randint(3, 50)
        self.field_height = random.randint(3, 50)
        self.maze = Maze((self.field_width, self.field_height))

        # display related
        self.maze_surf = surf
        self.bg_color = random.choice(self.BG_COLORS)
        self.screen = surf
        self.region = Vector(0, 0)
        self.cell_width = 0
        self.maze_edge_width = 0

    def update_arrangement(self):
        """update the screen size variables, call every time the screen size changes"""
        global window_size
        window_size = pg.display.get_window_size()
        self.maze_surf = pygame.Surface(window_size, pygame.SRCALPHA)
        self.cell_width = min(window_size[0] / (self.field_width * 1.2), window_size[1] / (self.field_height * 1.2))
        self.maze_edge_width = max(int(self.cell_width // 6), 1)
        size = (self.cell_width * self.field_width, self.cell_width * self.field_height)
        self.region = ((window_size[0] - size[0]) / 2, (window_size[1] - size[1]) / 2)

    def draw_maze(self):
        """draw the maze on self.maze_surf property."""
        self.maze_surf.fill((0, 0, 0, 0))
        inst = self.maze.draw_instructions()
        for row in range(self.field_height * 2 + 1):
            for col in range(self.field_width * 2 + 1):
                op = inst[row][col]
                if row % 2 == 0 and col % 2 == 1 and op == 0:
                    line(self.maze_surf,
                         self.MAZE_EDGE_COLOR,
                         (int(self.region[0] + self.cell_width * (col // 2)),
                          int(self.region[1] + self.cell_width * (row // 2))),
                         (int(self.region[0] + self.cell_width * (col // 2) + self.cell_width),
                          int(self.region[1] + self.cell_width * (row // 2))),
                         width=self.maze_edge_width)
                elif row % 2 == 1 and col % 2 == 0 and op == 0:
                    line(self.maze_surf,
                         self.MAZE_EDGE_COLOR,
                         (int(self.region[0] + self.cell_width * (col // 2)),
                          int(self.region[1] + self.cell_width * (row // 2))),
                         (int(self.region[0] + self.cell_width * (col // 2)),
                          int(self.region[1] + self.cell_width * (row // 2) + self.cell_width)),
                         width=self.maze_edge_width)

                # add round corners
                if self.maze_edge_width > 2:
                    # center coordinate plus (1, 1) to align the circles with the lines
                    # (ways line() and circle() calculate coordinate are different)
                    pygame.draw.circle(self.maze_surf,
                                       self.MAZE_EDGE_COLOR,
                                       (int(self.region[0] + self.cell_width * (col // 2) + 1),
                                        int(self.region[1] + self.cell_width * (row // 2)) + 1),
                                       int(self.maze_edge_width / 2))

    def game_logic(self):
        pass

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                exit()
            if event.type == pg.WINDOWSIZECHANGED:
                self.update_arrangement()
            else:
                pass
                # print(event)

    def update_display(self):
        self.screen.fill(self.bg_color)
        self.draw_maze()

        screen.blit(self.maze_surf, (0, 0))
        pygame.display.flip()


# set_callback_hook(mainloop_once)

frame_id = 0
if __name__ == '__main__':
    main_game = MazeGame(screen)
    main_game.update_arrangement()

    while True:
        clock.tick(60)
        main_game.handle_events()
        main_game.update_display()
