"""
(history) the results of the games played so far.

Every finished solo maze and every settled versus match is put on top of this list, and the list is
kept in "records.json" next to the game, so that it survives a restart. A missing, empty or
unreadable file simply means an empty history: the game must never fail because of its own record
keeping, and writing a record must never stop a round from being played.

    python -m unittest Tests.test_records -v
"""

import json
import os
import time

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = "records.json"
LOCATION_ENV = "MAZE_RECORDS_FILE"  # a portable install (or a test) can point the history elsewhere


def default_path():
    """where the history lives: next to the game, unless that was overridden"""
    return os.environ.get(LOCATION_ENV) or os.path.join(GAME_DIR, FILE_NAME)


class Records:
    """(history) the games played so far, newest first, backed by a json file."""

    VERSION = 1
    MAX_ENTRIES = 60     # how many games are remembered at all
    SHOWN_ENTRIES = 12   # how many of them the records screen lists (as far as the screen fits)

    def __init__(self, path=None):
        self.path = default_path() if path is None else path
        self.entries = []
        self.load()

    # ---------------------------------------------------------------- reading
    def load(self):
        """read the file; anything unreadable simply counts as an empty history"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = None
        entries = data.get("entries") if isinstance(data, dict) else None
        self.entries = [entry for entry in entries if isinstance(entry, dict) and entry.get("mode")] \
            if isinstance(entries, list) else []
        return self.entries

    def save(self):
        """write the file; a failure here is reported but never raised"""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"version": self.VERSION, "entries": self.entries},
                          f, ensure_ascii=False, indent=1)
            return True
        except OSError:
            return False

    # ---------------------------------------------------------------- writing
    def add(self, entry):
        """put one result on top of the list and keep the file up to date"""
        entry.setdefault("at", time.strftime("%Y-%m-%d %H:%M"))
        self.entries.insert(0, entry)
        del self.entries[self.MAX_ENTRIES:]
        self.save()
        return entry

    def add_single(self, game):
        """(history) a finished solo maze: its time, its score and the maze it was played on"""
        return self.add({"mode": "single",
                         "time": game.timer.get_str(),
                         "score": int(game.players[0].score) if game.players else 0,
                         "size": f"{game.field_width}x{game.field_height}",
                         "difficulty": game.difficulty})

    def add_versus(self, game, winner):
        """(history) a settled versus match: who won it, and what the two players scored"""
        players = list(game.players)
        return self.add({"mode": "versus",
                         "winner": winner,
                         "scores": [int(p.score) for p in players],
                         "deaths": [int(p.eaten) for p in players]})

    def clear(self):
        """forget everything, on disk as well"""
        self.entries = []
        return self.save()

    # ------------------------------------------------------------- looking at it
    def shown(self, count=None):
        """the entries the records screen lists, newest first"""
        count = self.SHOWN_ENTRIES if count is None else count
        return self.entries[:count]

    def of_mode(self, mode):
        """every entry of one game mode"""
        return [entry for entry in self.entries if entry.get("mode") == mode]

    def best_single(self):
        """the best solo score so far, or None when no solo maze was finished yet"""
        scores = [int(entry.get("score", 0)) for entry in self.of_mode("single")]
        return max(scores) if scores else None

    def row_text(self, entry):
        """one line of the records screen for one entry"""
        when = entry.get("at", "")
        if entry.get("mode") == "versus":
            scores = list(entry.get("scores", [])) or [0, 0]
            deaths = list(entry.get("deaths", [])) or [0, 0]
            pairs = "   ".join(f"P{i + 1} pts {score} deaths {deaths[i] if i < len(deaths) else 0}"
                               for i, score in enumerate(scores))
            return f"{when}   VERSUS   {entry.get('winner', '-'):<9} {pairs}"
        return (f"{when}   SINGLE   {entry.get('size', ''):<7} {entry.get('difficulty', ''):<7}"
                f"{entry.get('time', ''):<11} pts {entry.get('score', 0)}")

    def __len__(self):
        return len(self.entries)
