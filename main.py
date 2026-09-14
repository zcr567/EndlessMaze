import os
import random
from enum import IntEnum, IntFlag

import pygame
import pygame as pg
from pygame.draw import line

from Resources import *
from effects import *
from maze import Maze, DIFFICULTY_PRESETS, SIZE_PRESETS
from widgets import WelcomeScreen, HUD
from vectors import Cell, DIR_VECS
# noinspection PyPep8Naming
from vectors import Vector as V

# executable generating command
# pyinstaller -F --add-data "resource;resource" -w -i project_icon.ico main.py


pg.init()
INIT_SCREEN_SIZE = (600, 800)
window_size = (0, 0)


class PlayerType(IntEnum):
    SINGLE = 0
    PREDATOR = 1
    prey = 2


class GameMode(IntEnum):
    SINGLE = 0
    DOUBLE = 1


class GameState(IntEnum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2


class DispState(IntFlag):
    IDLE = 1
    MOVING = 2
    ROTATING = 4
    DYING = 8


game_mode = GameMode.SINGLE


class Player:
    """Player class."""

    def __init__(self, game, pos0=V(0, 0), heading=Cell.GO_UP, player_type=PlayerType.SINGLE):
        # basic properties
        self.game: MazeGame = game
        self.maze: Maze = self.game.maze
        self.surface = self.game.screen
        self.player_type = player_type
        self.pos = pos0
        self.heading = heading

        # game logic
        self.eaten = 0
        self.eat = 0

        # display
        if self.player_type == PlayerType.PREDATOR:
            self.anim_dict: dict[Cell:Animation] = predator_anim_dict
        else:
            self.anim_dict: dict[Cell:Animation] = prey_anim_dict
        self.cur_anim: Animation = self.anim_dict[self.heading]
        self.cur_anim.set_position(self.pos_to_surf())
        self.disp_state = DispState.IDLE

        self.movement_intp = ReversedQuad(step=15)
        self.pos_next = self.pos
        self.movement_vec = V(0, 0)

    def pos_to_surf(self, pos=None):
        """return the current position in maze_surf coordinates"""
        if pos is None:
            return V(int(self.game.region[0] + self.game.cell_width * (self.pos[0] + 0.5) + 1),
                     int(self.game.region[1] + self.game.cell_width * (self.pos[1] + 0.5)) + 1)
        else:
            return V(int(self.game.region[0] + self.game.cell_width * (pos[0] + 0.5) + 1),
                     int(self.game.region[1] + self.game.cell_width * (pos[1] + 0.5)) + 1)

    def _is_available(self, vec):
        """return True if there is no obstacle between 'self.pos_next' and 'self.pos_next + vec'"""
        return (self.maze.is_valid_coord(self.pos_next + vec)
                and self.game.inst[2 * self.pos_next[1] + vec[1] + 1][2 * self.pos_next[0] + vec[0] + 1] == 2)

    def move(self, direction: Cell):
        # calculate the next position
        if self.disp_state & DispState.MOVING:
            return
        vec = DIR_VECS[direction]
        if direction != self.heading:
            self.heading = direction
            self.disp_state |= DispState.ROTATING
        all_headings = [V(1, 0), V(0, -1), V(-1, 0), V(0, 1)]
        if self._is_available(vec):
            self.pos_next += vec
        else:
            return
        while (self._is_available(vec)
               and not self._is_available(all_headings[(all_headings.index(vec) + 1) % 4])
               and not self._is_available(all_headings[(all_headings.index(vec) + 3) % 4])
               and not self.pos == self.maze.end):
            # the condition: there is one available cell in the front, and there is no branch at the current cell
            # and the current cell is not the end of the maze
            self.pos_next += vec

        # initialize movement animation
        self.movement_intp = ReversedQuad(step=5 * abs(sum(self.pos_next - self.pos)))
        self.movement_vec = self.pos_to_surf(self.pos_next) - self.pos_to_surf(self.pos)
        self.disp_state |= DispState.MOVING

    def draw(self):
        if self.disp_state & DispState.MOVING:
            if self.movement_intp.get() != 1:
                self.cur_anim.set_position(self.pos_to_surf() + self.movement_vec * self.movement_intp.get())
                self.movement_intp.update()
            else:
                self.disp_state ^= DispState.MOVING
                self.pos = self.pos_next
                self.movement_intp.set(0)
                self.movement_vec = V(0, 0)
        if self.disp_state & DispState.ROTATING:
            fid = self.cur_anim.get_frame_id()
            pos = self.cur_anim.get_position()
            self.cur_anim = self.anim_dict[self.heading]
            self.cur_anim.set_frame_id(fid)
            self.cur_anim.set_position(pos)
            self.disp_state ^= DispState.ROTATING
        if self.disp_state == DispState.IDLE:  # must be "==" !
            self.cur_anim.set_position(self.pos_to_surf())

        self.cur_anim.step()
        self.cur_anim.draw(self.surface, size=[self.game.cell_width * 1.2, self.game.cell_width * 1.2])


class MazeGame:
    MAZE_EDGE_COLOR = (255, 255, 255)
    BG_COLORS = ((204, 128, 204), (108, 150, 200), (200, 175, 64), (100, 204, 100))
    _instance = None
    MAX_MAZE_WIDTH = 10
    MAX_MAZE_HEIGHT = 10

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, surf, gamemode=GameMode.SINGLE,
                 size_preset="medium", difficulty="normal"):
        # common
        self.gamemode = gamemode
        self.size_preset = size_preset
        self.difficulty = difficulty
        side_min, side_max = SIZE_PRESETS[size_preset]
        self.field_width = random.randint(side_min, side_max)
        self.field_height = random.randint(side_min, side_max)
        diff_kwargs = DIFFICULTY_PRESETS[difficulty] or {}
        self.maze = Maze((self.field_width, self.field_height), **diff_kwargs)
        self.inst = self.maze.draw_instructions()

        # display related
        self.maze_surf = pygame.Surface(window_size, pygame.SRCALPHA)
        self.bg_color = random.choice(self.BG_COLORS)
        self.screen = surf
        self.region = V(0, 0)
        self.cell_width = 0
        self.maze_edge_width = 0
        self.update_arrangement()

        # game logic related
        self.players = []
        if gamemode == GameMode.SINGLE:
            self.players.append(Player(self, pos0=self.maze.start))
        elif gamemode == GameMode.DOUBLE:
            pass

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
        """draw the maze on "self.maze_surf" property."""
        self.maze_surf.fill((0, 0, 0, 0))
        # self.inst = self.maze.draw_instructions()
        for row in range(self.field_height * 2 + 1):
            for col in range(self.field_width * 2 + 1):
                op = self.inst[row][col]
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

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_RIGHT:
                    self.players[0].move(Cell.GO_RIGHT)
                elif event.key == pg.K_LEFT:
                    self.players[0].move(Cell.GO_LEFT)
                elif event.key == pg.K_UP:
                    self.players[0].move(Cell.GO_UP)
                elif event.key == pg.K_DOWN:
                    self.players[0].move(Cell.GO_DOWN)
            else:
                pass
                # print(event)

    def update_display(self):
        self.screen.fill(self.bg_color)
        self.draw_maze()
        self.screen.blit(self.maze_surf, (0, 0))
        for p in self.players:
            p.draw()


