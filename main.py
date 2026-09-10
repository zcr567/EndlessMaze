import os
import random

import pygame
import pygame as pg
from pygame.draw import line, circle

from maze import Maze

window_pos = (0, 30)
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"

BG_COLORS = ((204, 128, 204), (108, 150, 200), (200, 175, 64), (100, 204, 100))
MAZE_EDGE_COLOR = (255, 255, 255)
SCREEN_SIZE = (600, 800)
field_width = random.randint(3, 50)
field_height = random.randint(3, 50)
bg_color = random.choice(BG_COLORS)

pg.init()
clock = pg.time.Clock()
screen = pg.display.set_mode(SCREEN_SIZE, pygame.RESIZABLE)
pg.display.set_caption('Maze')
screen.fill(bg_color)

window_size = (0, 0)
points_surf = pygame.Surface((1, 1))
maze_surf = pg.Surface((1, 1))
cell_width = 0
maze_edge_width = 0
size = 0
region = (0, 0)


def update_arrangement():
    global window_size, points_surf, maze_surf, cell_width, size, region, maze_edge_width
    window_size = pg.display.get_window_size()
    points_surf = pygame.Surface(window_size, pygame.SRCALPHA)
    maze_surf = pygame.Surface(window_size, pygame.SRCALPHA)
    cell_width = min(window_size[0] / (field_width * 1.2), window_size[1] / (field_height * 1.2))
    maze_edge_width = max(int(cell_width // 6), 1)
    size = (cell_width * field_width, cell_width * field_height)
    region = ((window_size[0] - size[0]) / 2, (window_size[1] - size[1]) / 2)


def draw_maze(_maze, extra_points=None, color="red", flip=True):
    if flip:
        maze_surf.fill((0, 0, 0, 0))
        points_surf.fill((0, 0, 0, 0))
    inst = _maze.draw_instructions()
    for row in range(field_height * 2 + 1):
        for col in range(field_width * 2 + 1):
            op = inst[row][col]
            if row % 2 == 0 and col % 2 == 1 and op == 0:
                line(maze_surf,
                     MAZE_EDGE_COLOR,
                     (int(region[0] + cell_width * (col // 2)),
                      int(region[1] + cell_width * (row // 2))),
                     (int(region[0] + cell_width * (col // 2) + cell_width),
                      int(region[1] + cell_width * (row // 2))),
                     width=maze_edge_width)
            elif row % 2 == 1 and col % 2 == 0 and op == 0:
                line(maze_surf,
                     MAZE_EDGE_COLOR,
                     (int(region[0] + cell_width * (col // 2)),
                      int(region[1] + cell_width * (row // 2))),
                     (int(region[0] + cell_width * (col // 2)),
                      int(region[1] + cell_width * (row // 2) + cell_width)),
                     width=maze_edge_width)

            # add round corners
            if maze_edge_width > 2:
                # center coordinate plus (1, 1) to align the circles with the lines
                # (ways line() and circle() calculate coordinate are different)
                pygame.draw.circle(points_surf,
                                   MAZE_EDGE_COLOR,
                                   (int(region[0] + cell_width * (col // 2) + 1),
                                    int(region[1] + cell_width * (row // 2)) + 1),
                                   int(maze_edge_width / 2))
    if extra_points:
        for col, row in extra_points:
            circle(points_surf,
                   color,
                   (int(region[0] + cell_width * (col + 0.5) + 1),
                    int(region[1] + cell_width * (row + 0.5)) + 1),
                   4)


def mainloop_once(_maze, extra_points=None, color=None, flip=True):
    clock.tick(60)
    update_arrangement()

    screen.fill(bg_color)
    draw_maze(_maze, extra_points, color, flip)
    if flip:
        p = _maze.get_right_path()
        for i in range(len(p)):
            for j in range(i + 1, len(p)):
                if p[i] == p[j]:
                    pygame.draw.circle(points_surf,
                                       "red",
                                       (region[0] + cell_width * (p[i][0] + 0.5),
                                        region[1] + cell_width * (p[i][1] + 0.5)),
                                       2)
        screen.blit(maze_surf, (0, 0))
        screen.blit(points_surf, (0, 0))
        pygame.display.flip()


# set_callback_hook(mainloop_once)

frame_id = 0
if __name__ == '__main__':
    maze0 = Maze((field_width, field_height))

    while True:
        clock.tick(60)
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                exit()
        mainloop_once(maze0)
