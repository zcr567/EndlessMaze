import os
from enum import IntEnum

import pygame
import pygame as pg

from Resources import *
from effects import *
# noinspection PyPep8Naming
from widgets import WelcomeScreen, GameMode, MazeGame, GameGameTrans, Player, ManuGameTrans

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
        self.p1, self.p2 = Player(), Player()

        # game sound config
        self.sound_on = True

        # game screens
        self.welcome = WelcomeScreen(self.window_size,
                                     sound_switch_cb=self.toggle_sound,
                                     size_set_cb=self.set_maze_size,
                                     single_player_cb=self.start_single_player,
                                     double_player_cb=self.start_double_player,
                                     diff_set_cb=self.set_difficulty)
        self.maze_game: MazeGame | None = None  # will be initialized when start button hit
        self.current_screen = self.welcome
        self.next_game = None

        # game logic related
        self.game_mode = GameMode.SINGLE
        self.maze_size_preset = 'medium'
        self.maze_diff_preset = 'normal'

    def toggle_sound(self):
        # TODO: complete the function after sounds are prepared
        print("called toggle_sound()")
        self.sound_on = not self.sound_on
        if self.maze_game is not None:
            self.maze_game.hud.set_sound(self.sound_on)
            self.maze_game.pause_screen.set_sound(self.sound_on)

    def start_single_player(self):
        print("called start_single_player()")
        self.current_screen = ManuGameTrans(self.welcome, gamemode=GameMode.SINGLE,
                                            size_preset=self.maze_size_preset,
                                            difficulty=self.maze_diff_preset,
                                            players=[self.p1],
                                            pause_cb=self.pause_game,
                                            sound_switch_cb=self.toggle_sound,
                                            resume_cb=self.resume_game,
                                            menu_cb=self.quit_to_menu)

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

    def pause_game(self):
        # called by the HUD pause button / ESC while playing
        if self.state == GameState.PLAYING and self.current_screen is self.maze_game:
            self.state = GameState.PAUSED
            self.maze_game.pause_timing()
            print("called pause_game()")

    def resume_game(self):
        # called by the pause screen resume button / ESC
        if self.state == GameState.PAUSED:
            self.state = GameState.PLAYING
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + 6))
            print("called resume_game()")

    def quit_to_menu(self):
        # called by the pause screen menu button; back to the main menu with a transition
        print("called quit_to_menu()")
        self.state = GameState.MENU
        self.current_screen = ManuGameTrans(self.maze_game, _manu=self.welcome)

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
                    print(self.maze_game)
                    self.state = GameState.GAME_GAME_TRANSITION
                    self.current_screen = GameGameTrans(self.maze_game)
                    # self.start_single_player()
                    # self.current_screen = self.welcome
                if event.type == pg.USEREVENT + 3:  # game-game transition ends
                    self.maze_game = self.current_screen.get_new_game()
                    self.current_screen = self.maze_game
                    self.current_screen.start_timing()
                    self.state = GameState.PLAYING
                    self.next_game = None
                if event.type == pg.USEREVENT + 4:  # from menu to game
                    self.maze_game = self.current_screen.get_new_screen()
                    self.current_screen = self.maze_game
                    self.current_screen.start_timing()
                    self.state = GameState.PLAYING if isinstance(self.maze_game, MazeGame) else GameState.MENU
                    self.next_game = None
                if event.type == pg.USEREVENT + 5:  # from game to menu
                    self.current_screen = self.welcome
                    self.state = GameState.MENU
                if event.type == pg.USEREVENT + 6:
                    if type(self.current_screen) is MazeGame:
                        self.current_screen.resume_timing()
                if event.type == pg.KEYDOWN:
                    if (event.key == pg.K_BACKSPACE and not isinstance(self.current_screen, WelcomeScreen)
                            and not isinstance(self.current_screen, ManuGameTrans)):
                        self.state = GameState.MENU
                        self.current_screen = ManuGameTrans(self.current_screen, _manu=self.welcome)
                    elif event.key == pg.K_ESCAPE:
                        # ESC toggles pause while the maze is running
                        if self.state == GameState.PLAYING and self.current_screen is self.maze_game:
                            self.pause_game()
                        elif self.state == GameState.PAUSED:
                            self.resume_game()
            if self.state == GameState.PAUSED:  # Maybe cause deadlock. (not occurred yet)
                self.maze_game.pause_screen.handle_events(events)
            else:
                self.current_screen.handle_events(events)
                if self.state == GameState.PLAYING and self.current_screen is self.maze_game:
                    self.maze_game.hud.handle_events(events)

            update_effects()
            self.current_screen.draw(self.screen)
            if self.state == GameState.PLAYING and self.current_screen is self.maze_game:
                self.maze_game.hud.draw(self.screen)
            elif self.state == GameState.PAUSED:
                self.maze_game.pause_screen.draw(self.screen)
            pygame.display.flip()


if __name__ == '__main__':
    window_pos = (0, 30)
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"
    app = Game()
    app.run()

