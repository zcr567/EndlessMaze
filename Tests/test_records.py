"""
Self-check of the history feature.

Two things matter here: the records have to survive a restart (and never take the game down when
the file is missing or damaged), and the game has to actually write a record when a solo maze is
finished or a versus match is settled.

    python -m unittest Tests.test_records -v
"""

import os
import sys
import tempfile
import unittest

import pygame as pg

import main as game_main
from records import Records
# noinspection PyPep8Naming
from vectors import Vector as V
from widgets import (GameMode, MazeGame, Player, RecordsScreen, WelcomeScreen,
                     assign_versus_roles, make_font, versus_pair)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCREEN_SIZE = (1200, 800)
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")


class FlowDone(Exception):
    """raised from inside a frame to leave the real game loop"""


class IdleClock:
    """the real loop ticks a clock between frames; tests do not want to wait"""

    @staticmethod
    def tick(_fps=60):
        return 0


def ensure_display():
    pg.init()
    if pg.display.get_surface() is None:
        pg.display.set_mode(SCREEN_SIZE, pg.RESIZABLE)
    return pg.display.get_surface()


def save_shot(surface, name):
    os.makedirs(SHOT_DIR, exist_ok=True)
    path = os.path.join(SHOT_DIR, name)
    pg.image.save(surface, path)
    return path


def click(rect):
    pg.event.post(pg.event.Event(pg.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1}))
    pg.event.post(pg.event.Event(pg.MOUSEBUTTONUP, {"pos": rect.center, "button": 1}))


def drive(app, step, max_frames=900):
    """run the real “Game.run” loop frame by frame, calling step(state) after every frame"""
    real_flip = pg.display.flip
    state = {"frames": 0, "stage": "start"}

    def flip():
        state["frames"] += 1
        real_flip()
        if state["frames"] > max_frames:
            raise FlowDone()
        step(state)

    pg.display.flip = flip
    try:
        app.run()
    except FlowDone:
        pass
    finally:
        pg.display.flip = real_flip
    return state


class TestRecordsStore(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "records.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_a_missing_file_is_an_empty_history(self):
        records = Records(self.path)
        self.assertEqual(len(records), 0)
        self.assertIsNone(records.best_single())
        self.assertEqual(records.shown(), [])

    def test_records_survive_a_restart(self):
        records = Records(self.path)
        records.add({"mode": "single", "time": "00:12:345", "score": 420, "size": "8x8",
                     "difficulty": "normal"})
        records.add({"mode": "versus", "winner": "P2 WINS", "scores": [100, 300], "deaths": [1, 0]})

        again = Records(self.path)
        self.assertEqual(len(again), 2, "both games have to come back from the file")
        self.assertEqual(again.entries[0]["mode"], "versus", "newest first")
        self.assertEqual(again.best_single(), 420)
        self.assertEqual(len(again.of_mode("single")), 1)
        self.assertEqual(len(again.of_mode("versus")), 1)

    def test_a_damaged_file_does_not_break_the_game(self):
        for junk in ("not json at all", "[]", '{"version": 1}', '{"entries": "nope"}'):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(junk)
            self.assertEqual(Records(self.path).entries, [], f"junk file: {junk!r}")
        # a file that holds a usable entry next to a broken one keeps the usable one
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"entries": [{"nope": 1}, {"mode": "single", "score": 7}]}')
        records = Records(self.path)
        self.assertEqual([entry["score"] for entry in records.entries], [7])

    def test_the_list_is_capped_and_newest_first(self):
        records = Records(self.path)
        for i in range(Records.MAX_ENTRIES + 12):
            records.add({"mode": "single", "score": i})
        self.assertEqual(len(records), Records.MAX_ENTRIES, "the list keeps a fixed size")
        self.assertEqual(records.entries[0]["score"], Records.MAX_ENTRIES + 11, "newest first")
        self.assertEqual(len(records.shown()), Records.SHOWN_ENTRIES)

    def test_it_records_a_solo_run_and_a_match(self):
        ensure_display()
        records = Records(self.path)
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        game.start_timing()
        game.players[0].score = 321
        entry = records.add_single(game)
        self.assertEqual(entry["mode"], "single")
        self.assertEqual(entry["score"], 321)
        self.assertEqual(entry["size"], f"{game.field_width}x{game.field_height}")
        self.assertEqual(entry["difficulty"], game.difficulty)
        self.assertRegex(entry["time"], r"^\d{2}:\d{2}:\d{3}$")

        p1, p2 = Player(), Player()
        assign_versus_roles(p1, p2)
        versus = MazeGame(gamemode=GameMode.DOUBLE, size_preset="small", players=[p1, p2])
        p1.score, p2.score = 900, 300
        versus_pair([p1, p2])[1].eaten = 2
        match = records.add_versus(versus, "P1 WINS")
        self.assertEqual(match["mode"], "versus")
        self.assertEqual(match["winner"], "P1 WINS")
        self.assertEqual(match["scores"], [900, 300])
        self.assertIn(2, match["deaths"])
        self.assertTrue(records.save())
        self.assertTrue(os.path.getsize(self.path) > 0)

    def test_clear_forgets_everything(self):
        records = Records(self.path)
        records.add({"mode": "single", "score": 1})
        self.assertTrue(records.clear())
        self.assertEqual(len(records), 0)
        self.assertEqual(Records(self.path).entries, [], "the file is emptied as well")


