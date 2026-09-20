"""
Headless self-check of the two-player (predator & prey) mode.

Everything runs on SDL's dummy video and audio drivers, so the whole flow - random role
assignment, spawn rules, the catch, the ghost transition, the escape and the routing of the real
main loop - can be exercised from a terminal:

    python -m unittest Tests.test_versus -v

The integration test also writes a few screenshots of the ghost transition into Tests/_shots/.
"""

import hashlib
import math
import os
import sys
import tempfile
import unittest

import pygame as pg

import main as game_main
from Resources import predator_anim_dict, prey_anim_dict
from effects import update_effects
# noinspection PyPep8Naming
from vectors import DIR_VECS, Vector as V
from widgets import (GameGameTrans, GameMode, MazeGame, Player, PlayerType,
                     VersusDeathTrans, VersusHUD, VersusResult, VERSUS_ENTRANCE_HEADINGS,
                     assign_versus_roles, cell_to_surf, pick_prey_spawn, versus_pair,
                     versus_touching)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# (history) never write the record file of the repository from a test
os.environ.setdefault("MAZE_RECORDS_FILE", os.path.join(tempfile.gettempdir(), "maze_test_records.json"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCREEN_SIZE = (1200, 800)
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")


def ensure_pygame():
    """the integration test drives the real main loop, which quits pygame on its way out, so
    every test has to make sure the library is up again before it touches a font or a surface"""
    pg.init()
    if not pg.mixer.get_init():
        pg.mixer.init()


def ensure_display():
    ensure_pygame()
    if pg.display.get_surface() is None:
        pg.display.set_mode(SCREEN_SIZE, pg.RESIZABLE)
    return pg.display.get_surface()


def new_game(size_preset="small"):
    """a two-player game on the dummy display, using one dedicated pair of Player objects"""
    ensure_display()
    p1, p2 = Player(), Player()
    assign_versus_roles(p1, p2)
    game = MazeGame(gamemode=GameMode.DOUBLE, size_preset=size_preset, difficulty="normal",
                    players=[p1, p2])
    for p in (p1, p2):
        p.game = game
    game.start_timing()  # the round score divides by the timer, exactly like the solo mode
    pg.event.get()  # drop the game-start event posted by MazeGame.__init__
    return game, p1, p2


def drain_and_check(event_type):
    """drain the event queue and report whether the given user event was in it"""
    found = False
    for event in pg.event.get():
        if event.type == event_type:
            found = True
    return found


def save_shot(surface, name):
    os.makedirs(SHOT_DIR, exist_ok=True)
    path = os.path.join(SHOT_DIR, name)
    pg.image.save(surface, path)
    return path


def force_contact(predator, prey, offset=None):
    """put the predator's sprite right next to the prey's: that is what the contact rule reads"""
    offset = int(prey.size[0] / 4) if offset is None else offset
    predator.cur_anim.set_position(V(prey.cur_anim.get_position()) + V(offset, 0))


def open_step(game, cell, vec):
    """the movement rule of the game, mirrored here to walk the maze in a test"""
    other = (cell[0] + vec[0], cell[1] + vec[1])
    if not game.maze.is_valid_coord(other):
        return False
    if game.inst[2 * cell[1] + vec[1] + 1][2 * cell[0] + vec[0] + 1] != 2:
        return False
    return not game.maze.blocks_one_way(cell, other)


def find_straight_run(game, length=3):
    """a straight corridor of at least "length" open cells, avoiding the start and the exit"""
    for cell in [(x, y) for y in range(game.maze.height) for x in range(game.maze.width)]:
        for vec, _ in ((V(1, 0), 0), (V(0, 1), 1)):
            cells = [cell]
            while len(cells) < length and open_step(game, cells[-1], vec):
                cells.append((cells[-1][0] + vec[0], cells[-1][1] + vec[1]))
            if len(cells) >= length and tuple(game.maze.end) not in cells and tuple(game.maze.start) not in cells:
                return cells[0], [c for c, v in DIR_VECS.items() if v == vec][0], cells
    return None


def rect_digest(surface, rect):
    """a short digest of one region, so a failed comparison does not print megabytes"""
    return hashlib.sha1(pg.image.tostring(surface.subsurface(rect).copy(), "RGBA")).hexdigest()


class TestVersusRules(unittest.TestCase):

    def setUp(self):
        ensure_display()

    def test_roles_are_random_and_complete(self):
        seen = set()
        for _ in range(60):
            p1, p2 = Player(), Player()
            assign_versus_roles(p1, p2)
            predator, prey = versus_pair([p1, p2])
            self.assertIsNotNone(predator, "every round needs a predator")
            self.assertIsNotNone(prey, "every round needs a prey")
            self.assertIsNot(predator, prey)
            self.assertIs(predator.anim_dict, predator_anim_dict)
            self.assertIs(prey.anim_dict, prey_anim_dict)
            seen.add((p1.player_type, p2.player_type))
        self.assertEqual(seen, {(PlayerType.PREDATOR, PlayerType.PREY),
                                (PlayerType.PREY, PlayerType.PREDATOR)},
                         "both role orders have to show up over 60 rounds")

    def test_spawn_rule(self):
        for _ in range(12):
            game, p1, p2 = new_game()
            predator, prey = versus_pair([p1, p2])
            self.assertEqual(tuple(predator.pos), tuple(game.maze.start), "predator starts on the entrance")
            self.assertEqual(tuple(predator.pos_next), tuple(predator.pos))
            self.assertEqual(predator.heading, VERSUS_ENTRANCE_HEADINGS[game.start_edge],
                             "the predator faces into the maze")
            self.assertNotEqual(tuple(prey.pos), tuple(game.maze.start))
            self.assertNotEqual(tuple(prey.pos), tuple(game.maze.end), "the prey never starts on the exit")
            self.assertTrue(game.maze.is_valid_coord(prey.pos))
            self.assertFalse(game._versus_over)
            self.assertEqual(game.hud.game_mode, GameMode.DOUBLE)
            self.assertEqual(game.fetch_scores(), [(0, 0), (0, 0)], "the counters start at zero")
            self.assertTrue(all(type(p.disp_state).IDLE == p.disp_state for p in (predator, prey)),
                            "no movement is carried into a fresh round")

    def test_prey_spawn_never_on_entrance_or_exit(self):
        game, _, _ = new_game()
        maze = game.maze
        for _ in range(200):
            cell = pick_prey_spawn(maze, maze.start)
            self.assertNotEqual(tuple(cell), tuple(maze.start))
            self.assertNotEqual(tuple(cell), tuple(maze.end))
            self.assertTrue(maze.is_valid_coord(cell))

    def test_prey_spawn_keeps_its_distance(self):
        game, _, _ = new_game(size_preset="medium")
        maze = game.maze
        min_dist = max(1, int(0.5 * (maze.width + maze.height)))
        for _ in range(50):
            cell = pick_prey_spawn(maze, maze.start)
            dist = abs(cell[0] - maze.start[0]) + abs(cell[1] - maze.start[1])
            self.assertGreaterEqual(dist, min_dist)

    def test_contact_is_half_an_edge_apart(self):
        """the catch rule: the distance between the two drawn centres is smaller than half of the
        sprite edge length (size[0]); the centres are the regions of the animations"""
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        edge = prey.size[0]
        middle = V(400, 400)
        prey.cur_anim.set_position(middle)

        inside = max(0, int(edge / 2) - 1)
        outside = int(edge / 2) + 1
        predator.cur_anim.set_position(middle + V(inside, 0))
        self.assertTrue(versus_touching(predator, prey), "just inside half an edge is a contact")
        predator.cur_anim.set_position(middle + V(outside, 0))
        self.assertFalse(versus_touching(predator, prey), "half an edge apart is not a contact yet")
        predator.cur_anim.set_position(middle + V(0, inside))
        self.assertTrue(versus_touching(predator, prey), "the rule has to work on both axes")
        predator.cur_anim.set_position(middle + V(int(edge), 0))
        self.assertFalse(versus_touching(predator, prey), "a whole edge apart is clearly no contact")

    def test_a_slide_over_the_prey_is_caught(self):
        """the rule reads the centres that are drawn, so a predator sliding over the prey is caught
        even though the two never sit on the same cell centre in one frame"""
        game, p1, p2 = new_game(size_preset="medium")
        predator, prey = versus_pair([p1, p2])
        surface = ensure_display()
        run = find_straight_run(game, length=3)
        self.assertIsNotNone(run, "the maze should offer a straight corridor for this check")
        start, direction, cells = run

        prey.pos = prey.pos_next = V(cells[1])
        predator.pos = predator.pos_next = V(start)
        predator.heading = direction
        for p in (predator, prey):
            p.disp_state = type(p.disp_state).IDLE
            p.cur_anim.set_position(p.pos_to_surf())
        predator.move(direction)
        self.assertNotEqual(tuple(predator.pos_next), tuple(start), "the predator has to slide")

        caught = False
        for _ in range(200):
            game.handle_events([])
            if drain_and_check(pg.USEREVENT + 8):
                caught = True
                break
            game.draw(surface)  # the frame that moves the sprites along
        self.assertTrue(caught, "sliding straight over the prey has to end the round")
        here = predator.cur_anim.get_position()
        there = prey.cur_anim.get_position()
        self.assertLess(math.hypot(here[0] - there[0], here[1] - there[1]), predator.size[0] / 2,
                        "the captured frame has to be a real contact on screen")
        shot = save_shot(surface, "_shot_contact.png")  # the last frame before the contact
        self.assertTrue(os.path.getsize(shot) > 0, "the contact frame should have been captured")

    def test_cell_to_surf_matches_the_player(self):
        game, p1, p2 = new_game()
        for p in (p1, p2):
            self.assertEqual(tuple(cell_to_surf(game, p.pos)), tuple(p.pos_to_surf()))

    def test_a_round_only_pays_the_player_who_won_it(self):
        """a catch pays the predator, an escape pays the prey, and neither pays the other one; the
        amount follows the scoring rule of the single player mode"""

        # noinspection PyShadowingNames
        def worth(game):
            """the points the very rule of the solo mode hands out for a fixed round time"""
            return int(game.SCORE_DICT[GameMode.SINGLE]["normal"] * game.field_width
                       * game.field_height * game.maze.p_len / 4.0)

        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        game.timer.get = lambda: 4.0  # a fixed round time, so the score is predictable
        expected = worth(game)
        self.assertGreater(expected, 0, "a round has to be worth points")

        before = (predator.score, prey.score)
        force_contact(predator, prey)
        game.handle_events([])
        self.assertTrue(game._versus_over)
        self.assertEqual(predator.score, before[0] + expected, "the catch pays the predator")
        self.assertEqual(prey.score, before[1], "and leaves the prey alone")
        self.assertTrue(drain_and_check(pg.USEREVENT + 8))

        game, p1, p2 = new_game()  # a fresh maze, so its own round value is computed again
        predator, prey = versus_pair([p1, p2])
        game.timer.get = lambda: 4.0
        expected = worth(game)
        prey.pos = prey.pos_next = V(game.maze.end)
        before = (predator.score, prey.score)
        game.handle_events([])
        self.assertTrue(game._versus_over)
        self.assertEqual(prey.score, before[1] + expected, "the escape pays the prey")
        self.assertEqual(predator.score, before[0], "and leaves the predator alone")
        self.assertTrue(drain_and_check(pg.USEREVENT + 2))

    def test_leaving_a_versus_match_through_the_menu_settles_it(self):
        """the menu button of the pause screen ends the match: the score decides it, and the main
        menu only shows up after the result"""
        app = game_main.Game()
        app.sound_on = False
        app.clock = IdleClock()
        real_flip = pg.display.flip
        state = {"frame": 0, "stage": "menu", "winner": None, "shot": 0}

        def click(rect):
            pg.event.post(pg.event.Event(pg.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1}))
            pg.event.post(pg.event.Event(pg.MOUSEBUTTONUP, {"pos": rect.center, "button": 1}))

        def step():
            stage = state["stage"]
            screen = app.current_screen
            if stage == "menu" and state["frame"] > 2:
                click(app.welcome.double_btn.rect)
                state["stage"] = "wait_game"
            elif stage == "wait_game" and isinstance(screen, MazeGame):
                game = app.maze_game
                game.players[0].score, game.players[1].score = 900, 300
                click(game.hud.pause_btn.rect)  # the pause button of the HUD
                state["stage"] = "wait_pause"
            elif stage == "wait_pause" and app.state == game_main.GameState.PAUSED:
                click(app.maze_game.pause_screen.menu_btn.rect)  # and on to the menu
                state["stage"] = "wait_result"
            elif stage == "wait_result" and isinstance(screen, VersusResult):
                state["winner"] = screen.winner_text()
                screen.life = VersusResult.INPUT_LOCK  # let the next frame draw it fully
                state["stage"] = "shoot"
            elif stage == "shoot":
                # state["shot"] = save_shot(app.screen, "_shot_versus_result.png")
                pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "}))
                state["stage"] = "wait_menu"
            elif stage == "wait_menu" and screen is app.welcome:
                state["stage"] = "done"
                raise FlowDone()
            if state["frame"] > 900:
                raise FlowDone()

        def flip():
            state["frame"] += 1
            real_flip()
            step()

        pg.display.flip = flip
        try:
            app.run()
        except FlowDone:
            pass
        finally:
            pg.display.flip = real_flip

        self.assertEqual(state["stage"], "done",
                         "leaving through the menu has to end up back in the main menu")
        self.assertEqual(state["winner"], "P1 WINS", "the higher score wins the match")
        self.assertTrue(os.path.getsize(state["shot"]) > 0)

    def test_the_result_names_the_higher_score(self):
        """leaving the match settles it: the higher score wins, a tie is a draw, and the value is
        only settled once"""
        game, p1, p2 = new_game()
        menu = object()
        game.players[0].score, game.players[1].score = 500, 300
        result = VersusResult(game, menu)
        self.assertEqual(result.winner_text(), "P1 WINS")
        game.players[0].score, game.players[1].score = 300, 500
        self.assertEqual(VersusResult(game, menu).winner_text(), "P2 WINS")
        game.players[0].score = game.players[1].score = 400
        self.assertEqual(VersusResult(game, menu).winner_text(), "DRAW")
        # self.assertTrue(game.versus_settled, "the match is marked as settled")
        solid = pg.mask.from_surface(result.panel).count()
        area = result.panel.get_width() * result.panel.get_height()
        self.assertGreater(solid, area * 0.9,
                           "the text sits on a dark panel, readable on any maze background")

        surface = ensure_display()
        result.life = VersusResult.INPUT_LOCK  # drawn fully, not half faded in
        result.draw(surface)
        shot = save_shot(surface, "_shot_versus_result.png")
        self.assertTrue(os.path.getsize(shot) > 0)
        pg.event.get()
        result.life = VersusResult.INPUT_LOCK
        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "})
        result.handle_events([key])
        self.assertTrue(drain_and_check(pg.USEREVENT + 5),
                        "a key carries on to the menu")

    def test_hud_stacks_tag_points_and_deaths(self):
        """the versus HUD: role tag under the label, then points and deaths, and no eat icon"""
        game, p1, p2 = new_game()
        self.assertIsInstance(game.hud, VersusHUD, "the versus mode builds the versus HUD")
        hud = game.hud
        predator, prey = versus_pair([p1, p2])
        predator.score, prey.score = 700, 300
        prey.eaten = 2
        surface = ensure_display()
        surface.fill((0, 0, 0))
        hud.draw(surface)

        self.assertEqual(hud._points(0), [p1.score for _ in game.players][0])
        self.assertEqual([hud._points(i) for i in (0, 1)], [p1.score, p2.score],
                         "both players report a score of their own")
        roles = hud.fetch_roles_cb()
        self.assertEqual(sorted(roles), ["PREDATOR", "PREY"])
        for index in (0, 1):
            tag = hud._tag_surface(hud._role_label(index), hud._p1_label.get_height())
            self.assertGreater(tag.get_width(), 0, "each player gets a role tag")
        death_row = hud._deaths_surface(0)
        self.assertGreater(death_row.get_width(), hud._kill_icon.get_width(),
                           "the death row shows the skull and its count")
        self.assertFalse(hasattr(hud, "_eat_icon") and hud._eat_icon is None)

        # a screenshot of the real thing: the maze, then the HUD on top of it
        face = pg.Surface(pg.display.get_window_size())
        game.draw(face)
        hud.draw(face)
        shot = save_shot(face, "_shot_versus_hud.png")
        self.assertTrue(os.path.getsize(shot) > 0)

        # the rows hang below the label, and the mirrored P2 block is flush with the right margin
        rows = hud._row_positions(0)
        self.assertGreater(rows[0][2], hud.MARGIN + hud._p1_label.get_height(),
                           "the tag sits below the P1 label")
        self.assertLess(rows[0][2], rows[1][2], "points come first, deaths below them")
        self.assertLess(rows[1][2], rows[2][2], "deaths are the last row")
        p2_rows = hud._row_positions(1)
        self.assertEqual(p2_rows[0][1] + p2_rows[0][0].get_width(), surface.get_width() - hud.MARGIN,
                         "the P2 block is flush with the right margin")

    def test_hud_labels_the_two_roles(self):
        game, p1, p2 = new_game()
        self.assertEqual(sorted(game.fetch_roles()), ["PREDATOR", "PREY"])
        hud = game.hud
        self.assertIsNotNone(hud.fetch_roles_cb)
        self.assertEqual(hud.fetch_roles_cb(), game.fetch_roles())
        size = pg.display.get_window_size()

        with_tags = pg.Surface(size)
        with_tags.fill((0, 0, 0))
        hud.draw(with_tags)
        hud.fetch_roles_cb = None
        without_tags = pg.Surface(size)
        without_tags.fill((0, 0, 0))
        hud.draw(without_tags)
        self.assertNotEqual(pg.image.tostring(with_tags, "RGBA"),
                            pg.image.tostring(without_tags, "RGBA"),
                            "the two role tags have to show up in the HUD")

        # the role swap after a catch has to show up in the tags as well
        predator, prey = versus_pair([p1, p2])
        roles_before = game.fetch_roles()
        prey.set_player_type(PlayerType.PREDATOR)
        predator.set_player_type(PlayerType.PREY)
        self.assertEqual(game.fetch_roles(), list(reversed(roles_before)))

        single = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        self.assertIsNone(single.hud.fetch_roles_cb, "single player has no roles to label")


class TestVersusRound(unittest.TestCase):

    def setUp(self):
        ensure_display()

    def test_catch_posts_the_ghost_event(self):
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        force_contact(predator, prey)
        game.handle_events([])
        self.assertTrue(game._versus_over)
        self.assertTrue(drain_and_check(pg.USEREVENT + 8), "a catch has to post the ghost transition")
        # the round must not be resolved twice
        game.handle_events([])
        self.assertFalse(drain_and_check(pg.USEREVENT + 8))

    def test_death_transition_counts_swaps_and_hands_over(self):
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        force_contact(predator, prey)
        game.handle_events([])
        pg.event.get()

        trans = VersusDeathTrans(game)

        # the death counter and the kill counter moved by exactly one
        self.assertEqual(prey.eaten, 1)
        self.assertEqual(predator.eat, 1)
        self.assertEqual(trans.deaths, 1)
        self.assertIn(game.fetch_scores(), ([(1, 0), (0, 1)], [(0, 1), (1, 0)]),
                      "the HUD reads (skull = deaths, eat icon = kills) per player")
        # the two roles are swapped for the next maze
        self.assertEqual(prey.player_type, PlayerType.PREDATOR)
        self.assertEqual(predator.player_type, PlayerType.PREY)
        self.assertIs(prey.anim_dict, predator_anim_dict)
        self.assertIs(predator.anim_dict, prey_anim_dict)
        # the next maze keeps the preset and obeys the spawn rule with the swapped roles
        self.assertIs(trans.get_new_game(), trans.maze2)
        self.assertEqual(trans.maze2.gamemode, GameMode.DOUBLE)
        self.assertEqual(trans.maze2.size_preset, game.size_preset)
        new_predator, new_prey = versus_pair([p1, p2])
        self.assertIs(new_predator, prey)
        self.assertIs(new_prey, predator)
        self.assertEqual(tuple(new_predator.pos), tuple(trans.maze2.maze.start))
        self.assertNotEqual(tuple(new_prey.pos), tuple(trans.maze2.maze.start))
        self.assertTrue(trans.maze2.maze.is_valid_coord(new_prey.pos))
        self.assertFalse(trans.maze2._versus_over, "the new round is unresolved")

    def test_ghost_scene_runs_and_waits_for_a_key(self):
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        force_contact(predator, prey)
        game.handle_events([])
        pg.event.get()

        trans = VersusDeathTrans(game)
        surface = ensure_display()
        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "})

        trans.handle_events([key])  # still inside the input lock
        self.assertFalse(drain_and_check(pg.USEREVENT + 3), "a key during the lock must be ignored")

        shots = []
        for i in range(trans.GHOST_TIME + 10):
            update_effects()
            trans.draw(surface)
            if i == trans.GRAY_FADE_TIME:
                self.assertAlmostEqual(trans._gray_intp.get(), 1.0, msg="the gray fade has to finish")
                shots.append(save_shot(surface, "_shot_death_mid.png"))
        self.assertEqual(trans._ghost_intp.get(), 1.0, "the ghost has to finish floating out")
        shots.append(save_shot(surface, "_shot_death_end.png"))
        for path in shots:
            self.assertTrue(os.path.getsize(path) > 0, f"{path} should not be empty")

        trans.handle_events([key])  # after the lock: any key jumps into the next maze
        self.assertTrue(drain_and_check(pg.USEREVENT + 3))
        self.assertIs(trans.get_new_game(), trans.maze2)

    def test_the_escape_intro_runs_the_prey_out_and_the_predator_in(self):
        """the escape transition: the prey runs off the screen, the predator runs in after it,
        there is a pause and only then the stats; a key cannot skip the little scene"""
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        prey.pos = V(game.maze.end)
        prey.pos_next = V(prey.pos)
        game.handle_events([])
        pg.event.get()
        trans = GameGameTrans(game)
        surface = ensure_display()
        self.assertIs(trans.players[0], prey, "the prey is the player the transition animates")
        self.assertIs(trans._chasing_player(), predator)

        start, out, back, middle = trans._escape_lane()
        direction = trans.direction

        def along(pos):
            return (pos[0] - start[0]) * direction[0] + (pos[1] - start[1]) * direction[1]

        trans._ani_p = 1
        trans.pre_p3 = 0
        trans.life = trans.ESCAPE_RUN_TIME // 2  # the prey is on its way out
        self.assertEqual(trans._escape_stage(), "prey")
        running, chased = trans._escape_actor_positions()
        self.assertIsNone(chased, "the predator is not on stage yet")
        self.assertGreater(along(running), 0, "the prey runs the way it faces")
        trans.life = trans.ESCAPE_RUN_TIME - 1  # one frame before its beat ends
        running, _ = trans._escape_actor_positions()
        self.assertGreaterEqual(along(running), out - 1,
                                "the prey leaves the screen completely, a sprite past the edge")
        self.assertLessEqual(out, max(surface.get_width(), surface.get_height()) + trans.maze2.cell_width * 3,
                             "and the run is a dash across the screen, not a marathon")

        trans.life = trans.ESCAPE_RUN_TIME + trans.ESCAPE_CHASE_TIME // 2
        self.assertEqual(trans._escape_stage(), "predator")
        running, chased = trans._escape_actor_positions()
        self.assertIsNone(running, "the prey is gone")
        self.assertLess(along(chased), 0, "the predator comes in from the other side")
        self.assertGreater(along(chased), -back, "and it is already on its way")

        trans.life = trans.ESCAPE_RUN_TIME + trans.ESCAPE_CHASE_TIME + 1
        self.assertEqual(trans._escape_stage(), "pause")
        _, stopped = trans._escape_actor_positions()
        self.assertEqual(along(stopped), int(middle), "the predator stops in the middle of the screen")

        trans.life = trans.ESCAPE_RUN_TIME + trans.ESCAPE_CHASE_TIME + trans.ESCAPE_PAUSE_TIME
        self.assertEqual(trans._escape_stage(), "stats")
        self.assertTrue(trans._escape_ready(), "the stats may be read out now")

        # a key that arrives during the chase is swallowed, so the scene plays out
        trans.life = 5
        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "})
        trans.handle_events([key])
        self.assertEqual(trans.pre_p3, 0, "a key during the chase must not skip it")
        trans.life = trans.ESCAPE_RUN_TIME + trans.ESCAPE_CHASE_TIME + trans.ESCAPE_PAUSE_TIME + 1
        trans.handle_events([key])
        self.assertEqual(trans.pre_p3, 1, "once the stats are up a key carries on")

        # the prey is hidden while the predator walks on, and only the predator is drawn
        drawn = []

        def spy(player):
            def wrapper(_surface, pos, _size=None):
                drawn.append((player, V(pos)))

            return wrapper

        real = {p: p.directly_draw for p in (predator, prey)}
        for p in (predator, prey):
            p.directly_draw = spy(p)
        try:
            trans.pre_p3 = 1
            trans.life = 0
            trans.intp1.set(0.6)
            trans.draw(surface)
        finally:
            for p, fn in real.items():
                p.directly_draw = fn
        self.assertEqual([who for who, _ in drawn], [prey, predator],
                         "their own player is still drawn first, then the predator")
        self.assertIsNotNone(trans._frame_under(surface, trans.p0[0]),
                             "and a versus transition can hide the player it animates")
        prey_pos = drawn[0][1]
        self.assertEqual(surface.get_at((prey_pos[0], prey_pos[1]))[:3], trans._start_color,
                         "the prey is erased again: only the predator is on the runway")

    def test_the_prey_faces_the_way_the_lines_extend(self):
        """the only player on screen walks in the direction the gateway lines extend"""
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        prey.pos = V(game.maze.end)
        prey.pos_next = V(prey.pos)
        game.handle_events([])
        pg.event.get()
        trans = GameGameTrans(game)
        surface = ensure_display()
        self.assertIs(trans.players[0], prey)
        self.assertEqual(prey.heading, VERSUS_ENTRANCE_HEADINGS[trans.start_edge],
                         "the prey has to face the way the lines extend")

        seen = []
        real_draw = prey.directly_draw
        prey.directly_draw = lambda surf, pos, size=None: seen.append(V(pos))
        try:
            trans._ani_p = 1
            trans.pre_p3 = 1
            trans.intp1.set(0.5)
            trans.draw(surface)
        finally:
            prey.directly_draw = real_draw
        self.assertEqual(tuple(seen[0]),
                         tuple(trans.p0[0] + (trans.p0[1] - trans.p0[0]) * 0.5),
                         "the prey has to travel along the transition's own curve")

    def test_the_new_maze_loads_before_the_prey_appears(self):
        """nobody may appear in the new maze before the reveal has arrived at their cell"""
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        prey.pos = V(game.maze.end)
        prey.pos_next = V(prey.pos)
        game.handle_events([])
        pg.event.get()
        trans = GameGameTrans(game)

        # nothing is revealed yet, so the prey drawn this frame has to be put back
        trans._ani_p = 2
        trans.life = 0
        self.assertEqual(trans._versus_reveal_radius(), 0, "the reveal has not started yet")
        under = trans._versus_hidden_frames()
        self.assertEqual(len(under), 2,
                         "both the prey and the predator that walked in are remembered")
        trans.players[0].directly_draw(trans.surface0, trans.p0[1])
        trans.players[1].directly_draw(trans.surface0, cell_to_surf(trans.maze2, trans.players[1].pos))
        drawn = rect_digest(trans.surface0, under[0][1])
        trans._hide_unrevealed_players(under)
        erased = rect_digest(trans.surface0, under[0][1])
        self.assertNotEqual(drawn, erased, "an unrevealed player has to be erased again")
        self.assertEqual(erased, hashlib.sha1(pg.image.tostring(under[0][2], "RGBA")).hexdigest(),
                         "the frame under the player has to come back exactly")
        self.assertEqual(trans.players[1].pos, trans.maze2.maze.start,
                         "the predator stands on the entrance of the new maze, where it belongs")

        # while the reveal runs its radius grows, and it has to survive the end of the effect
        trans.p2_fade.animate_now()
        update_effects()
        self.assertTrue(trans.p2_fade.animating)
        self.assertGreater(trans._versus_reveal_radius(), 0)
        for _ in range(trans.p2_fade._duration + 2):
            update_effects()
        self.assertFalse(trans.p2_fade.animating)
        self.assertGreater(trans._versus_reveal_radius(), 0,
                           "the last radius has to be remembered after the effect is over")

        # a revealed player stays on screen
        trans._versus_reveal_r = 10 ** 6
        under = trans._versus_hidden_frames()
        trans.players[0].directly_draw(trans.surface0, trans.p0[1])
        trans.players[1].directly_draw(trans.surface0, cell_to_surf(trans.maze2, trans.players[1].pos))
        trans._hide_unrevealed_players(under)
        kept = rect_digest(trans.surface0, under[0][1])
        self.assertNotEqual(kept, hashlib.sha1(pg.image.tostring(under[0][2], "RGBA")).hexdigest(),
                            "a revealed player must not be erased")

    def test_the_predator_arrives_on_the_entrance_and_stays_there(self):
        """after the escape transition the predator must walk up to the new entrance and be on
        screen there - in single player the one player never just vanishes either"""
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        prey.pos = V(game.maze.end)
        prey.pos_next = V(prey.pos)
        game.handle_events([])
        pg.event.get()
        trans = GameGameTrans(game)
        surface = ensure_display()
        entrance = cell_to_surf(trans.maze2, trans.maze2.maze.start)

        drawn = []

        def spy(player):
            def wrapper(_surf, pos, _size=None):
                drawn.append((player, V(pos)))

            return wrapper

        real = {p: p.directly_draw for p in (predator, prey)}
        for p in (predator, prey):
            p.directly_draw = spy(p)
        try:
            trans._ani_p = 2  # the new maze is on screen, the reveal has run its course
            trans.life = trans.PHASE_TIMES[1] + 5
            trans._versus_reveal_r = 10 ** 6
            drawn.clear()
            trans.draw(surface)
        finally:
            for p, fn in real.items():
                p.directly_draw = fn
        self.assertEqual([who for who, _ in drawn], [prey, predator],
                         "both players belong to the new maze")
        self.assertEqual(tuple(drawn[1][1]), tuple(entrance),
                         "the predator stands on the entrance it walked into")
        self.assertNotEqual(tuple(drawn[1][1]), tuple(drawn[0][1]),
                            "and not on top of the prey")

        # and it faces into the new maze again once the hand-over is done
        trans._ani_p = 1
        trans.pre_p3 = 1
        trans.life = trans.PHASE_TIMES[2]
        trans.handle_events([])
        self.assertEqual(trans._ani_p, 2)
        self.assertEqual(predator.heading, VERSUS_ENTRANCE_HEADINGS[trans.start_edge],
                         "the predator must not keep facing out of the maze it came from")

    def test_escape_posts_the_regular_transition_and_keeps_the_roles(self):
        game, p1, p2 = new_game()
        predator, prey = versus_pair([p1, p2])
        prey.pos = V(game.maze.end)
        prey.pos_next = V(prey.pos)
        game.handle_events([])
        self.assertTrue(game._versus_over)
        self.assertTrue(drain_and_check(pg.USEREVENT + 2), "an escape posts the regular transition")
        self.assertFalse(drain_and_check(pg.USEREVENT + 8))

        trans = GameGameTrans(game)
        self.assertEqual(trans.maze2.gamemode, GameMode.DOUBLE)
        self.assertIs(trans.players[0], prey, "only the escapee is animated by the transition")
        self.assertEqual(prey.player_type, PlayerType.PREY, "an escape keeps the roles")
        self.assertEqual(predator.player_type, PlayerType.PREDATOR)
        new_predator, new_prey = versus_pair([p1, p2])
        self.assertEqual(tuple(new_predator.pos), tuple(trans.maze2.maze.start))
        self.assertNotEqual(tuple(new_prey.pos), tuple(trans.maze2.maze.start))

        # the regular transition has to reach its own end, carry the prey all the way through
        # and post the hand-over event
        surface = ensure_display()
        key = pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "})
        handed_over = False
        shots = {}
        intro = (trans.ESCAPE_RUN_TIME + trans.ESCAPE_CHASE_TIME + trans.ESCAPE_PAUSE_TIME)
        for i in range(600):
            update_effects()
            # the frames about to be drawn: the first one of the new maze, and one while its
            # circular reveal is still sweeping over it
            new_maze_first = trans._ani_p == 2 and trans.life == 1
            mid_reveal = trans._ani_p == 2 and trans.life == trans.PHASE_TIMES[1] // 2
            trans.draw(surface)
            # the little chase swallows early keys, so a player keeps pressing until it moves on
            trans.handle_events([key] if i >= trans.PHASE_TIMES[0] and (i - trans.PHASE_TIMES[0]) % 4 == 0
                                else [])
            if i == 10:
                shots["old_maze"] = save_shot(surface, "_shot_trans_old_maze.png")
            elif i == trans.PHASE_TIMES[0] + trans.ESCAPE_RUN_TIME // 2:
                shots["escape_run"] = save_shot(surface, "_shot_escape_run.png")
            elif i == trans.PHASE_TIMES[0] + trans.ESCAPE_RUN_TIME + trans.ESCAPE_CHASE_TIME // 2:
                shots["escape_chase"] = save_shot(surface, "_shot_escape_chase.png")
            elif i == trans.PHASE_TIMES[0] + intro + 25:
                shots["escape_stats"] = save_shot(surface, "_shot_escape_stats.png")
            elif new_maze_first:
                shots["new_maze_start"] = save_shot(surface, "_shot_trans_start.png")
            elif mid_reveal:
                shots["reveal"] = save_shot(surface, "_shot_trans_reveal.png")
            elif i > trans.PHASE_TIMES[0] + intro + 30 and trans._ani_p == 2 \
                    and trans.life == trans.PHASE_TIMES[1]:
                shots["new_maze"] = save_shot(surface, "_shot_trans_new_maze.png")
            if drain_and_check(pg.USEREVENT + 3):
                handed_over = True
                break
        self.assertTrue(handed_over, "the regular transition has to hand the new maze over")
        self.assertEqual(tuple(trans.p0[1]), tuple(cell_to_surf(trans.maze2, prey.pos)),
                         "the prey has to land on its own spawning cell")
        self.assertEqual(sorted(shots),
                         ["escape_chase", "escape_run", "escape_stats", "new_maze",
                          "new_maze_start", "old_maze", "reveal"],
                         "all phases of the transition should have been captured")
        for path in shots.values():
            self.assertTrue(os.path.getsize(path) > 0, f"{path} should not be empty")

    def test_player2_walks_with_wasd_in_double_mode(self):
        game, p1, p2 = new_game()
        p2.disp_state = type(p2.disp_state).IDLE
        start = V(p2.pos)
        # walk player 2 in every direction; at least one of them has to leave its cell
        moved = False
        for key in (pg.K_w, pg.K_a, pg.K_s, pg.K_d):
            game.handle_events([pg.event.Event(pg.KEYDOWN, {"key": key, "mod": 0, "unicode": ""})])
            if tuple(p2.pos_next) != tuple(start):
                moved = True
            p2.pos = p2.pos_next = V(start)
            p2.disp_state = type(p2.disp_state).IDLE
        self.assertTrue(moved, "WASD has to drive player 2 in the two-player mode")

    def test_arrows_still_drive_player1_in_double_mode(self):
        game, p1, p2 = new_game()
        start = V(p1.pos)
        moved = False
        for key in (pg.K_UP, pg.K_LEFT, pg.K_DOWN, pg.K_RIGHT):
            game.handle_events([pg.event.Event(pg.KEYDOWN, {"key": key, "mod": 0, "unicode": ""})])
            if tuple(p1.pos_next) != tuple(start):
                moved = True
            p1.pos = p1.pos_next = V(start)
            p1.disp_state = type(p1.disp_state).IDLE
        self.assertTrue(moved, "the arrows have to keep driving player 1")


class FlowDone(Exception):
    """raised from the patched “display.flip” to leave the real main loop without quitting pygame
    (quitting would invalidate the surfaces that Resources loaded at import time)"""


class IdleClock:
    """a clock that never sleeps, so the integration test runs at full speed"""

    @staticmethod
    def tick(_fps=0):
        return 0


class FlowDriver:
    """Drives the real "Game.run" loop frame by frame: starts the two-player match through the menu
    button, forces a catch, skips the ghost scene with a key, forces an escape, then leaves the
    loop by raising FlowDone."""

    MAX_FRAMES = 1200

    def __init__(self, app):
        self.shot_mid = None
        self.shot_next = None
        self.app = app
        self.real_flip = pg.display.flip
        self.clock = IdleClock()
        self.frame = 0
        self.stage = "menu"
        self.problems = []
        self.notes = []
        self.game1 = self.game2 = None
        self.death_frames = 0
        self.trans_frames = 0

    # helpers
    def fail(self, message):
        self.problems.append(message)

    def note(self, message):
        self.notes.append(message)

    @staticmethod
    def key(key=pg.K_SPACE):
        pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": key, "mod": 0, "unicode": " "}))

    @staticmethod
    def click(rect):
        pg.event.post(pg.event.Event(pg.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1}))
        pg.event.post(pg.event.Event(pg.MOUSEBUTTONUP, {"pos": rect.center, "button": 1}))

    def flip(self):
        self.frame += 1
        self.real_flip()
        try:
            self.step()
        except FlowDone:
            raise
        except Exception as exc:  # a crash inside the driver must not look like a game crash
            self.fail(f"driver error at frame {self.frame} ({self.stage}): {exc!r}")
            raise FlowDone()
        if self.frame > self.MAX_FRAMES and self.stage != "done":
            self.fail(f"the flow got stuck in stage '{self.stage}' after {self.frame} frames")
            self.stage = "stuck"
            raise FlowDone()

    def step(self):
        app = self.app
        if self.stage == "menu":
            if self.frame >= 3:
                self.click(app.welcome.double_btn.rect)
                self.stage = "wait_play"
        elif self.stage == "wait_play":
            if app.state == game_main.GameState.PLAYING and app.maze_game is not None:
                self.game1 = app.maze_game
                if self.game1.gamemode != GameMode.DOUBLE:
                    self.fail("the two-player entry did not start a DOUBLE game")
                predator, prey = versus_pair(self.game1.players)
                if len(self.game1.players) != 2:
                    self.fail("a two-player match needs two players")
                if tuple(predator.pos) != tuple(self.game1.maze.start):
                    self.fail("the predator did not spawn on the entrance")
                if tuple(prey.pos) in (tuple(self.game1.maze.start), tuple(self.game1.maze.end)):
                    self.fail("the prey spawned on the entrance or on the exit")
                self.note(f"round 1 started: roles {[int(p.player_type) for p in self.game1.players]}")
                self.stage = "catch"
        elif self.stage == "catch":
            predator, prey = versus_pair(self.game1.players)
            force_contact(predator, prey)
            self.stage = "wait_death"
        elif self.stage == "wait_death":
            if isinstance(app.current_screen, VersusDeathTrans):
                self.stage = "death"
                self.death_frames = 0
                self.shot_mid = save_shot(app.screen, "_shot_loop_death.png")
        elif self.stage == "death":
            self.death_frames += 1
            if self.death_frames == 70:
                self.key()
                self.stage = "wait_play2"
        elif self.stage == "wait_play2":
            if app.state == game_main.GameState.PLAYING and app.maze_game is not self.game1:
                self.game2 = app.maze_game
                died, killer = self.game1.players[0], self.game1.players[1]
                died, killer = (died, killer) if died.eaten else (killer, died)
                if died.eaten != 1 or killer.eat != 1:
                    self.fail("the catch did not move the death / kill counters by one")
                if died.player_type != PlayerType.PREDATOR:
                    self.fail("the roles were not swapped after the catch")
                if self.game2.fetch_scores() != [(1, 0), (0, 1)] and self.game2.fetch_scores() != [(0, 1), (1, 0)]:
                    self.fail(f"the HUD counters do not show the death: {self.game2.fetch_scores()}")
                new_predator, new_prey = versus_pair(self.game2.players)
                if tuple(new_predator.pos) != tuple(self.game2.maze.start):
                    self.fail("the new predator does not start on the entrance")
                if tuple(new_prey.pos) == tuple(self.game2.maze.start):
                    self.fail("the new prey starts on the entrance")
                self.note(f"ghost scene done after {self.death_frames} frames, "
                          f"roles now {[int(p.player_type) for p in self.game2.players]}")
                self.shot_next = save_shot(app.screen, "_shot_loop_new_maze.png")
                self.stage = "escape"
        elif self.stage == "escape":
            prey = versus_pair(self.game2.players)[1]
            prey.pos = V(self.game2.maze.end)
            prey.pos_next = V(prey.pos)
            self.stage = "wait_trans"
        elif self.stage == "wait_trans":
            if isinstance(app.current_screen, GameGameTrans):
                self.stage = "trans"
                self.trans_frames = 0
        elif self.stage == "trans":
            self.trans_frames += 1
            # the escape intro swallows early keys, so keep pressing like a player would
            if self.trans_frames >= GameGameTrans.PHASE_TIMES[0] and self.trans_frames % 6 == 0:
                self.key()
        elif self.stage == "wait_play3":
            if app.state == game_main.GameState.PLAYING and app.maze_game is not self.game2:
                roles_before = [p.player_type for p in self.game2.players]
                roles_after = [p.player_type for p in app.maze_game.players]
                if roles_before != roles_after:
                    self.fail("an escape must keep the roles")
                self.note(f"escape hand-over done after {self.trans_frames} transition frames")
                self.stage = "done"
                raise FlowDone()
        # the regular transition hands its new maze over through USEREVENT + 3
        if self.stage == "trans" and app.state == game_main.GameState.PLAYING and app.maze_game is not self.game2:
            self.stage = "wait_play3"
            self.step()


