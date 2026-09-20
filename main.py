import os
from enum import IntEnum

import pygame as pg

from Resources import *
from effects import *
# noinspection PyPep8Naming
from widgets import WelcomeScreen, GameMode, MazeGame, GameGameTrans, Player, BlackScreenTrans
# (two-player mode) the ghost transition of the versus mode and its random role assignment
from widgets import RecordsScreen, VersusDeathTrans, VersusResult, assign_versus_roles
# (history) the results of the games played so far, kept in records.json next to the game
from records import Records

# executable generating command
# pyinstaller -F --add-data "Resources;Resources" -w -i project_icon.ico main.py

pg.init()
INIT_SCREEN_SIZE = (1200, 800)  # not necessarily this value
pg.mixer.init()


class GameState(IntEnum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_GAME_TRANSITION = 3
    MENU_GAME_TRANSITION = 4


def _test_cb(*args):
    print(args)


class Game:
    BG_MUSIC_VOLUME = 0.5

    def __init__(self):

        # initialize game window
        self.state = GameState.MENU
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode(INIT_SCREEN_SIZE, pg.RESIZABLE)
        pg.display.set_caption('EndlessMaze')
        pg.display.set_icon(app_logo)
        self.window_size = pg.display.get_window_size()
        self.p1, self.p2 = Player(), Player()
        pg.mixer.music.play(-1)
        pg.mixer.music.set_volume(self.BG_MUSIC_VOLUME)

        # game sound config
        self.sound_on = True

        # game screens
        self.welcome = WelcomeScreen(self.window_size,
                                     sound_switch_cb=self.toggle_sound,
                                     size_set_cb=self.set_maze_size,
                                     single_player_cb=self.start_single_player,
                                     double_player_cb=self.start_double_player,
                                     diff_set_cb=self.set_difficulty,
                                     vision_set_cb=self.set_vision,
                                     open_rec_cb=self.open_records)

        self.records = Records()
        self.records_screen = RecordsScreen(self.records, back_cb=self.close_records)

        self.maze_game: MazeGame | None = None  # will be initialized when start button hit
        self.current_screen = self.welcome
        self.next_game = None

        # game logic related
        self.game_mode = GameMode.SINGLE
        self.maze_size_preset = 'medium'
        self.maze_diff_preset = 'normal'
        self.limited_vision = False  # (limited vision) off until the menu switches it on

    def open_records(self):
        """show the records of the games played so far"""
        print("called open_records()")
        self.records_screen.resize(pg.display.get_window_size())
        self.current_screen = self.records_screen
        self.state = GameState.MENU

    def close_records(self):
        """back to the main menu"""
        self.current_screen = self.welcome
        self.state = GameState.MENU

    def set_vision(self, preset: str):
        """the menu hands over "full" or "limited". MazeGame carries the mode as a
        class default, so every maze built from now on already has it - including the one the menu
        transition builds a few lines before the match really starts, which used to show the whole
        map for its first frames."""
        print(f"called set_vision({preset})")
        self.limited_vision = preset == "limited"
        MazeGame.limited_vision = self.limited_vision

    def toggle_sound(self):
        print("called toggle_sound()")
        self.sound_on = not self.sound_on
        if self.sound_on:
            pg.mixer.music.set_volume(self.BG_MUSIC_VOLUME)
            pg.mixer.music.play(-1)
        else:
            pg.mixer.music.fadeout(500)

        if self.maze_game is not None:
            self.maze_game.hud.set_sound(self.sound_on)
            self.maze_game.pause_screen.set_sound(self.sound_on)

    def start_single_player(self):
        print("called start_single_player()")
        self.reset_players()
        self.current_screen = BlackScreenTrans(self.welcome, gamemode=GameMode.SINGLE,
                                               size_preset=self.maze_size_preset,
                                               difficulty=self.maze_diff_preset,
                                               players=[self.p1],
                                               pause_cb=self.pause_game,
                                               sound_switch_cb=self.toggle_sound,
                                               resume_cb=self.resume_game,
                                               menu_cb=self.quit_to_menu)

    # noinspection PyMethodMayBeStatic
    def start_double_player(self):
        print("called start_double_player()")
        self.reset_players()
        assign_versus_roles(self.p1, self.p2)
        self.current_screen = BlackScreenTrans(self.welcome, gamemode=GameMode.DOUBLE,
                                               size_preset=self.maze_size_preset,
                                               difficulty=self.maze_diff_preset,
                                               players=[self.p1, self.p2],
                                               pause_cb=self.pause_game,
                                               sound_switch_cb=self.toggle_sound,
                                               resume_cb=self.resume_game,
                                               menu_cb=self.quit_to_menu)

    def set_difficulty(self, preset: str):
        print(f"called set_difficulty({preset})")
        self.maze_diff_preset = preset

    def set_maze_size(self, preset: str):
        print(f"called set_maze_size({preset})")
        self.maze_size_preset = preset

    def reset_players(self):
        self.p1.score = 0
        self.p2.score = 0
        self.p1.eaten = 0
        self.p2.eaten = 0
        self.p1.eat = 0
        self.p2.eat = 0

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
            pg.event.post(pg.event.Event(pg.USEREVENT + 6))
            print("called resume_game()")

    def quit_to_menu(self):
        """called by the pause screen menu button; back to the main menu with a transition"""
        print("called quit_to_menu()")
        self.state = GameState.MENU
        if (self.maze_game.gamemode == GameMode.DOUBLE
                and not getattr(self.maze_game, "versus_settled", False)):
            self.current_screen = VersusResult(self.maze_game, self.welcome)
            self.records.add_versus(self.maze_game, self.current_screen.winner_text())
        else:
            self.current_screen = BlackScreenTrans(self.maze_game, _manu=self.welcome)

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
                    self.current_screen.resize(pg.display.get_window_size())
                if event.type == pg.USEREVENT + 2:  # game ends
                    self.state = GameState.GAME_GAME_TRANSITION
                    self.current_screen = GameGameTrans(self.maze_game)
                    # a finished solo maze is written down with its time and its score
                    if (isinstance(self.maze_game, MazeGame)
                            and self.maze_game.gamemode == GameMode.SINGLE):
                        self.records.add_single(self.maze_game)
                if event.type == pg.USEREVENT + 8:  # (two-player mode) the prey was caught
                    self.state = GameState.GAME_GAME_TRANSITION
                    self.current_screen = VersusDeathTrans(self.maze_game)
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
                if event.type == pg.USEREVENT + 5:  # from other to menu
                    self.current_screen = self.welcome
                    self.state = GameState.MENU
                if event.type == pg.USEREVENT + 6:
                    if type(self.current_screen) is MazeGame:
                        self.current_screen.resume_timing()
                if event.type == pg.USEREVENT + 7 and self.sound_on:
                    event.sound.play()
                if event.type == pg.KEYDOWN:
                    if (event.key == pg.K_BACKSPACE and not isinstance(self.current_screen, WelcomeScreen)
                            and not isinstance(self.current_screen, BlackScreenTrans)):
                        self.quit_to_menu()
                    elif event.key == pg.K_ESCAPE:
                        # ESC toggles pause while the maze is running
                        if self.state == GameState.PLAYING and self.current_screen is self.maze_game:
                            self.pause_game()
                        elif self.state == GameState.PAUSED:
                            self.resume_game()
            if self.state == GameState.PAUSED:  # Maybe cause deadlock. (not occurred yet)
                self.pause_game()
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
            pg.display.flip()


if __name__ == '__main__':
    window_pos = (0, 30)
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"
    app = Game()
    app.run()
