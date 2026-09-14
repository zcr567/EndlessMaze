import os
from enum import IntEnum

import pygame
import pygame as pg

from Resources import *
# noinspection PyPep8Naming
from widgets import WelcomeScreen, HUD, GameMode, MazeGame

# executable generating command
# pyinstaller -F --add-data "resource;resource" -w -i project_icon.ico main.py

pg.init()
INIT_SCREEN_SIZE = (1200, 800)  # not necessarily this value


class GameState(IntEnum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_GAME_TRANSITION = 3
    MENU_GAME_TRANSITION = 4


def _test_cb(*args):
    print(args)


class Game:
    def __init__(self):

        # initialize game window
        self.state = GameState.MENU
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode(INIT_SCREEN_SIZE, pygame.RESIZABLE)
        pg.display.set_caption('EndlessMaze')
        pg.display.set_icon(app_logo)
        self.window_size = pg.display.get_window_size()

        # game sound config
        self.sound_on = True

        # game screens
        self.welcome = WelcomeScreen(self.window_size,
                                     sound_switch_cb=self.toggle_sound,
                                     size_set_cb=self.set_maze_size,
                                     single_player_cb=self.start_single_player,
                                     double_player_cb=self.start_double_player,
                                     diff_set_cb=self.set_difficulty)
        self.hud = HUD(self.window_size)  # TODO: fill the params after the class is implemented
        self.maze_game: MazeGame | None = None  # will be initialized when start button hit
        self.current_screen = self.welcome

        # game logic related
        self.game_mode = GameMode.SINGLE
        self.maze_size_preset = 'medium'
        self.maze_diff_preset = 'normal'

    def run(self):
        # main loop
        while True:
            self.clock.tick(60)
            events = pg.event.get()

            # window managing
            for event in events:
                if event.type == pg.QUIT:
                    pg.quit()
                    raise SystemExit
                if event.type == pg.WINDOWSIZECHANGED:
                    self.current_screen.resize(pygame.display.get_window_size())
                if event.type == pg.USEREVENT + 2:  # game ends
                    self.start_single_player()
                    # self.current_screen = self.welcome
            if self.state != GameState.PAUSED:  # Maybe cause deadlock. (not occurred yet)
                self.current_screen.handle_events(events)
            self.current_screen.draw(self.screen)
            pygame.display.flip()

    def toggle_sound(self):
        # TODO: complete the function after sounds are prepared
        print("called toggle_sound()")
        self.sound_on = not self.sound_on

    def start_single_player(self):
        print("called start_single_player()")
        self.current_screen = MazeGame(gamemode=GameMode.SINGLE,
                                       size_preset=self.maze_size_preset,
                                       difficulty=self.maze_diff_preset)

    # noinspection PyMethodMayBeStatic
    def start_double_player(self):
        # TODO: complete it after two-player mode is implemented
        print("called start_double_player()")

    def set_difficulty(self, preset: str):
        print(f"called set_difficulty({preset})")
        self.maze_diff_preset = preset

    def set_maze_size(self, preset: str):
        print(f"called set_maze_size({preset})")
        self.maze_size_preset = preset


if __name__ == '__main__':
    window_pos = (0, 30)
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"
    app = Game()
    app.run()