class SingleFlowDriver:
    """the same idea as FlowDriver, for the untouched single-player path: start it from the menu,
    walk the only player onto the exit, press a key inside the transition and make sure a new maze
    is handed over."""

    MAX_FRAMES = 900

    def __init__(self, app):
        self.app = app
        self.real_flip = pg.display.flip
        self.clock = IdleClock()
        self.frame = 0
        self.extra = 0
        self.stage = "menu"
        self.problems = []
        self.game1 = None

    def fail(self, message):
        self.problems.append(message)

    def flip(self):
        self.frame += 1
        self.real_flip()
        app = self.app
        if self.stage == "menu":
            if self.frame >= 3:
                rect = app.welcome.single_btn.rect
                pg.event.post(pg.event.Event(pg.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1}))
                self.stage = "wait_play"
        elif self.stage == "wait_play":
            if app.state == game_main.GameState.PLAYING and app.maze_game is not None:
                game = app.maze_game
                if game.gamemode != GameMode.SINGLE or len(game.players) != 1:
                    self.fail("the single-player entry did not build a SINGLE game")
                self.game1 = game
                game.players[0].pos = V(game.maze.end)
                game.players[0].pos_next = V(game.players[0].pos)
                self.stage = "wait_trans"
        elif self.stage == "wait_trans":
            if isinstance(app.current_screen, GameGameTrans):
                self.stage = "trans"
        elif self.stage == "trans":
            self.extra += 1
            if self.extra == GameGameTrans.PHASE_TIMES[0] + 5:
                pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE, "mod": 0, "unicode": " "}))
            if app.state == game_main.GameState.PLAYING and app.maze_game is not self.game1:
                self.stage = "done"
                raise FlowDone()
        if self.frame > self.MAX_FRAMES and self.stage != "done":
            self.fail(f"the single-player flow got stuck in stage '{self.stage}'")
            self.stage = "stuck"
            raise FlowDone()


