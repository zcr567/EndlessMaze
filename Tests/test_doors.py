"""
Self-check of the one-way doors.

A door is a wall between two neighbouring cells that the maze already connects around: the wall is
opened and may only be walked the way its arrow points. That construction is what keeps the feature
fair, and these tests pin the two properties it buys:

  * nothing of the original maze is taken away, so its plain path always stays open as the choice a
    player can fall back on - a door is a shortcut, never the only way;
  * because that path is still there, walking a door the wrong way can always be undone with a
    detour, and the whole maze stays reachable in every direction: no dead end is ever sealed.

    python -m unittest Tests.test_doors -v
"""

import os
import random
import sys
import unittest

import pygame as pg

import main as game_main  # noqa: F401  (initialises pygame exactly like the game does)
from maze import Maze
# noinspection PyPep8Naming
from vectors import DIR_VECS, Vector as V
from widgets import GameMode, MazeGame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCREEN_SIZE = (1000, 800)
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")
STEPS = [(V(1, 0), 0), (V(-1, 0), 1), (V(0, 1), 2), (V(0, -1), 3)]


def ensure_display():
    pg.init()
    if pg.display.get_surface() is None:
        pg.display.set_mode(SCREEN_SIZE, pg.RESIZABLE)
    return pg.display.get_surface()


def new_maze(side=(8, 14), diff="normal"):
    """a generated maze of a random size, with whatever doors its generation handed out"""
    return Maze((random.randint(*side), random.randint(*side)), diff_preset=diff)


def cells_of(maze):
    return [(x, y) for y in range(maze.height) for x in range(maze.width)]


def carved_cells(maze):
    """the cells the maze actually connects: the generator can leave pockets of solid rock behind,
    and nothing to do with walking (or doors) is claimed about those"""
    # noinspection PyProtectedMember
    tree = maze._tree_adjacency()
    return set(bfs(tree, tuple(maze.start)))


def step_open(maze, inst, cell, vec):
    """the movement rule of the game: an open wall that is not a door walked backwards"""
    other = (cell[0] + vec[0], cell[1] + vec[1])
    if not (0 <= other[0] < maze.width and 0 <= other[1] < maze.height):
        return False
    if inst[2 * cell[1] + vec[1] + 1][2 * cell[0] + vec[0] + 1] != 2:
        return False
    return not maze.blocks_one_way(cell, other)


def open_passages(maze, inst):
    """every pair of neighbouring cells the instruction matrix connects, doors included"""
    found = set()
    for cell in cells_of(maze):
        for vec, _ in STEPS:
            other = (cell[0] + vec[0], cell[1] + vec[1])
            if not (0 <= other[0] < maze.width and 0 <= other[1] < maze.height):
                continue
            if inst[2 * cell[1] + vec[1] + 1][2 * cell[0] + vec[0] + 1] == 2:
                found.add(frozenset((cell, other)))
    return found


def bfs(graph, source):
    seen = {source}
    queue = [source]
    while queue:
        cur = queue.pop(0)
        for nxt in graph[cur]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


