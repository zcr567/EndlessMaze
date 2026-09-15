"""
======================================
a simple maze generating & I/O script

The Maze generating an algorithm. First, generate a most simple right path, connecting the two ends, then make some
attempts to add twists. Finally, branches are added using a breadth first search method.

version: 1.0
author: ZCR
======================================
"""
import math
from hashlib import md5
from random import random, randint, choice

from vectors import *

V = Vector

DIFFICULTY_PRESETS = {
    "easy": None,
    "normal": None,
    "hard": None,
}
# size presets: (min side length, max side length);
SIZE_PRESETS = {
    "small": (5, 10),
    "medium": (10, 20),
    "large": (20, 40),
}


def count(start, stop):
    """an enhanced version of range(), supports stop smaller than start"""
    if start > stop:
        return range(start, stop, -1)
    else:
        return range(start, stop)


class Maze:

    def __init__(self,
                 size: vec_like = (10, 10),
                 start: vec_like = None,
                 end: vec_like = None,
                 start_edge=None,
                 end_edge=None,
                 filepath=None,
                 diff_preset=None):

        self._size = size
        self._start = start
        self._end = end
        self._width = self._size[0]
        self._height = self._size[1]
        self._data = [[Cell.EMPTY for _ in range(self._width)] for _ in range(self._height)]
        self._ls_paths: list[list[tuple[int, int]]] = []  # path segments used for bending
        self._right_path = []

        # hyperparameters for branching
        self.diff_preset = diff_preset
        # TODO: find a set of parameters below, to implement difficulty preset function
        self.PATH_LENGTH_UNIFORMITY = 2  # larger than 1, controls the length uniformity of the right path's segments
        self.BRANCH_THR = math.sqrt(self._width * self._height) // 2  # controls branch nesting depth
        self.BRANCH_EXTEND_PROB = 1 - 1 / (self._width + self._height)  # controls average branch length
        self.MAKING_BRANCH_PROB = .8  # controls branch numbers

        if filepath is not None:
            try:
                with open("maze1.txt", "r") as f:
                    content_hash = f.readline()[:-1]
                    content = f.read()
                    if md5(bytes(content, "utf-8")).hexdigest() != content_hash:
                        raise ValueError(f"File is corrupted or not a valid maze file.")
                    content = content.splitlines()
                    self._size, self._start, self._end = [eval(content[i]) for i in range(3)]
                    self._data = [[int(i) for i in ln.split()] for ln in content[3:]]
            except FileNotFoundError:
                raise FileNotFoundError(f"File '{filepath}' not found")
            return

        self.start_edge = start_edge
        self.end_edge = end_edge

        if start is None:
            self._start = self._b_select(start_edge, is_start=True)
            while self._start == self._end:
                self._start = self._b_select(start_edge, is_start=True)
        else:
            if self.is_valid_coord(start):
                self._start = start
            else:
                raise ValueError("Invalid coordinate for parameter start")

        if end is None:
            self._end = self._b_select(end_edge, is_end=True)
            while abs(self._start[0] - self._end[0]) + abs(self._start[1] - self._end[1]) < 2:
                self._start = self._b_select(end_edge, is_start=True)
        else:
            if self.is_valid_coord(end):
                self._end = end
            else:
                raise ValueError("Invalid coordinate for parameter end")

        self.set_p(self._start, 5)
        self.generate()

        # print(f"{start_edge} {self.start_edge} {self.end_edge}")

    # do NOT change the order of the two lists below
    REPR_CORNER_ENUM = ['┼', '┤', '┬', '┐', '├', '│', '┌', ' ', '┴', '┘', '─', ' ', '└', ' ', ' ', ' ']

    def draw_instructions(self):
        """HOW IT WORKS:

        Firstly, make a draw instruction based on the maze paths, the instruction is a matrix of int, each int
        represents a draw operation.
        Corners: each cross intersection has four lines, and whether the one of then should be drawn is independent.
                 so if 1 represents draw and 0 is do not draw, we can use a four-digit binary number to encode
                 every situation. This way we can traversal the cells instead of the corners, reducing lookup
                 operations by 4 times.
        edges:   it is simple.
        the instruction code can be reused for rendering the maze in games.

        Secondly, make the repr text based on the instructions."""
        inst = [[0 for _ in range(self._width * 2 + 1)] for _ in range(self._height * 2 + 1)]
        # maze edges
        for row in range(0, self._height * 2 + 2, 2):
            inst[row][0] = 4
            inst[row][-1] = 1
        for col in range(0, self._width * 2 + 2, 2):
            inst[0][col] += 2
            inst[-1][col] += 8
        # maze path corners and maze path edges
        for row in range(1, self._height * 2 + 1, 2):
            for col in range(1, self._width * 2 + 1, 2):
                direction = self.get_p((col // 2, row // 2))
                if (col // 2, row // 2) == self._start or (col // 2, row // 2) == self._end:  # start or end of the maze
                    if row // 2 == 0:
                        inst[0][col - 1] |= 1
                        inst[0][col + 1] |= 4
                        inst[0][col] = 2
                    elif col // 2 == 0:
                        inst[row - 1][0] |= 8
                        inst[row + 1][0] |= 2
                        inst[row][0] = 2
                    elif row // 2 == self._height - 1:
                        inst[row + 1][col - 1] |= 1
                        inst[row + 1][col + 1] |= 4
                        inst[row + 1][col] = 2
                    elif col // 2 == self._width - 1:
                        inst[row - 1][col + 1] |= 8
                        inst[row + 1][col + 1] |= 2
                        inst[row][col + 1] = 2
                if direction == Cell.GO_RIGHT:
                    inst[row - 1][col - 1] |= 8
                    inst[row + 1][col - 1] |= 2
                    inst[row][col - 1] = 2
                elif direction == Cell.GO_UP:
                    inst[row + 1][col - 1] |= 1
                    inst[row + 1][col + 1] |= 4
                    inst[row + 1][col] = 2
                elif direction == Cell.GO_LEFT:
                    inst[row - 1][col + 1] |= 8
                    inst[row + 1][col + 1] |= 2
                    inst[row][col + 1] = 2
                elif direction == Cell.GO_DOWN:
                    inst[row - 1][col - 1] |= 1
                    inst[row - 1][col + 1] |= 4
                    inst[row - 1][col] = 2
        return inst

    def __repr__(self):
        """Give a string representation of the Maze. The string includes a description of the basic properties and a
        graph of the maze in the form of text. Use the font JetBrain Source to obtain the best effect."""
        r = f"<Maze(size={self._size}, start={self._start}, end={self._end})>\n\n"

        inst = self.draw_instructions()

        # draw using characters
        for row in range(self._height * 2 + 1):
            for col in range(self._width * 2 + 1):
                op = inst[row][col]
                if row % 2 == 0 and col % 2 == 0:
                    r += self.REPR_CORNER_ENUM[op]
                if row % 2 == 0 and col % 2 == 1:
                    r += " " if op == 2 else "─"
                # elif row % 2 == 1 and col % 2 == 0:
                #     r += " " if op == 2 else "|"
                # elif row % 2 == 1 and col % 2 == 1:
                #     r += " "
            if row % 2 == 0:
                r += "\n"
        return r

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    def _b_select(self, edge=None, is_start=False, is_end=False):
        """Select a random point on the edge of the maze, and mark it in the _data property. Each point has an equal
        probability to be chosen. This function is used to determine the start and end points of the maze."""
        edge = edge if edge is not None else randint(0, 3)
        if edge == 0:  # top edge
            t = randint(1, self.width - 2)
            p = (t, 0)
        elif edge == 1:  # right edge
            t = randint(self.width, self.width + self.height - 3)
            p = (self._width - 1, t - self._width + 1)
        elif edge == 2:  # bottom edge
            t = randint(self.width + self.height - 1, self.width * 2 + self.height - 4)
            p = (t - self._width - self._height + 2, self._height - 1)
        elif edge == 3:  # left edge
            t = randint(self.width * 2 + self.height - 2, self.width * 2 + self.height * 2 - 5)
            p = (0, t - self._height - self._width * 2 + 3)
        else:
            raise ValueError(f"Wrong edge value {edge}")
        if is_start:
            self.start_edge = edge
        elif is_end:
            self.end_edge = edge
        return p

    def get_right_path(self):
        return self._right_path.copy()

    def save(self, filepath):
        try:
            open(filepath, "x").close()
        except FileExistsError:
            pass

        with open(filepath, "w", encoding="utf-8") as f:
            content = ""
            content += f"{self._size}\n{self._start}\n{self._end}\n"
            for i in self._data:
                for j in i:
                    content += f"{j} "
                content += "\n"
            f.write(md5(bytes(content, "utf-8")).hexdigest())
            f.write("\n")
            f.write(content)

    def set_p(self, point, value):
        self._data[point[1]][point[0]] = value

    def get_p(self, point):
        return self._data[point[1]][point[0]]

    def is_valid_coord(self, point: vec_like) -> bool:
        return 0 <= point[0] < self._width and 0 <= point[1] < self._height

    def is_valid_empty(self, point: vec_like) -> bool:
        return (0 <= point[0] < self._width
                and 0 <= point[1] < self._height
                and self._data[point[1]][point[0]] == Cell.EMPTY)

    def _available(self, p: vec_like) -> list[Vector]:
        """Return the available (i.e. it is empty) points next to the given point."""
        available = []
        for pp in [V(0, 1), V(0, -1), V(1, 0), V(-1, 0)]:
            if self.is_valid_empty(p + pp):
                available.append(pp)
        return available

    def _update_right_path(self):
        """update the whole right path in self._data property"""
        prev = V(self._right_path[0])
        for point in self._right_path[1:]:
            self.set_p(point, DIR_ENUMS[point - prev])
            prev = V(point)

    def _bend(self):
        # randomly choose a path segment to be bent
        # ln_raw = choice(self._ls_paths)
        ln_raw = choice(self._ls_paths[:len(self._ls_paths) // self.PATH_LENGTH_UNIFORMITY])
        ln = ln_raw.copy()
        failed_count = 0
        while len(ln) < 2:
            failed_count += 1
            ln_raw = choice(self._ls_paths)
            ln = ln_raw.copy()
            if failed_count > 10:
                return False

        # find a proper segment and available offsets
        start, end = 0, len(ln_raw)
        while len(ln) > 1:
            p1, p2 = ln[0], ln[-1]
            if ln[0][0] == ln[1][0]:
                max_offset = V(1, 0)
                min_offset = V(-1, 0)
                step = V(1, 0)
            elif ln[0][1] == ln[1][1]:
                max_offset = V(0, 1)
                min_offset = V(0, -1)
                step = V(0, 1)
            else:
                raise ValueError(f"the line {ln} is neither horizontal nor vertical")

            while (self.is_valid_empty(p1 + max_offset)
                   and self.is_valid_empty(p2 + max_offset)):
                max_offset = max_offset + step
            while (self.is_valid_empty(p1 + min_offset)
                   and self.is_valid_empty(p2 + min_offset)):
                min_offset = min_offset - step

            if step[0]:  # horizontal offset
                available = [V(i, 0) for i in count(min_offset[0] + 1, max_offset[0])]
            else:
                available = [V(0, i) for i in count(min_offset[1] + 1, max_offset[1])]

            self._update_right_path()
            for p in ln[1:-1]:
                tmp = available.copy()
                for offset in tmp:
                    if self.get_p(p + offset) != Cell.EMPTY:
                        available.remove(offset)

            try:
                available.remove(V(0, 0))
            except ValueError:
                pass

            if not available or available == [0]:
                start, end = choice(range(len(ln))), choice(range(len(ln)))
                start, end = min(start, end), max(start, end)
                ln = ln[start:end]
            else:  # available offsets found
                break
        else:  # no available bend offset for the given line
            return False

        # offset the selected path
        offset = choice(available)
        offset_d = sum(offset)
        insert_pos = self._right_path.index(ln[0])

        self._ls_paths.remove(ln_raw)
        self._ls_paths.append(ln_raw[:start])
        self._ls_paths.append(ln_raw[end:])

        self._right_path = self._right_path[:insert_pos] + self._right_path[insert_pos + len(ln) - 1:]
        for p in ln[1:]:
            self.set_p(p, Cell.EMPTY)

        # path register
        self._right_path = (self._right_path[:insert_pos]
                            + [(p1[0] + step[0] * d, p1[1] + step[1] * d) for d in count(0, offset_d)]
                            + [(p[0] + step[0] * offset_d, p[1] + step[1] * offset_d) for p in ln[:-1]]
                            + [(p2[0] + step[0] * d, p2[1] + step[1] * d) for d in count(offset_d, 0)]
                            + self._right_path[insert_pos:])

        self._ls_paths = []
        delta_prev = V(0, 0)
        seg = []
        for i in range(1, len(self._right_path)):
            if V(self._right_path[i]) - self._right_path[i - 1] == delta_prev:
                seg.append(self._right_path[i - 1])
            else:
                seg.append(self._right_path[i - 1])
                self._ls_paths.append(seg)
                seg = [self._right_path[i - 1]]
            delta_prev = V(self._right_path[i]) - self._right_path[i - 1]
        seg.append(self._right_path[-1])
        self._ls_paths.append(seg)
        self._ls_paths.sort(key=lambda x: len(x), reverse=True)
        return True

    def _gen_right_path(self):
        p1 = self._start
        p2 = self._end
        dy = p2[1] - p1[1]
        dx = p2[0] - p1[0]
        sgn_y = 1 if dy > 0 else -1
        sgn_x = 1 if dx > 0 else -1
        # initial path
        if random() < 0.5:
            self._ls_paths.append([(p1[0] + sgn_x * i, p1[1]) for i in range(0, abs(dx) + 1)])
            self._ls_paths.append([(p2[0], p1[1] + sgn_y * i) for i in range(1, abs(dy) + 1)])
        else:
            self._ls_paths.append([(p1[0], p1[1] + sgn_y * i) for i in range(0, abs(dy) + 1)])
            self._ls_paths.append([(p1[0] + sgn_x * i, p2[1]) for i in range(1, abs(dx) + 1)])
        self._right_path = self._ls_paths[0] + self._ls_paths[1]
        self._update_right_path()

        # add bends
        for i in range(self._width * self._height // 15):
            self._bend()
            self._update_right_path()

    def _gen_branch(self):
        """Add branch paths to the existing paths, randomly."""
        existing = self._right_path.copy()
        while True:  # nested branches
            bp_count = 0
            new = []
            for p in existing:  # branches
                if random() > self.MAKING_BRANCH_PROB:
                    continue
                cur_p = p
                while True:  # a SINGLE path
                    if random() > self.BRANCH_EXTEND_PROB:
                        break
                    available = self._available(cur_p)
                    if len(available) == 0:
                        break
                    else:
                        vec = choice(available)
                        cur_p += vec
                        new.append(cur_p)
                        self.set_p(cur_p, DIR_ENUMS[vec])
                        bp_count += 1
            existing = new
            if bp_count <= self.BRANCH_THR:
                break

    def generate(self):
        if len(self._right_path):
            return
        self._gen_right_path()
        self._gen_branch()
        self._ls_paths = []  # clean up the space


if __name__ == '__main__':
    # a simple save-load test
    import os

    maze = Maze()
    print(maze)
    maze.save("maze1.txt")
    maze = Maze(filepath="maze1.txt")
    print(maze)
    os.remove("maze1.txt")
