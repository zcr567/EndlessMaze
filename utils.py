"""
Low-level tool functions that all modules may use.
Author: ZCR
"""
import sys
import time
from os.path import abspath


# resource path
def resource_path(relative_path):
    """get the packaged resource directory (from previous projects, tested OK)"""
    if hasattr(sys, '_MEIPASS'):
        # packaged env
        # noinspection PyProtectedMember
        base_path = str(sys._MEIPASS)
    else:
        # development env
        base_path = abspath(".")
    return base_path + '\\' + relative_path


# color related
def rgb_to_hsl(r, g, b):
    r_norm = r / 255
    g_norm = g / 255
    b_norm = b / 255

    max_c = max(r_norm, g_norm, b_norm)
    min_c = min(r_norm, g_norm, b_norm)
    delta = max_c - min_c

    # Hue
    h = 0
    if delta != 0:
        if max_c == r_norm:
            h = ((g_norm - b_norm) / delta) % 6
        elif max_c == g_norm:
            h = (b_norm - r_norm) / delta + 2
        else:
            h = (r_norm - g_norm) / delta + 4
    h *= 60

    # Lightness
    lt = (max_c + min_c) * 0.5

    # Saturation
    s = 0.0
    if 0 < lt < 1:
        s = delta / (1 - abs(2 * lt - 1))

    return h % 360, s, lt


def hsl_to_rgb(h, s, lt):
    c = (1 - abs(2 * lt - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = lt - c / 2

    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    return (
        int(round((r + m) * 255)),
        int(round((g + m) * 255)),
        int(round((b + m) * 255))
    )


def adjust_color(color,
                 brightness_factor=1.0,
                 saturation_factor=1.0,
                 hue_offset=0.0):
    """
    Adjust the hue, saturation and brightness of the given color list.
    :param color: color in (r, g, b) or (r, g, b, a) format, components' range from 0 to 255
    :param brightness_factor: brightness factor, brighten the color if it's larger than 1, or darken it
    :param saturation_factor: saturation factor, acts like brightness_factor
    :param hue_offset: valid values are [-360-360]
    :return: adjusted color in original format
    """
    h, s, ls = rgb_to_hsl(*color)
    h = (h + hue_offset) % 360
    s = max(0.0, min(1.0, s * saturation_factor))
    ls = max(0.0, min(1.0, ls * brightness_factor))

    nr, ng, nb = hsl_to_rgb(h, s, ls)

    if len(color) == 4:
        return nr, ng, nb, color[3]

    return nr, ng, nb


class Timer:
    def __init__(self):
        self._start_t = 0.0
        self._paused_t = 0.0
        self._running = False
        self._paused_timedelta = 0.0

    @property
    def running(self):
        return self._running

    def start(self):
        """start the timer, only works if the timer is not running"""
        if not self._running:
            self._start_t = time.perf_counter()
            self._paused_timedelta = 0.0
            self._running = True

    def pause(self):
        """pause the timer"""
        if self._running and self._paused_t == 0.0:
            self._paused_t = time.perf_counter()

    def resume(self):
        """resume the timer"""
        if self._running and self._paused_t != 0.0:
            paused_delta = time.perf_counter() - self._paused_t
            self._paused_timedelta += paused_delta
            self._paused_t = 0.0

    def get(self):
        """return current timedelta"""
        if not self._running:
            return 0.0
        if self._paused_t != 0.0:
            return self._paused_t - self._start_t - self._paused_timedelta
        return time.perf_counter() - self._start_t - self._paused_timedelta

    def get_str(self):
        """return formated string: MM:SS:mmm"""
        total_seconds = self.get()
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds - int(total_seconds)) * 1000)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"

    def clear(self):
        """reset the timer"""
        self._start_t = 0.0
        self._paused_t = 0.0
        self._running = False
        self._paused_timedelta = 0.0