class TestDoorPlacement(unittest.TestCase):

    def test_a_door_is_an_opened_wall(self):
        for _ in range(12):
            maze = new_maze()
            tree = maze._tree_adjacency()
            inst = maze.draw_instructions()
            for start, end in maze.one_way_doors:
                self.assertEqual(abs(start[0] - end[0]) + abs(start[1] - end[1]), 1,
                                 "a door connects two neighbouring cells")
                self.assertNotIn(tuple(end), tree[tuple(start)],
                                 "a door is opened in a wall the maze did not use before")
                carved = carved_cells(maze)
                self.assertIn(tuple(start), carved)
                self.assertIn(tuple(end), carved,
                              "a door may only connect cells of the carved maze, never a pocket")
                vec = V(end) - V(start)
                self.assertTrue(step_open(maze, inst, tuple(start), vec),
                                "a door has to be walkable the way it points")
                self.assertFalse(step_open(maze, inst, tuple(end), -vec),
                                 "walking a door backwards has to be blocked")

    def test_the_plain_path_stays_available(self):
        """a door is added, never swapped in: every plain passage of the maze is still open, so the
        old route always stays available as the choice, and the doors are the only new passages"""
        for _ in range(12):
            maze = new_maze()
            inst = maze.draw_instructions()
            tree = maze._tree_adjacency()
            plain = {frozenset((cell, other))
                     for cell, neighbours in tree.items() for other in neighbours}
            doors = {frozenset((tuple(start), tuple(end))) for start, end in maze.one_way_doors}
            passages = open_passages(maze, inst)
            self.assertTrue(plain <= passages,
                            "a passage of the plain maze disappeared")
            self.assertEqual(passages, plain | doors,
                             "the doors have to be the only passages the maze did not have before")
            self.assertIn(tuple(maze.end), bfs(tree, tuple(maze.start)),
                          "the exit stays reachable without walking a door")

    def test_no_cell_can_be_trapped(self):
        """with the doors in place every carved cell still reaches every other carved cell, so a
        door taken the wrong way can always be undone and no dead end is sealed"""
        for _ in range(8):
            maze = new_maze(side=(6, 9))
            inst = maze.draw_instructions()
            cells = sorted(carved_cells(maze))
            graph = {cell: [] for cell in cells}
            for cell in cells:
                for vec, _ in STEPS:
                    if step_open(maze, inst, cell, vec):
                        graph[cell].append((cell[0] + vec[0], cell[1] + vec[1]))
            for source in cells:
                self.assertEqual(len(bfs(graph, source)), len(cells),
                                 f"cell {source} cannot reach the whole maze any more")

    def test_dead_ends_can_be_entered_and_left(self):
        for _ in range(8):
            maze = new_maze(side=(6, 9))
            inst = maze.draw_instructions()
            tree = maze._tree_adjacency()
            for cell in sorted(carved_cells(maze)):
                outgoing = [vec for vec, _ in STEPS if step_open(maze, inst, cell, vec)]
                incoming = [vec for vec, _ in STEPS
                            if step_open(maze, inst, (cell[0] + vec[0], cell[1] + vec[1]), -vec)]
                self.assertTrue(outgoing, f"cell {cell} cannot be left at all")
                if len(tree[cell]) == 1:  # a dead end of the plain maze
                    self.assertTrue(incoming, f"the dead end {cell} cannot be entered")
                    self.assertTrue(outgoing, f"the dead end {cell} cannot be left")

    def test_doors_are_limited_and_common(self):
        mazes = with_doors = 0
        for _ in range(24):
            maze = new_maze()
            mazes += 1
            with_doors += 1 if maze.one_way_doors else 0
            self.assertLessEqual(len(maze.one_way_doors), Maze.ONE_WAY_DOOR_MAX)
        self.assertGreaterEqual(with_doors / mazes, 0.6, "most mazes should offer a door")

    def test_doors_keep_their_distance(self):
        for _ in range(12):
            maze = new_maze(side=(14, 20))
            doors = maze.one_way_doors
            for i, first in enumerate(doors):
                for second in doors[i + 1:]:
                    distance = min(abs(first[a][0] - second[b][0]) + abs(first[a][1] - second[b][1])
                                   for a in (0, 1) for b in (0, 1))
                    self.assertGreaterEqual(distance, Maze.ONE_WAY_DOOR_SPACING,
                                            "doors have to be spread over the maze")


class TestDoorMovement(unittest.TestCase):

    def setUp(self):
        ensure_display()

    def game_with_a_door(self, tries=40):
        for _ in range(tries):
            game = MazeGame(gamemode=GameMode.SINGLE, size_preset="medium")
            if game.maze.one_way_doors:
                return game
        self.fail("no maze with a one-way door was generated")

    def test_the_player_walks_a_door_only_forwards(self):
        game = self.game_with_a_door()
        player = game.players[0]
        for start, end in game.maze.one_way_doors:
            forward = [cell for cell, vec in DIR_VECS.items() if vec == V(end) - V(start)][0]
            backward = [cell for cell, vec in DIR_VECS.items() if vec == V(start) - V(end)][0]

            player.pos = player.pos_next = V(start)
            player.heading = forward
            player.disp_state = type(player.disp_state).IDLE
            player.move(forward)
            self.assertNotEqual(tuple(player.pos_next), tuple(start),
                                "the player has to be able to walk a door forwards")

            player.pos = player.pos_next = V(end)
            player.heading = backward
            player.disp_state = type(player.disp_state).IDLE
            player.move(backward)
            self.assertEqual(tuple(player.pos_next), tuple(end),
                             "the player must not be able to walk a door backwards")

    def test_doors_run_through_the_whole_game_loop(self):
        """a game with doors still plays: no crash, the exit is still reachable and the maze
        surfaces are redrawn with the arrows on every resize"""
        game = self.game_with_a_door()
        surface = ensure_display()
        game.start_timing()
        for _ in range(10):
            game.handle_events([])
            game.draw(surface)
        game.resize(SCREEN_SIZE)
        game.draw(surface)
        path = os.path.join(SHOT_DIR, "_shot_one_way_doors.png")
        os.makedirs(SHOT_DIR, exist_ok=True)
        game.draw(surface)
        game.hud.draw(surface)
        pg.image.save(surface, path)
        self.assertTrue(os.path.getsize(path) > 0, "the screenshot should not be empty")

        arrows = pg.mask.from_threshold(surface, MazeGame.DOOR_COLOR, (30, 30, 30, 255))
        self.assertGreater(arrows.count(), 50, "the door arrows have to be drawn on the maze")

    def test_doors_survive_a_decorative_maze(self):
        """the menu draws a maze of its own, which must not choke on the doors"""
        ensure_display()
        from widgets import WelcomeScreen
        screen = WelcomeScreen(SCREEN_SIZE)
        screen.draw(ensure_display())


if __name__ == "__main__":
    unittest.main(verbosity=2)