frame_id = 0
if __name__ == '__main__':
    clock = pg.time.Clock()

    window_pos = (0, 30)
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"

    screen = pg.display.set_mode(INIT_SCREEN_SIZE, pygame.RESIZABLE)
    pg.display.set_caption('EndlessMaze')
    pg.display.set_icon(app_logo)
    window_size = pg.display.get_window_size()

    main_game = MazeGame(screen)

    welcome = WelcomeScreen(window_size)
    hud = HUD(window_size)
    main_game: MazeGame | None = None
    sound_on = True
    state = GameState.MENU

    while True:
        clock.tick(60)
        events = pg.event.get()

        # 窗口级事件
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if event.type == pg.WINDOWSIZECHANGED:
                window_size = pg.display.get_window_size()
                welcome.resize(window_size)
                hud.resize(window_size)
                if main_game is not None:
                    main_game.update_arrangement()

        esc_pressed = any(e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE for e in events)

        if state == GameState.MENU:
            action = welcome.handle_events(events)
            if action == "start_single":
                main_game = MazeGame(screen, size_preset=welcome.size_preset,
                                     difficulty=welcome.difficulty)
                hud.set_paused(False)
                state = GameState.PLAYING
            elif action == "toggle_sound":
                sound_on = not sound_on
            welcome.draw(screen)

        elif state == GameState.PLAYING:
            if esc_pressed:
                state = GameState.PAUSED
                hud.set_paused(True)
            else:
                main_game.handle_events(events)
                action = hud.handle_events(events)
                if action == "pause":
                    state = GameState.PAUSED
                    hud.set_paused(True)
                elif action == "toggle_sound":
                    sound_on = not sound_on
            main_game.game_logic()
            main_game.update_display()
            hud.draw(screen, main_game.players[0].eaten)

        else:  # GameState.PAUSED
            if esc_pressed:
                state = GameState.PLAYING
                hud.set_paused(False)
            else:
                action = hud.handle_events(events)
                if action == "resume":
                    state = GameState.PLAYING
                    hud.set_paused(False)
                elif action == "quit_to_menu":
                    state = GameState.MENU
                    hud.set_paused(False)
                elif action == "toggle_sound":
                    sound_on = not sound_on
            main_game.update_display()
            hud.draw(screen, main_game.players[0].eaten)

        welcome.set_sound(sound_on)
        hud.set_sound(sound_on)
        pygame.display.flip()
