r"""
(history) the results of the games played so far.

Every finished solo maze and every settled versus match is put on top of this list, and the list is
kept in "records.json" next to the game, so that it survives a restart. A missing, empty or
unreadable file simply means an empty history: the game must never fail because of its own record
keeping, and writing a record must never stop a round from being played.

File format (checked, the same idea as the maze files of this project): the first line is the
md5 of the body, the body is the json of the history and follows on the next lines. Loading compares
the two, so a half written file, a disk error or a hand edited file is recognised instead of being
played back as a broken history. A file without that first line is an older version of the game: it
is read as it is, and the next save writes it back in the checked format.

Packaging (PyInstaller): the file is written next to the executable, not next to this module. That
matters because a one-file build unpacks the code into a temporary folder that PyInstaller deletes
on exit: a history written beside the module would be gone after every session. If the executable
sits in a folder that cannot be written (for instance "C:\Program Files"), the history moves to
the user's home directory instead, and is read back from there next time.

    python -m unittest Tests.test_records -v
"""

import hashlib
import json
import os
import sys
import time

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = "records.json"
LOCATION_ENV = "MAZE_RECORDS_FILE"  # a portable install (or a test) can point the history elsewhere
HOME_DIR = os.path.join(os.path.expanduser("~"), ".endlessmaze")  # where a read-only install keeps it
CHECKSUM_LEN = 32  # md5 hex digest, the checksum line of the file
CORRUPT_SUFFIX = ".corrupt"  # a file that fails its checksum is kept under this name


def checksum(text: str) -> str:
    """the md5 of one text block, exactly like the maze files of this project do it"""
    return hashlib.md5(bytes(text, "utf-8")).hexdigest()


def compose(text: str) -> str:
    """the whole file for one body: the checksum on the first line, then the body"""
    return f"{checksum(text)}\n{text}"


def looks_like_history(body: str) -> bool:
    """whether a file body is a history at all: an older version wrote the json object on its own"""
    return body.lstrip().startswith("{")


def split(text: str):
    """(stored checksum, body); the checksum is None for a file written before it existed"""
    first, sep, rest = text.partition("\n")
    if sep and len(first) == CHECKSUM_LEN and all(c in "0123456789abcdef" for c in first.lower()):
        return first.lower(), rest
    return None, text


def installed_dir():
    """the folder the player started the game from.

    Once PyInstaller packaged the game this is the folder of the executable; a one-file build runs
    from a temporary folder that is deleted on exit, so this must not be the module's folder."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return GAME_DIR


def default_path():
    """where the history lives: next to the game (next to the exe once packaged), or wherever the
    MAZE_RECORDS_FILE environment variable points it"""
    return os.environ.get(LOCATION_ENV) or os.path.join(installed_dir(), FILE_NAME)


class Records:
    """(history) the games played so far, newest first, backed by a json file.

    The file carries a checksum of its own body (see the module docstring). Records.verify() answers
    whether the file on disk is intact, and Records.corrupted tells whether the history that was
    loaded came from a damaged file; a damaged file is kept next to the original as
    "records.json.corrupt" so that nothing is thrown away, and the game simply starts empty."""

    VERSION = 1
    MAX_ENTRIES = 60     # how many games are remembered at all
    SHOWN_ENTRIES = 12   # how many of them the records screen lists (as far as the screen fits)

    def __init__(self, path=None):
        self.path = default_path() if path is None else path
        self.entries = []
        self.corrupted = False  # the file on disk failed its checksum when it was read
        self.legacy = False     # ... it was written before the checksum existed (read as it is)
        self.status = ""        # a short note for the records screen, empty when all is well
        self.load()
        fallback = os.path.join(HOME_DIR, FILE_NAME)
        if not self.entries and not os.path.exists(self.path) and os.path.exists(fallback):
            # a previous session could only write to the home directory; carry on from there
            self.path = fallback
            self.load()

    def verify(self, path=None):
        """(history) check the file against its own checksum: (ok, reason)

        This is the same test the maze files use: the first line has to be the md5 of everything
        that follows. Files written before this check existed have no such line and count as intact,
        they are upgraded the next time the history is saved."""
        path = self.path if path is None else path
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as error:
            return False, f"cannot be read ({error.__class__.__name__})"
        stored, body = split(text)
        if stored is None:
            if looks_like_history(body):
                return True, "no checksum in the file (written by an older version)"
            return False, "the file is neither a checksummed history nor an older one"
        if checksum(body) != stored:
            return False, "the checksum of the file does not match its content"
        return True, "the checksum matches"

    def load(self):
        """read the file, checking it first; anything unreadable counts as an empty history"""
        self.corrupted = False
        self.legacy = False
        self.status = ""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            self.entries = []
            return self.entries

        stored, body = split(text)
        if stored is None and not looks_like_history(body):
            # not a checksummed file and not an older history either: a truncated or damaged write
            self.corrupted = True
            self.status = "the history file is damaged - starting from an empty list"
            self._keep_damaged_file()
            self.entries = []
            return self.entries
        if stored is None:
            self.legacy = True
        elif checksum(body) != stored:
            # the file was damaged (half a write, a disk error, an edit): keep it for the record and
            # start from an empty history instead of playing back something broken
            self.corrupted = True
            self.status = "the history file failed its checksum - starting from an empty list"
            self._keep_damaged_file()
            self.entries = []
            return self.entries

        try:
            data = json.loads(body)
        except ValueError:
            data = None
        entries = data.get("entries") if isinstance(data, dict) else None
        self.entries = [entry for entry in entries if isinstance(entry, dict) and entry.get("mode")] \
            if isinstance(entries, list) else []
        if self.legacy:
            self.status = "the history file has no checksum yet - it is written with one from now on"
        return self.entries

    def _keep_damaged_file(self):
        """put a damaged file aside, so that nothing is thrown away"""
        try:
            if os.path.exists(self.path):
                os.replace(self.path, self.path + CORRUPT_SUFFIX)
        except OSError:
            pass  # keeping a copy is a courtesy, never a reason to stop the game

    def save(self):
        """write the file, checksum first; a failure here is reported but never raised"""
        payload = {"version": self.VERSION, "entries": self.entries}
        text = json.dumps(payload, ensure_ascii=False, indent=1)
        if self._write(self.path, compose(text)):
            self.corrupted = self.legacy = False
            self.status = ""
            return True
        fallback = os.path.join(HOME_DIR, FILE_NAME)
        if self.path != fallback and self._write(fallback, compose(text)):
            self.path = fallback  # a read-only install keeps its history at home from now on
            self.corrupted = self.legacy = False
            self.status = ""
            return True
        return False

    @staticmethod
    def _write(path, text):
        """write one file, creating its folder when needed; never raises"""
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except OSError:
            return False

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

    @staticmethod
    def row_text(entry):
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