class TestRecordsScreen(unittest.TestCase):

    def setUp(self):
        ensure_display()
        self.dir = tempfile.TemporaryDirectory()
        self.records = Records(os.path.join(self.dir.name, "records.json"))

    def tearDown(self):
        self.dir.cleanup()

    def test_the_rows_read_well(self):
        self.records.add({"mode": "single", "time": "00:12:345", "score": 420, "size": "8x8",
                          "difficulty": "normal", "at": "2026-09-20 03:40"})
        self.records.add({"mode": "versus", "winner": "P1 WINS", "scores": [900, 300],
                          "deaths": [0, 2], "at": "2026-09-20 03:41"})
        text = "\n".join(self.records.row_text(entry) for entry in self.records.shown())
        for wanted in ("SINGLE", "00:12:345", "pts 420", "VERSUS", "P1 WINS", "deaths 2"):
            self.assertIn(wanted, text)

    def test_the_screen_is_drawn(self):
        self.records.add({"mode": "single", "time": "00:12:345", "score": 420, "size": "8x8",
                          "difficulty": "normal", "at": "2026-09-20 03:40"})
        self.records.add({"mode": "versus", "winner": "P1 WINS", "scores": [900, 300],
                          "deaths": [0, 2], "at": "2026-09-20 03:41"})
        screen = RecordsScreen(self.records, back_cb=lambda: None)
        surface = pg.Surface(SCREEN_SIZE)
        screen.life = RecordsScreen.INPUT_LOCK  # drawn fully, not half faded in
        screen.draw(surface)
        dark = sum(1 for y in range(0, SCREEN_SIZE[1], 9) for x in range(0, SCREEN_SIZE[0], 9)
                   if sum(surface.get_at((x, y))[:3]) < 200)
        self.assertGreater(dark, 50, "the list panel has to be drawn")
        shot = save_shot(surface, "_shot_records.png")
        self.assertTrue(os.path.getsize(shot) > 0)

    def test_an_empty_history_is_drawn_too(self):
        screen = RecordsScreen(self.records, back_cb=lambda: None)
        self.assertEqual(self.records.shown(), [])
        screen.draw(pg.Surface(SCREEN_SIZE))  # must not raise on an empty history

    def test_the_clear_button_never_collides_with_the_list(self):
        """the button lives in the footer, so a short list or a small window cannot overlap it"""
        for i in range(14):
            self.records.add({"mode": "single", "time": "00:12:345", "score": 400 + i, "size": "8x8",
                              "difficulty": "normal", "at": "2026-09-20 03:40"})
        self.records.add({"mode": "versus", "winner": "P2 WINS", "scores": [100, 300],
                          "deaths": [1, 0], "at": "2026-09-20 03:41"})
        for size in ((1200, 800), (900, 600), (1600, 900), (700, 500)):
            pg.display.set_mode(size, pg.RESIZABLE)
            screen = RecordsScreen(self.records, back_cb=lambda: None)
            panel = pg.Rect(screen.pos, screen._panel.get_size())
            button = screen.clear_btn.rect
            self.assertTrue(panel.contains(button),
                            f"the button stays inside the panel at {size}")
            self.assertGreaterEqual(button.top, panel.top + screen._body_bottom,
                                    f"the button sits below the list at {size}")
            self.assertEqual(screen._body_bottom + screen.PAD + max(
                make_font(screen.HINT_SIZE).get_height(), screen.CLEAR_SIZE[1]), panel.height,
                             f"the footer is the last band of the panel at {size}")
        pg.display.set_mode(SCREEN_SIZE, pg.RESIZABLE)

    def test_a_short_list_still_fills_the_screen(self):
        self.records.add({"mode": "single", "score": 1})
        screen = RecordsScreen(self.records, back_cb=lambda: None)
        self.assertGreaterEqual(screen._panel.get_width(),
                                int(SCREEN_SIZE[0] * RecordsScreen.WIDTH_RATIO),
                                "the panel is wide even when there is little to list")

    def test_a_key_goes_back_and_clear_forgets_the_list(self):
        self.records.add({"mode": "single", "score": 5})
        went_back = []
        screen = RecordsScreen(self.records, back_cb=lambda: went_back.append(True))
        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_ESCAPE, "mod": 0, "unicode": ""})

        screen.handle_events([key])
        self.assertEqual(went_back, [], "the key that opened the screen cannot close it at once")
        screen.life = RecordsScreen.INPUT_LOCK + 1
        screen.handle_events([key])
        self.assertEqual(went_back, [True], "afterwards a key returns to the menu")

        screen.handle_events([pg.event.Event(pg.MOUSEBUTTONDOWN,
                                             {"pos": screen.clear_btn.rect.center, "button": 1})])
        self.assertEqual(len(self.records), 0, "the clear button empties the list")
        self.assertEqual(Records(self.records.path).entries, [], "on disk as well")

    def test_the_menu_opens_it(self):
        menu = WelcomeScreen(SCREEN_SIZE)
        menu.draw(pg.Surface(SCREEN_SIZE))
        self.assertGreater(menu.records_btn.rect.width, 0, "the button needs a rectangle")
        app = game_main.Game()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app.records = Records(os.path.join(tmp.name, "records.json"))
        self.assertIsInstance(app.records, Records)
        # a bound method is built anew on every access, so compare what it is bound to
        self.assertIs(app.welcome.records_btn.callback.__self__, app)
        # self.assertEqual(app.welcome.records_btn.callback.__func__, app.open_records.__func__)
        app.open_records()
        self.assertIs(app.current_screen, app.records_screen)
        app.close_records()
        self.assertIs(app.current_screen, app.welcome)