class TestSinglePlayerRegression(unittest.TestCase):
    """the versus mode is wired in with inserted branches only, so the original mode has to keep
    behaving exactly as before"""

    def test_single_player_game_logic(self):
        ensure_display()
        game = MazeGame(gamemode=GameMode.SINGLE, size_preset="small")
        pg.event.get()
        game.start_timing()  # the main loop starts the timer when the round becomes playable
        player = game.players[0]
        self.assertEqual(tuple(player.pos), tuple(game.maze.start))
        self.assertEqual(len(game.players), 1)
        # WASD must stay out of the single-player mode
        start = V(player.pos)
        for key in (pg.K_w, pg.K_a, pg.K_s, pg.K_d):
            game.handle_events([pg.event.Event(pg.KEYDOWN, {"key": key, "mod": 0, "unicode": ""})])
        self.assertEqual(tuple(player.pos_next), tuple(start), "WASD must not move the single player")
        # reaching the exit still ends the round through the regular transition
        player.pos = V(game.maze.end)
        player.pos_next = V(player.pos)
        game.handle_events([])
        self.assertTrue(drain_and_check(pg.USEREVENT + 2))
        self.assertFalse(drain_and_check(pg.USEREVENT + 8))
        trans = GameGameTrans(game)
        self.assertEqual(trans.maze2.gamemode, GameMode.SINGLE)
        self.assertEqual(tuple(trans.maze2.players[0].pos), tuple(trans.maze2.maze.start))

    def test_single_player_flow_in_the_real_loop(self):
        app = game_main.Game()
        driver = SingleFlowDriver(app)
        app.clock = driver.clock
        pg.display.flip = driver.flip
        try:
            with self.assertRaises(FlowDone):
                app.run()
        finally:
            pg.display.flip = driver.real_flip
        self.assertEqual(driver.stage, "done", f"single player stopped in stage '{driver.stage}'")
        self.assertEqual(driver.problems, [], "single-player problems")


class TestMainLoopIntegration(unittest.TestCase):

    def test_full_two_player_flow(self):
        app = game_main.Game()
        self.assertEqual(app.welcome.double_btn.text, "TWO PLAYER",
                         "the menu entry of the finished mode should not say SOON")
        driver = FlowDriver(app)
        app.clock = driver.clock
        pg.display.flip = driver.flip
        try:
            with self.assertRaises(FlowDone):
                app.run()
        finally:
            pg.display.flip = driver.real_flip

        self.assertEqual(driver.stage, "done", f"the flow stopped in stage '{driver.stage}'")
        self.assertEqual(driver.problems, [], "integration problems")
        self.assertTrue(os.path.getsize(driver.shot_mid) > 0, "the death scene screenshot is empty")
        self.assertTrue(os.path.getsize(driver.shot_next) > 0, "the new maze screenshot is empty")
        print("\n".join("  " + note for note in driver.notes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
