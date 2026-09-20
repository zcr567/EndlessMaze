"""
Self-check of the three user-interface features:

  * the limited vision mode the menu can switch on, which hides the maze outside the area around
    the players;
  * the solo HUD, which shows the score as "pts N" instead of the skull counter;
  * the three stat lines of the transition between two mazes: the time of the maze that was just
    finished, its score and the hint, all as wide as each other, sitting in the widest of the three
    areas the two gateway lines cut the screen into.

    python -m unittest Tests.test_ui -v
"""

import math
import os
import sys
import tempfile
import unittest
import pygame as pg

import main as game_main  # noqa: F401  (initialises pygame exactly like the game does)
from effects import Fade, update_effects
from widgets import (GameGameTrans, GameMode, HUD, MazeGame, Player, SinglePlayerHUD, VersusHUD,
                     VISION_PRESETS, WelcomeScreen, assign_versus_roles)

# noinspection PyPep8Naming
from vectors import Vector as V

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# (history) never write the record file of the repository from a test
os.environ.setdefault("MAZE_RECORDS_FILE", os.path.join(tempfile.gettempdir(), "maze_test_records.json"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


SCREEN_SIZE = (1200, 800)
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")


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


def wall_pixels(game):
    """screen positions of the wall segments the maze draws, one per wall"""
    positions = []
    for row in range(game.field_height * 2 + 1):
        for col in range(game.field_width * 2 + 1):
            if game.inst[row][col] != 0:
                continue
            if row % 2 == 0 and col % 2 == 1:  # a horizontal wall segment
                positions.append((int(game.region[0] + game.cell_width * (col // 2) + game.cell_width // 2),
                                  int(game.region[1] + game.cell_width * (row // 2))))
            elif row % 2 == 1 and col % 2 == 0:  # a vertical wall segment
                positions.append((int(game.region[0] + game.cell_width * (col // 2)),
                                  int(game.region[1] + game.cell_width * (row // 2) + game.cell_width // 2)))
    return positions


def gateway_lines(trans):
    """the two gateway lines as rectangles, exactly the way _draw_path_1 draws them"""
    sw, sh = pg.display.get_window_size()
    a1 = trans.p1[0] + (trans.p1[1] - trans.p1[0]) * trans.intp1.get()
    a2 = trans.p2[0] + (trans.p2[1] - trans.p2[0]) * trans.intp1.get()
    if trans.end_edge == 0:
        a1, a2 = V(a1[0], 0), V(a2[0], 0)
    elif trans.end_edge == 1:
        a1, a2 = V(sw, a1[1]), V(sw, a2[1])
    elif trans.end_edge == 2:
        a1, a2 = V(a1[0], sh), V(a2[0], sh)
    elif trans.end_edge == 3:
        a1, a2 = V(0, a1[1]), V(0, a2[1])
    half = trans.line_width // 2 + 1
    rects = []
    for point in (a1, a2):
        end = point - trans.direction * trans.line_length
        rects.append(pg.Rect(min(point[0], end[0]) - half, min(point[1], end[1]) - half,
                             abs(point[0] - end[0]) + 2 * half, abs(point[1] - end[1]) + 2 * half))
    return rects


class TestLimitedVision(unittest.TestCase):

    def setUp(self):
        ensure_display()
        MazeGame.limited_vision = False

    def tearDown(self):
        MazeGame.limited_vision = False

    def test_the_menu_offers_the_vision_row(self):
        menu = WelcomeScreen(SCREEN_SIZE)
        self.assertEqual(list(VISION_PRESETS), ["full", "limited"])
        self.assertEqual(menu.vision_selector.value, "full", "full vision is the default")
        surface = pg.Surface(SCREEN_SIZE)
        menu.draw(surface)  # the row has to be drawn with the rest of the menu
        self.assertTrue(menu.vision_selector.rect.width > 0, "the row needs a real rectangle")

    def test_full_vision_is_the_default(self):
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        self.assertFalse(game.limited_vision)

    def test_the_fog_hides_far_walls_and_keeps_near_ones(self):
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="medium")
        center = game.players[0].cur_anim.get_position()
        radius = game.cell_width * game.VISION_RADIUS_CELLS
        walls = wall_pixels(game)
        near = [pos for pos in walls
                if math.hypot(pos[0] - center[0], pos[1] - center[1]) < radius * 0.5]
        far = [pos for pos in walls
               if math.hypot(pos[0] - center[0], pos[1] - center[1]) > radius * 1.5]
        self.assertTrue(near, "the maze should have walls right around the player")
        self.assertTrue(far, "and walls far away from it")

        plain = pg.Surface(SCREEN_SIZE)
        game.limited_vision = False
        game.draw(plain)
        fogged = pg.Surface(SCREEN_SIZE)
        game.limited_vision = True
        game.draw(fogged)

        self.assertEqual(plain.get_at(far[0])[:3], MazeGame.MAZE_EDGE_COLOR,
                         "a far wall is drawn in full vision")
        self.assertEqual(fogged.get_at(far[0])[:3], game.bg_color,
                         "and the fog has to take it away")
        self.assertEqual(plain.get_at(near[0])[:3], MazeGame.MAZE_EDGE_COLOR)
        self.assertEqual(fogged.get_at(near[0])[:3], MazeGame.MAZE_EDGE_COLOR,
                         "a wall next to the player stays visible")

        shot = save_shot(fogged, "_shot_limited_vision.png")
        self.assertTrue(os.path.getsize(shot) > 0)

    def test_the_fog_keeps_the_player_on_screen(self):
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="medium")
        game.limited_vision = True
        surface = pg.Surface(SCREEN_SIZE)
        game.draw(surface)
        center = game.players[0].cur_anim.get_position()
        around = [(int(center[0]) + dx, int(center[1]) + dy)
                  for dx in range(-12, 13, 4) for dy in range(-12, 13, 4)]
        drawn = [surface.get_at(pos)[:3] for pos in around
                 if surface.get_at(pos)[:3] != game.bg_color]
        self.assertTrue(drawn, "the player stays drawn on top of the fog")

    def test_the_map_never_flashes_up_during_the_menu_wipe(self):
        """the menu builds the maze before the match starts, so that maze has to carry the mode from
        its first drawn frame - otherwise the whole map shows up once while the screen wipes in"""
        app = game_main.Game()
        app.set_vision("limited")
        app.start_single_player()
        transition = app.current_screen
        game = transition.new_sc
        self.assertTrue(game.limited_vision, "the maze of the menu transition carries the mode")

        surface = pg.Surface(SCREEN_SIZE)
        for _ in range(2 * transition.HALF_DURATION + 5):
            update_effects()
            transition.draw(surface)
        center = game.players[0].cur_anim.get_position()
        radius = game.cell_width * game.VISION_RADIUS_CELLS
        far = [pos for pos in wall_pixels(game)
               if math.hypot(pos[0] - center[0], pos[1] - center[1]) > radius * 1.5]
        self.assertTrue(far, "the maze should have walls far away from the player")
        self.assertEqual(surface.get_at(far[0])[:3], game.bg_color,
                         "the map has to stay hidden all through the wipe")
        shot = save_shot(surface, "_shot_menu_transition_fog.png")
        self.assertTrue(os.path.getsize(shot) > 0)

    def test_the_menu_choice_reaches_the_game(self):
        app = game_main.Game()
        self.assertFalse(app.limited_vision)
        app.set_vision("limited")
        self.assertTrue(app.limited_vision)
        app.set_vision("full")
        self.assertFalse(app.limited_vision)


class TestSoloHUD(unittest.TestCase):

    def setUp(self):
        ensure_display()
        MazeGame.limited_vision = False

    def test_the_solo_hud_shows_points_and_no_counter(self):
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        self.assertIsInstance(game.hud, SinglePlayerHUD, "the solo mode builds the solo HUD")
        hud = game.hud
        self.assertIsNotNone(hud.fetch_points_cb)
        self.assertEqual(hud._points(0), 0)

        game.players[0].score = 1234
        self.assertEqual(hud._points(0), 1234)
        wide = hud._points_text(0).get_width()
        game.players[0].score = 0
        self.assertGreater(wide, hud._points_text(0).get_width(),
                           "the pts line has to show the score")

        game.players[0].score = 1234
        counters = []
        real_score = HUD._draw_score

        def count_score(inst, *args, **kwargs):
            counters.append(args)
            return real_score(inst, *args, **kwargs)

        HUD._draw_score = count_score
        try:
            surface = pg.Surface(SCREEN_SIZE)
            surface.fill((0, 0, 0))
            hud.draw(surface)
        finally:
            HUD._draw_score = real_score
        self.assertEqual(counters, [], "the solo HUD must draw no counter, the skull included")
        shot = save_shot(surface, "_shot_solo_hud.png")
        self.assertTrue(os.path.getsize(shot) > 0)

    def test_the_timer_is_centred_and_reads_the_timer_of_utils(self):
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        game.start_timing()
        surface = ensure_display()

        timer = game.time_surface()
        self.assertRegex(getattr(game, "_time_str"), r"^\d{2}:\d{2}:\d{3}$",
                         "the time comes from utils.Timer.get_str()")
        self.assertGreaterEqual(MazeGame.TIME_FONT_SIZE, 40, "the time is drawn a bit large")
        self.assertGreater(MazeGame.TIME_FONT_SIZE, HUD.SCORE_FONT_SIZE,
                           "and larger than the rest of the HUD text")
        digits = pg.mask.from_threshold(timer, MazeGame.TIME_COLOR, (10, 10, 10, 255))
        self.assertGreater(digits.count(), 0, "the timer has to draw its digits")

        pos = game.timer_pos(timer)
        self.assertEqual(pos[0], (SCREEN_SIZE[0] - timer.get_width()) // 2,
                         "the time is centred on the screen")
        self.assertGreaterEqual(pos[1], 0)
        if game.region[1] >= timer.get_height() + 2:
            self.assertLessEqual(pos[1] + timer.get_height(), int(game.region[1]),
                                 "and it stays in the free strip above the maze")

        # frozen while paused: the same surface comes back and the time stands still
        game.pause_timing()
        frozen = game.time_surface()
        for _ in range(3):
            self.assertIs(game.time_surface(), frozen, "a frozen time is not rendered again")

        game.draw(surface)
        game.hud.draw(surface)
        around = pg.Surface((timer.get_width(), timer.get_height()))
        around.blit(surface, (0, 0), pg.Rect(pos[0], pos[1], timer.get_width(), timer.get_height()))
        self.assertGreater(pg.mask.from_threshold(around, MazeGame.TIME_COLOR, (10, 10, 10, 255)).count(),
                           0, "and it has to end up on the screen, in the middle of the top row")
        shot = save_shot(surface, "_shot_timer.png")
        self.assertTrue(os.path.getsize(shot) > 0)

    def test_the_versus_hud_drops_the_eat_counter(self):
        """the versus HUD keeps the skull for the deaths, but the eat counter of the old layout is
        gone: a round only ever pays the player who won it"""
        p1, p2 = Player(), Player()
        assign_versus_roles(p1, p2)
        game = MazeGame(gamemode=GameMode.DOUBLE, size_preset="small", players=[p1, p2])
        self.assertIsInstance(game.hud, VersusHUD, "the versus mode builds the versus HUD")
        counters = []
        real_score = HUD._draw_score

        def count_score(inst, *args, **kwargs):
            counters.append(args)
            return real_score(inst, *args, **kwargs)

        HUD._draw_score = count_score
        try:
            game.hud.draw(pg.Surface(SCREEN_SIZE))
        finally:
            HUD._draw_score = real_score
        self.assertEqual(counters, [], "no icon counter is drawn by the versus HUD any more")


class TestTransitionStats(unittest.TestCase):

    def setUp(self):
        ensure_display()
        MazeGame.limited_vision = False

    @staticmethod
    def build_transition(seconds=12.345, score=777):
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        game.start_timing()
        game.timer.get = lambda: seconds  # a fixed time for the maze that was just finished
        player = game.players[0]
        player.pos = V(game.maze.end)
        player.pos_next = V(player.pos)
        game.handle_events([])
        pg.event.get()
        game.players[0].score = score
        return game, GameGameTrans(game)

    def test_the_three_lines_are_equally_wide(self):
        game, trans = self.build_transition()
        self.assertEqual(trans.time_str, "00:12:345", "the stats show the finished maze's time")
        self.assertEqual(trans._stats_texts(), ["00:12:345", "score: 777", "press any key to continue"])

        lines, sizes = trans._stats_lines()
        self.assertEqual(len({line.get_width() for line in lines}), 1,
                         "the three lines have to come out exactly as long as each other")
        self.assertGreater(max(sizes), min(sizes), "and each of them keeps a size of its own")
        self.assertGreaterEqual(min(sizes), GameGameTrans.STATS_MIN_LINE_SIZE * 0.95,
                                "the smallest line stays readable")

        narrow, narrow_sizes = trans._stats_lines(max_width=120)
        self.assertEqual(len({line.get_width() for line in narrow}), 1,
                         "they stay equally long when the space is tight")
        self.assertLessEqual(max(line.get_width() for line in narrow), 120,
                             "and they fit into the space they are given")

    def test_the_stats_do_not_change_while_the_timer_runs_on(self):
        game, trans = self.build_transition()
        game.timer.get = lambda: 99.0  # the old game's timer keeps running after the round
        self.assertEqual(trans._stats_texts()[0], "00:12:345",
                         "the stats are frozen at the time the maze was finished")

    def test_the_block_sits_in_the_widest_gap_and_lined_up_with_the_player(self):
        game, trans = self.build_transition()
        trans._build_stats()
        block = pg.Rect(trans._stats_pos[0], trans._stats_pos[1],
                        trans._stats_surf.get_width(), trans._stats_surf.get_height())
        spaces = trans._stats_spaces()
        widest = max(spaces, key=lambda space: space[2] * space[3])
        self.assertTrue(pg.Rect(widest).contains(block),
                        "the block has to sit inside the widest of the three gaps")
        for rect in gateway_lines(trans):
            self.assertFalse(block.colliderect(rect),
                             "the block must not touch a gateway line")
        player_x, player_y = trans.p0[0][0], trans.p0[0][1]
        if trans.end_edge in (1, 3):  # horizontal lines: the block follows the player's x
            aligned = abs(block.centerx - player_x) <= 1
            clamped = block.left == widest[0] or block.right == widest[0] + widest[2]
        else:                          # vertical lines: it follows the player's y
            aligned = abs(block.centery - player_y) <= 1
            clamped = block.top == widest[1] or block.bottom == widest[1] + widest[3]
        self.assertTrue(aligned or clamped,
                        "the block is lined up with the player, or clamped into the gap if that "
                        "would push it off screen")

    def test_the_stats_fly_in_from_behind_the_player(self):
        game, trans = self.build_transition()
        trans.direction = V(0, -1)  # a player facing up
        self.assertEqual(tuple(trans._stats_fly_offset(0)), (0, trans.STATS_FLY_DISTANCE),
                         "facing up, the stats start below the player")
        self.assertEqual(tuple(trans._stats_fly_offset(1)), (0, 0), "and land on their spot")
        trans.direction = V(1, 0)  # a player facing right
        self.assertEqual(tuple(trans._stats_fly_offset(0)), (-trans.STATS_FLY_DISTANCE, 0),
                         "facing right, they come in from the left")

    def test_the_stats_fade_out_on_the_key_press(self):
        game, trans = self.build_transition()
        surface = ensure_display()
        trans._ani_p = 1
        trans.life = 0
        trans.draw(surface)
        self.assertIsNotNone(trans._stats_surf, "the first stats frame builds the block")
        for _ in range(trans.STATS_ENTER_DURATION + 2):
            trans.draw(surface)
        self.assertIsNone(trans._stats_enter, "the fly-in entrance has to finish")
        self.assertGreater(pg.mask.from_surface(trans._stats_surf).count(), 0)

        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "})
        trans.handle_events([key])
        self.assertIsInstance(trans._stats_fade, Fade, "the key press starts the Fade effect")
        for _ in range(trans.PHASE_TIMES[2] + 2):
            update_effects()
        self.assertEqual(pg.mask.from_surface(trans._stats_surf).count(), 0,
                         "the fade-out has to take the stats away")

    def test_the_whole_transition_draws_the_stats(self):
        game, trans = self.build_transition(score=4242)
        surface = ensure_display()
        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "})
        pg.event.get()  # drop the game events the maze posted while it was built
        shots = 0
        for i in range(200):
            update_effects()
            trans.draw(surface)
            # the player waits a while before pressing a key, like a human reading the stats
            trans.handle_events([key] if i == trans.PHASE_TIMES[0] + 30 else [])
            if i == trans.PHASE_TIMES[0] + 28:
                shots = save_shot(surface, "_shot_transition_stats.png")
            if any(event.type == pg.USEREVENT + 3 for event in pg.event.get()):
                break
        self.assertTrue(os.path.getsize(shots) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