class TestRecordsInTheRealFlow(unittest.TestCase):
    """the hooks live in the game loop, so drive the real loop and look at the store afterward"""

    def setUp(self):
        ensure_display()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "records.json")

    def new_app(self):
        app = game_main.Game()
        app.sound_on = False
        app.clock = IdleClock()
        app.records = Records(self.path)  # keep the record file of the repo clean
        return app

    def test_a_finished_solo_maze_is_written_down(self):
        app = self.new_app()

        def step(state):
            if state["stage"] == "start" and isinstance(app.current_screen, WelcomeScreen):
                click(app.welcome.single_btn.rect)
                state["stage"] = "playing"
            elif state["stage"] == "playing" and isinstance(app.current_screen, MazeGame):
                game = app.maze_game
                game.players[0].pos = V(game.maze.end)  # the solo player reaches the exit
                game.players[0].pos_next = V(game.players[0].pos)
                game.handle_events([])  # posts USEREVENT + 2, the loop writes the record
                state["stage"] = "recorded"
            elif state["stage"] == "recorded" and app.records.entries:
                raise FlowDone()

        drive(app, step)
        entries = Records(self.path).entries
        self.assertEqual(len(entries), 1, "the finished maze has to be in the records")
        self.assertEqual(entries[0]["mode"], "single")
        self.assertEqual(entries[0]["size"], f"{app.maze_game.field_width}x{app.maze_game.field_height}")
        self.assertEqual(entries[0]["score"], app.maze_game.players[0].score)

    def test_a_settled_versus_match_is_written_down(self):
        app = self.new_app()

        def step(state):
            if state["stage"] == "start" and isinstance(app.current_screen, WelcomeScreen):
                click(app.welcome.double_btn.rect)
                state["stage"] = "playing"
            elif state["stage"] == "playing" and isinstance(app.current_screen, MazeGame):
                game = app.maze_game
                game.players[0].score, game.players[1].score = 900, 300
                click(game.hud.pause_btn.rect)
                state["stage"] = "paused"
            elif state["stage"] == "paused" and app.state == game_main.GameState.PAUSED:
                click(app.maze_game.pause_screen.menu_btn.rect)
                state["stage"] = "leaving"
            elif state["stage"] == "leaving" and app.records.entries:
                raise FlowDone()

        drive(app, step)
        entries = Records(self.path).entries
        self.assertEqual(len(entries), 1, "leaving the match settles it and writes one record")
        self.assertEqual(entries[0]["mode"], "versus")
        self.assertEqual(entries[0]["winner"], "P1 WINS")
        self.assertEqual(entries[0]["scores"], [900, 300])


if __name__ == "__main__":
    unittest.main(verbosity=2)
