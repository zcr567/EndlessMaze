"""
A simple widget module for pygame first version written by zyw and refactored by zcr .
"""

import math
import random
from enum import IntEnum, IntFlag

import pygame
import pygame as pg

from Resources import *
from effects import Linear, Quad, DoubleQuad, ReversedQuad, Fade, Shadow, ChangeColor, RoundMaskFade
from maze import Maze, SIZE_PRESETS, DIFFICULTY_PRESETS
from utils import adjust_color, Timer
# noinspection PyPep8Naming
from vectors import Vector as V, Cell, DIR_VECS

# colors to be used
DISABLED_TEXT = (132, 152, 146)
HINT_TEXT = (70, 105, 95)

main_color = (63, 122, 106)
palette = [(0, 0, 0)] + [adjust_color(main_color, i) for i in (0.2, 0.4, 0.8, 1, 1.2, 1.8, 2)] + [(255, 255, 255)]

_font_cache = {}


def set_theme(color):
    global main_color, palette
    main_color = color
    palette = [(0, 0, 0)] + [adjust_color(main_color, i) for i in (0.2, 0.4, 0.8, 1, 1.2, 1.8, 2)] + [(255, 255, 255)]


def make_font(size, bold=False):
    key = (size, bold)
    font = _font_cache.get(key)
    if font is None:
        font = pg.font.Font(main_font_path, int(size))
        font.set_bold(bold)
        _font_cache[key] = font
    return font


def icon_coloring(surface, color):
    img = surface.copy().convert_alpha()
    img.fill((*color, 255), special_flags=pg.BLEND_RGBA_MULT)
    return img


def vertical_gradient(size, top_color, bottom_color):
    w, h = size
    surf = pg.Surface((w, h))
    for y in range(h):
        t = y / (h - 1)
        color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        pg.draw.line(surf, color, (0, y), (w, y))
    return surf


class ButtonBase:
    def __init__(self, callback=None):
        self.rect = pg.Rect(0, 0, 10, 10)
        self.enabled = True
        self.pressed = False
        self.callback = callback

    def set_rect(self, rect):
        self.rect = pg.Rect(rect)

    def _hovered(self):
        return self.enabled and self.rect.collidepoint(pg.mouse.get_pos())

    def handle_event(self, event):
        if not self.enabled:
            return False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                if self.callback is not None:
                    self.callback()
                    return True
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.pressed = False
        return False


class Button(ButtonBase):

    def __init__(self, text="", icon=None, style="ghost", on_light=False, callback=None):
        """
        A rounded button that can hold text or icon.
            :param style: Literal["solid"|"ghost"]
                "solid" (filled teal, white content)
                "ghost" (frosted white, teal content)
            :param on_light: in case of ghost buttons being placed on a white background
            :param callback: callback function, accepting no arguments any of its return will be
                discarded
            icon must be handled by icon_coloring
        """
        super().__init__(callback=callback)
        self.text = text
        self.icon = icon
        self.style = style
        self.on_light = on_light

    def draw(self, surface):
        radius = self.rect.height // 2
        if self.style == "solid":
            if not self.enabled:
                fill = palette[4]
            elif self.pressed:
                fill = palette[3]
            elif self._hovered():
                fill = palette[5]
            else:
                fill = main_color
            pg.draw.rect(surface, fill, self.rect, border_radius=radius)
            content_color = palette[-1]
        elif self.on_light:
            # ghost button on a white panel: a light mist-teal fill keeps it visible
            if self.pressed:
                fill = (215, 230, 225)
            elif self._hovered():
                fill = (225, 240, 235)
            else:
                fill = (235, 240, 240)
            pg.draw.rect(surface, fill, self.rect, border_radius=radius)
            content_color = main_color
        else:  # ghost
            if not self.enabled:
                alpha = 110
                content_color = DISABLED_TEXT
            elif self.pressed:
                alpha = 200
                content_color = palette[4]
            elif self._hovered():
                alpha = 255
                content_color = palette[5]
            else:
                alpha = 225
                content_color = palette[4]
            pill = pg.Surface(self.rect.size, pg.SRCALPHA)
            pg.draw.rect(pill, (255, 255, 255, alpha), pill.get_rect(), border_radius=radius)
            surface.blit(pill, self.rect)

        # lay out icon + text as one centered group
        parts = []
        if self.icon is not None:
            icon_size = int(self.rect.height * 0.46)
            parts.append(pg.transform.smoothscale(self.icon, (icon_size, icon_size)))
        if self.text:
            parts.append(make_font(int(self.rect.height * 0.40)).render(self.text, True, content_color))
        gap = 10
        total_w = sum(p.get_width() for p in parts) + gap * (len(parts) - 1)
        x = self.rect.centerx - total_w // 2
        for p in parts:
            surface.blit(p, (x, self.rect.centery - p.get_height() // 2))
            x += p.get_width() + gap


class IconButton(ButtonBase):
    def __init__(self, icon: pg.Surface, size=44, callback=None, enabled=True):
        """
        a small round button showing an icon
            :param icon: the icon to be shown
            :param size: size of the icon
            :param callback: callback function, accepting 1 positional argument "button", any of its return will be
                discarded
            icon must be handled by icon_coloring
        """
        super().__init__(callback=callback)
        self.icon = icon
        self.size = size
        self.rect = pg.Rect(0, 0, size, size)
        self.pressed = False
        self.enabled = enabled

    def draw(self, surface):
        if self.pressed:
            alpha = 200
        elif self._hovered():
            alpha = 255
        else:
            alpha = 220

        # noinspection DuplicatedCode
        circle = pg.Surface((self.size, self.size), pg.SRCALPHA)
        pg.draw.circle(circle, (255, 255, 255, alpha), (self.size // 2, self.size // 2), self.size // 2)
        surface.blit(circle, self.rect)
        icon_size = int(self.size * 0.56)
        icon = pg.transform.smoothscale(self.icon, (icon_size, icon_size))
        surface.blit(icon, (self.rect.centerx - icon_size // 2, self.rect.centery - icon_size // 2))


class IconToggleButton(IconButton):
    _group_dict = {}

    def __init__(self, icon: pg.Surface, icon_pressed=None, group=None, size=64, callback=None, enabled=True,
                 allow_all_release=True):
        super().__init__(icon, size, callback, enabled)
        self.icon_pressed = icon_pressed
        if group is not None:
            if group in self._group_dict:
                self._group_dict[group].append(self)
            else:
                self._group_dict[group] = [self]
            self.group = group
        else:
            self.group = f"btn_{len(self._group_dict)}"
            self._group_dict[self.group] = [self]
        self.allow_all_release = allow_all_release

    def handle_event(self, event):
        if not self.enabled:
            return False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                new_state = not self.pressed
                if new_state is False:
                    if self.allow_all_release:
                        self.pressed = False
                        if self.callback is not None:
                            self.callback()
                            return True
                    else:
                        return False
                else:
                    for btn in self._group_dict[self.group]:
                        btn.pressed = False
                    self.pressed = True
                    if self.callback is not None:
                        self.callback()
                        return True
        return False

    def draw(self, surface):
        if self.pressed and self.icon_pressed is None:
            alpha = 175
        elif self._hovered():
            alpha = 255
        else:
            alpha = 220

        # noinspection DuplicatedCode
        circle = pg.Surface((self.size, self.size), pg.SRCALPHA)
        pg.draw.circle(circle, (255, 255, 255, alpha), (self.size // 2, self.size // 2), self.size // 2)
        surface.blit(circle, self.rect)
        icon_size = int(self.size * 0.56)
        if self.pressed and self.icon_pressed is not None:
            icon = pg.transform.smoothscale(self.icon_pressed, (icon_size, icon_size))
        else:
            icon = pg.transform.smoothscale(self.icon, (icon_size, icon_size))
        surface.blit(icon, (self.rect.centerx - icon_size // 2, self.rect.centery - icon_size // 2))


class OptionSelector:
    # A labeled [<] current option [>] stepper laid out in one row.

    def __init__(self, label, options: list[str], index=0, callback=None):
        self.label = label
        self.options = options
        self.index = index
        self.rect = pg.Rect(0, 0, 10, 10)
        self._pill_rect = pg.Rect(0, 0, 10, 10)
        self._left_rect = pg.Rect(0, 0, 10, 10)
        self._right_rect = pg.Rect(0, 0, 10, 10)
        self._pressed = None
        self.callback = callback

    @property
    def value(self):
        return self.options[self.index]

    def set_rect(self, rect):
        self.rect = pg.Rect(rect)
        h = self.rect.height
        pill_w = int(self.rect.width * 0.58)
        self._pill_rect = pg.Rect(self.rect.right - pill_w, self.rect.y, pill_w, h)
        self._left_rect = pg.Rect(self._pill_rect.x, self.rect.y, h, h)
        self._right_rect = pg.Rect(self._pill_rect.right - h, self.rect.y, h, h)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self._left_rect.collidepoint(event.pos):
                self._pressed = "left"
            elif self._right_rect.collidepoint(event.pos):
                self._pressed = "right"
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            hit = self._pressed
            self._pressed = None
            if hit == "left" and self._left_rect.collidepoint(event.pos):
                self._step(-1)
                if self.callback is not None:
                    self.callback(self.value)
                return True
            if hit == "right" and self._right_rect.collidepoint(event.pos):
                self._step(1)
                if self.callback is not None:
                    self.callback(self.value)
                return True
        return False

    def _step(self, direction):
        self.index = (self.index + direction) % len(self.options)

    def draw(self, surface):
        # label
        font = make_font(int(self.rect.height * 0.46))
        text = font.render(self.label, True, main_color)
        surface.blit(text, (self.rect.x, self.rect.centery - text.get_height() // 2))

        # pill
        pill = pg.Surface(self._pill_rect.size, pg.SRCALPHA)
        pg.draw.rect(pill, (255, 255, 255, 220), pill.get_rect(),
                     border_radius=self._pill_rect.height // 2)
        surface.blit(pill, self._pill_rect)

        # current option
        font = make_font(int(self.rect.height * 0.40))
        text = font.render(self.options[self.index].upper(), True, main_color)
        surface.blit(text, (self._pill_rect.centerx - text.get_width() // 2,
                            self._pill_rect.centery - text.get_height() // 2))

        # arrows
        for side, rect in (("left", self._left_rect), ("right", self._right_rect)):
            hovered = rect.collidepoint(pg.mouse.get_pos())
            color = palette[5] if self._pressed == side or hovered else palette[4]
            cx, cy = rect.center
            w, hh = self.rect.height * 0.10, self.rect.height * 0.16
            if side == "right":
                points = ((cx - w, cy - hh), (cx + w, cy), (cx - w, cy + hh))
            else:
                points = ((cx + w, cy - hh), (cx - w, cy), (cx + w, cy + hh))
            pg.draw.polygon(surface, color, points)


class GameScreen:
    def resize(self, size: tuple[int, int] | V) -> None: ...

    def handle_events(self, events: list[pg.event.Event]) -> list[pg.event.Event]: ...

    def draw(self, surface: pg.Surface) -> None: ...


class WelcomeScreen(GameScreen):
    # The main menu

    DECO_COLS = 40
    DECO_ROWS = 30

    # title float animation hyperparameters
    TITLE_FLOAT_STEP = 120  # frames per half cycle
    TITLE_FLOAT_AMP = 6  # vertical float amplitude in pixels

    def __init__(self,
                 size,
                 sound_switch_cb=None,
                 single_player_cb=None,
                 double_player_cb=None,
                 size_set_cb=None,
                 diff_set_cb=None,
                 vision_set_cb=None,
                 open_rec_cb=None):
        self.size = size

        # decorative faint maze behind the menu
        self._deco = Maze((self.DECO_COLS, self.DECO_ROWS),
                          start=(0, 0), end=(self.DECO_COLS - 1, self.DECO_ROWS - 1))
        self._deco_inst = self._deco.draw_instructions()
        self._deco_surf = None

        self.sound_btn = IconToggleButton(icon_coloring(icons_dict["sound_on"], main_color),
                                          icon_coloring(icons_dict["sound_off"], main_color),
                                          size=46, callback=sound_switch_cb)
        self.single_btn = Button("SINGLE PLAYER", icon=icons_dict["play"], style="solid", callback=single_player_cb)
        self.double_btn = Button("TWO PLAYER", style="ghost", callback=double_player_cb)
        self.records_btn = Button("RECORDS", style="ghost", callback=open_rec_cb)

        # maze option selectors; option keys follow the maze preset dictionaries
        self.size_selector = OptionSelector("SIZE", list(SIZE_PRESETS), index=1, callback=size_set_cb)
        self.diff_selector = OptionSelector("DIFFICULTY", list(DIFFICULTY_PRESETS), index=1, callback=diff_set_cb)
        self.vision_selector = OptionSelector("VISION", list(VISION_PRESETS), index=0, callback=vision_set_cb)
        self._card_rect = pg.Rect(0, 0, 10, 10)

        self.bg = None
        self.title_img = None
        self.title_pos = (0, 0)
        self.title_shadow = None
        self.title_intp = DoubleQuad(step=self.TITLE_FLOAT_STEP)
        self.hint_img = None
        self.hint_pos = (0, 0)
        self.resize(size)

    @property
    def difficulty(self):
        return self.diff_selector.value

    def _render_deco(self):
        # Render the faint decorative maze, centered behind the menu.
        w, h = self.size
        cols, rows = self.DECO_COLS, self.DECO_ROWS
        cw = max(w / cols, h / rows)
        edge_w = max(4, int(cw // 8))
        mw, mh = cw * cols, cw * rows
        ox, oy = (w - mw) / 2, (h - mh) / 2 + h * 0.01
        self._deco_surf = pg.Surface((w, h), pg.SRCALPHA)
        line_color = (255, 255, 255, 46)
        inst = self._deco_inst
        for row in range(rows * 2 + 1):
            for col in range(cols * 2 + 1):
                op = inst[row][col]
                x = int(ox + cw * (col // 2))
                y = int(oy + cw * (row // 2))
                if row % 2 == 0 and col % 2 == 1 and op == 0:
                    pg.draw.line(self._deco_surf, line_color, (x, y), (x + int(cw), y), edge_w)
                elif row % 2 == 1 and col % 2 == 0 and op == 0:
                    pg.draw.line(self._deco_surf, line_color, (x, y), (x, y + int(cw)), edge_w)
                if row % 2 == 0 and col % 2 == 0 and edge_w > 2:
                    pg.draw.circle(self._deco_surf, line_color, (x, y), edge_w // 2)

    def _update_title(self):
        # Advance the title float animation by one frame.
        self.title_intp.update()
        p = self.title_intp.get()
        if self.title_intp.direction == 1 and p >= 1.0:
            self.title_intp.switch()
        elif self.title_intp.direction == -1 and p <= 0.0:
            self.title_intp.switch()

    def resize(self, size):
        self.size = size
        w, h = size
        self.bg = vertical_gradient(
            size,
            adjust_color(palette[-3],
                         hue_offset=5,
                         saturation_factor=0.8),
            adjust_color(palette[-3],
                         hue_offset=-5,
                         saturation_factor=0.8,
                         brightness_factor=0.95))
        self._render_deco()

        # title: up to 86% of the width and 13% of the height, keeps aspect
        aspect = title.get_width() / title.get_height()
        title_h = min(int(h * 0.13), int(w * 0.86 / aspect))
        title_w = int(title_h * aspect)
        self.title_img = pg.transform.smoothscale(title.convert_alpha(), (title_w, title_h))
        shadow = title.copy().convert_alpha()
        shadow.fill((45, 85, 75, 255), special_flags=pg.BLEND_RGBA_MULT)
        self.title_shadow = pg.transform.smoothscale(shadow, (title_w, title_h))
        self.title_shadow.set_alpha(60)
        self.title_pos = ((w - title_w) // 2, int(h * 0.15) - title_h // 2)

        # options card
        cx = w // 2
        btn_w = min(int(w * 0.66), 320)
        card_h = min(150, max(96, int(h * 0.18)))
        card_top = int(h * 0.335)
        self._card_rect = pg.Rect(cx - btn_w // 2, card_top, btn_w, card_h)
        pad_x, pad_y = 18, 12
        row_h = (card_h - pad_y * 3) // 2
        row_x = self._card_rect.x + pad_x
        row_w = btn_w - pad_x * 2
        self.size_selector.set_rect(
            (row_x, card_top + pad_y, row_w, row_h))
        self.diff_selector.set_rect(
            (row_x, card_top + pad_y * 2 + row_h, row_w, row_h))

        # buttons
        btn_h = max(54, int(h * 0.078))
        gap = int(btn_h * 0.4)
        top = self._card_rect.bottom + gap
        self.single_btn.set_rect((cx - btn_w // 2, top, btn_w, btn_h))
        self.double_btn.set_rect((cx - btn_w // 2, top + btn_h + gap, btn_w, btn_h))
        self.vision_selector.set_rect(
            (cx - btn_w // 2, self.double_btn.rect.bottom + gap, btn_w, row_h))

        s = self.sound_btn.size
        self.sound_btn.set_rect((w - s - 22, 22, s, s))
        rec_w = min(int(w * 0.16), 150)
        self.records_btn.set_rect((w - s - 22 - rec_w - 12, 22, rec_w, s))

        self.hint_img = make_font(max(14, int(h * 0.022))).render(
            "MADE BY ZCR & ZYW", True, palette[-1])
        self.hint_img.set_alpha(255)
        self.hint_pos = (cx - self.hint_img.get_width() // 2, h - self.hint_img.get_height() - 26)

    def handle_events(self, events):
        # Process one frame's events, return an action string or None.
        for event in events:
            # (limited vision) the third option row reacts on its own, the chain below is untouched
            self.vision_selector.handle_event(event)
            # (history) and so does the records button of the top row
            self.records_btn.handle_event(event)
            if (self.sound_btn.handle_event(event)
                    or self.single_btn.handle_event(event)
                    or self.double_btn.handle_event(event)
                    or self.size_selector.handle_event(event)
                    or self.diff_selector.handle_event(event)):
                events.remove(event)
        return events

    def draw(self, surface):
        self._update_title()
        surface.blit(self.bg, (0, 0))
        surface.blit(self._deco_surf, (0, 0))
        # title float: a gentle vertical bobbing driven by title_intp
        amp = self.title_intp.get()
        float_y = int(round(amp * self.TITLE_FLOAT_AMP))
        surface.blit(self.title_shadow, (self.title_pos[0] + 3, self.title_pos[1] + 5 + float_y))
        surface.blit(self.title_img, (self.title_pos[0], self.title_pos[1] + float_y))

        # options card
        card = pg.Surface(self._card_rect.size, pg.SRCALPHA)
        pg.draw.rect(card, (255, 255, 255, 150), card.get_rect(), border_radius=22)
        surface.blit(card, self._card_rect)

        self.size_selector.draw(surface)
        self.diff_selector.draw(surface)
        self.vision_selector.draw(surface)
        self.double_btn.draw(surface)
        self.single_btn.draw(surface)
        self.sound_btn.draw(surface)
        self.records_btn.draw(surface)
        surface.blit(self.hint_img, self.hint_pos)


class HUD(GameScreen):
    # In-game heads-up display: P1/P2 score rows on top, sound / pause buttons at the bottom corners.

    # layout hyperparameters
    MARGIN = 16
    SCORE_ICON_SIZE = 28  # skull / eat icon size in pixels
    SCORE_GAP = 8  # gap between the label and the score items
    SCORE_FONT_SIZE = 20
    SCORE_COLOR = (255, 255, 255)  # score number color
    LABEL_H = 66  # P1/P2 title image height
    LABEL_H_RATIO = 0.09  # title height also capped to this fraction of window height

    def __init__(self, size, game_mode=None,
                 pause_cb=None, sound_switch_cb=None, fetch_scores_cb=None):
        """
            :param game_mode: GameMode.SINGLE shows the skull only;
                "GameMode.DOUBLE" shows the skull and the eat icon for both players
            :param pause_cb: called when the pause button is hit, no arguments
            :param sound_switch_cb: called when the sound button is toggled, no arguments
            :param fetch_scores_cb: called every frame to fetch per-player scores,
                expected to return [(eaten, eat), ...] in player order
        """
        self.size = size
        # GameMode is defined below in this module, so the default is resolved here
        self.game_mode = GameMode.SINGLE if game_mode is None else game_mode
        self.fetch_scores_cb = fetch_scores_cb
        # (two-player mode) optional source of the two role names, drawn as role tags
        self.fetch_roles_cb = None
        # (single player) optional source of the scores, drawn as "pts N"
        self.fetch_points_cb = None

        self.pause_btn = IconButton(icon_coloring(icons_dict["pause"], main_color),
                                    size=42, callback=pause_cb)
        self.sound_btn = IconToggleButton(icon_coloring(icons_dict["sound_on"], main_color),
                                          icon_coloring(icons_dict["sound_off"], main_color),
                                          size=46, callback=sound_switch_cb)

        self._kill_icon = None
        self._eat_icon = None
        self._p1_label = None
        self._p2_label = None
        self.resize(size)

    def set_sound(self, sound_on: bool):
        self.sound_btn.pressed = not sound_on

    def set_game_mode(self, game_mode):
        self.game_mode = game_mode

    def _points(self, index):
        """(single player) the score of one player, 0 while no source is wired up"""
        if self.fetch_points_cb is None:
            return 0
        points = self.fetch_points_cb()
        return points[index] if index < len(points) else 0

    def _role_label(self, index):
        """(two-player mode) the role tag of one player, empty when the mode hands out no roles."""
        if self.fetch_roles_cb is None:
            return ""
        roles = self.fetch_roles_cb()
        return roles[index] if index < len(roles) else ""

    def resize(self, size):
        self.size = size
        w, h = size
        label_h = min(self.LABEL_H, int(h * self.LABEL_H_RATIO))
        self._p1_label = self._scale_label("P1_title", label_h)
        self._p2_label = self._scale_label("P2_title", label_h)
        self._kill_icon = pg.transform.smoothscale(
            icons_dict["dead_icon"].convert_alpha(),
            (self.SCORE_ICON_SIZE, self.SCORE_ICON_SIZE))
        self._eat_icon = pg.transform.smoothscale(
            icons_dict["eat_icon_v1"].convert_alpha(),
            (self.SCORE_ICON_SIZE, self.SCORE_ICON_SIZE))

        # bottom corners: sound on the left, pause on the right
        s = self.sound_btn.size
        self.sound_btn.set_rect((self.MARGIN, h - s - self.MARGIN, s, s))
        p = self.pause_btn.size
        self.pause_btn.set_rect((w - p - self.MARGIN, h - p - self.MARGIN, p, p))

    @staticmethod
    def _scale_label(key, label_h):
        img = icons_dict[key]
        aspect = img.get_width() / img.get_height()
        return pg.transform.smoothscale(img.convert_alpha(), (int(label_h * aspect), label_h))

    def _fetch_scores(self):
        # fall back to a single zeroed P1 when no data source is available
        if self.fetch_scores_cb is not None:
            fetched = self.fetch_scores_cb()
            if fetched:
                return fetched
        return [(0, 0)]

    def _score_width(self, icon, count) -> int:
        # pixel width of a bare "icon + x N" score (no background)
        tw, _ = make_font(self.SCORE_FONT_SIZE).size(f"x {count}")
        return icon.get_width() + 6 + tw

    def _draw_score(self, surface, x, y, row_h, icon, count) -> int:
        # draw icon + "x N" vertically centered in row_h; returns the score width
        surface.blit(icon, (x, y + (row_h - icon.get_height()) // 2))
        text = make_font(self.SCORE_FONT_SIZE).render(f"x {count}", True, self.SCORE_COLOR)
        surface.blit(text, (x + icon.get_width() + 6,
                            y + (row_h - text.get_height()) // 2))
        return self._score_width(icon, count)

    def _player_row_width(self, label, scores) -> int:
        # total width of a label + score row (for right-alignment)
        return (label.get_width()
                + sum(self._score_width(icon, c) for icon, c in scores)
                + self.SCORE_GAP * len(scores))

    def _draw_player_row(self, surface, x, y, label, scores, label_on_right=False):
        """Draw one player row, everything vertically centered on the label height.

        P1 order: label then scores; P2 (label_on_right=True) mirrors it:
        scores then label, so the P2 title sits next to the screen edge.
        """
        row_h = label.get_height()
        cx = x
        if not label_on_right:
            surface.blit(label, (cx, y))
            cx += label.get_width() + self.SCORE_GAP
            for icon, c in scores:
                cx += self._draw_score(surface, cx, y, row_h, icon, c) + self.SCORE_GAP
        else:
            for icon, c in reversed(scores):
                cx += self._draw_score(surface, cx, y, row_h, icon, c) + self.SCORE_GAP
            surface.blit(label, (cx - self.SCORE_GAP, y))

    def handle_events(self, events):
        # buttons act through callbacks; consumed events are filtered out
        for event in events:
            if (self.pause_btn.handle_event(event)
                    or self.sound_btn.handle_event(event)):
                events.remove(event)
        return events

    def draw(self, surface):
        scores = self._fetch_scores()
        y = self.MARGIN
        w, _ = self.size

        # P1 panel (top-left); single mode keeps the skull only
        p1_scores = [(self._kill_icon, scores[0][0])]
        if self.game_mode == GameMode.DOUBLE:
            p1_scores.append((self._eat_icon, scores[0][1]))
        self._draw_player_row(surface, self.MARGIN, y, self._p1_label, p1_scores)

        # P2 panel (top-right), mirrored; double mode only
        if self.game_mode == GameMode.DOUBLE and len(scores) > 1:
            p2_scores = [(self._kill_icon, scores[1][0]), (self._eat_icon, scores[1][1])]
            row_w = self._player_row_width(self._p2_label, p2_scores)
            self._draw_player_row(surface, w - self.MARGIN - row_w, y,
                                  self._p2_label, p2_scores, label_on_right=True)

        # bottom corners
        self.sound_btn.draw(surface)
        self.pause_btn.draw(surface)


class PauseScreen(GameScreen):
    # Pause overlay: dark scrim + centered white panel with resume / menu / sound.

    def __init__(self, size, resume_cb=None, menu_cb=None, sound_switch_cb=None):
        """
            :param resume_cb: called when RESUME is hit, no arguments
            :param menu_cb: called when MENU is hit, no arguments
            :param sound_switch_cb: called when the sound button is toggled, no arguments
        """
        self.size = size
        self.resume_btn = Button("RESUME", icon=icons_dict["play"], style="solid", callback=resume_cb)
        self.menu_btn = Button("MENU", style="ghost", on_light=True, callback=menu_cb)
        self.sound_btn = IconToggleButton(icon_coloring(icons_dict["sound_on"], main_color),
                                          icon_coloring(icons_dict["sound_off"], main_color),
                                          size=46, callback=sound_switch_cb)
        self._panel_rect = None
        self._panel_title = None
        self._panel_hint = None
        self.resize(size)

    def set_sound(self, sound_on: bool):
        self.sound_btn.pressed = not sound_on

    def resize(self, size):
        self.size = size
        w, h = size
        pw, ph = min(int(w * 0.78), 380), 250
        self._panel_rect = pg.Rect((w - pw) // 2, (h - ph) // 2, pw, ph)
        btn_w, btn_h = int(pw * 0.62), 52
        bx = self._panel_rect.centerx - btn_w // 2
        self.resume_btn.set_rect((bx, self._panel_rect.y + 100, btn_w, btn_h))
        self.menu_btn.set_rect((bx, self._panel_rect.y + 100 + btn_h + 18, btn_w, btn_h))
        s = self.sound_btn.size
        self.sound_btn.set_rect((self._panel_rect.right - s - 16, self._panel_rect.y + 16, s, s))
        self._panel_title = make_font(30).render("PAUSED", True, main_color)
        self._panel_hint = make_font(16).render("PRESS ESC TO RESUME", True, HINT_TEXT)

    def handle_events(self, events):
        # buttons act through callbacks; consumed events are filtered out
        for event in events:
            if (self.resume_btn.handle_event(event)
                    or self.menu_btn.handle_event(event)
                    or self.sound_btn.handle_event(event)):
                events.remove(event)
        return events

    def draw(self, surface):
        w, h = self.size

        # dark scrim over the whole screen
        scrim = pg.Surface((w, h), pg.SRCALPHA)
        scrim.fill((35, 58, 52, 120))
        surface.blit(scrim, (0, 0))

        r = self._panel_rect
        panel = pg.Surface(r.size, pg.SRCALPHA)
        pg.draw.rect(panel, (255, 255, 255, 245), panel.get_rect(), border_radius=24)
        surface.blit(panel, r)

        surface.blit(self._panel_title,
                     (r.centerx - self._panel_title.get_width() // 2, r.y + 34))
        surface.blit(self._panel_hint,
                     (r.centerx - self._panel_hint.get_width() // 2, r.y + 72))
        self.resume_btn.draw(surface)
        self.menu_btn.draw(surface)
        self.sound_btn.draw(surface)


class PlayerType(IntEnum):
    SINGLE = 0
    PREDATOR = 1
    PREY = 2


class GameMode(IntEnum):
    SINGLE = 0
    DOUBLE = 1


class DispState(IntFlag):
    IDLE = 1
    MOVING = 2
    ROTATING = 4
    DYING = 8


class Player:
    """Player class."""

    def __init__(self, game=None, pos0=V(0, 0), heading=Cell.GO_UP, player_type=PlayerType.SINGLE):
        # basic properties
        self._game: MazeGame = game
        self.maze: Maze = None if self._game is None else self._game.maze
        self.player_type = player_type
        self.pos = pos0
        self._heading = heading
        self.size = (0, 0) if self.game is None else (self._game.cell_width * 1.2, self._game.cell_width * 1.2)

        # game logic
        self.score = 0
        self.eaten = 0
        self.eat = 0

        # display
        if self.player_type == PlayerType.PREDATOR:
            self.anim_dict: dict[Cell:Animation] = predator_anim_dict
        else:
            self.anim_dict: dict[Cell:Animation] = prey_anim_dict
        self.cur_anim: Animation = self.anim_dict[self._heading]
        if self._game is not None:
            self.cur_anim.set_position(self.pos_to_surf())
        self.disp_state = DispState.IDLE

        self.movement_intp = ReversedQuad(step=15)
        self.pos_next = self.pos
        self.movement_vec = V(0, 0)

    @property
    def game(self):
        return self._game

    @game.setter
    def game(self, game):
        self._game = game
        self.maze = game.maze
        self.cur_anim.set_position(self.pos_to_surf())
        self.size = (self._game.cell_width * 1.2, self._game.cell_width * 1.2)

    @property
    def heading(self):
        return self._heading

    @heading.setter
    def heading(self, heading):
        # This should be rewritten if a rotate animation is added
        self._heading = heading
        fid = self.cur_anim.get_frame_id()
        pos = self.cur_anim.get_position()
        self.cur_anim = self.anim_dict[self._heading]
        self.cur_anim.set_frame_id(fid)
        self.cur_anim.set_position(pos)

    def set_player_type(self, player_type):
        """switch this player's role: swap the animation set and keep the
        current frame and position."""
        self.player_type = player_type
        self.anim_dict = predator_anim_dict if player_type == PlayerType.PREDATOR else prey_anim_dict
        fid = self.cur_anim.get_frame_id()
        pos = self.cur_anim.get_position()
        self.cur_anim = self.anim_dict[self._heading]
        self.cur_anim.set_frame_id(fid)
        self.cur_anim.set_position(pos)

    def pos_to_surf(self, pos=None):
        """return the current position in maze_surf coordinates"""
        if pos is None:
            return V(int(self._game.region[0] + self._game.cell_width * (self.pos[0] + 0.5) + 1),
                     int(self._game.region[1] + self._game.cell_width * (self.pos[1] + 0.5)) + 1)
        else:
            return V(int(self._game.region[0] + self._game.cell_width * (pos[0] + 0.5) + 1),
                     int(self._game.region[1] + self._game.cell_width * (pos[1] + 0.5)) + 1)

    def _is_available(self, vec):
        """return True if there is no obstacle between 'self.pos_next' and 'self.pos_next + vec'"""
        # (one-way doors) a one-way passage may only be walked the way its arrow points
        if self.maze.blocks_one_way(self.pos_next, self.pos_next + vec):
            return False
        return (self.maze.is_valid_coord(self.pos_next + vec)
                and self._game.inst[2 * self.pos_next[1] + vec[1] + 1][2 * self.pos_next[0] + vec[0] + 1] == 2)

    def move(self, direction: Cell):
        # calculate the next position
        if self.disp_state & DispState.MOVING:
            return
        vec = DIR_VECS[direction]
        if direction != self._heading:
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + 7, {"sound": rotate_sound}))
            self._heading = direction
            self.disp_state |= DispState.ROTATING
        all_headings = [V(1, 0), V(0, -1), V(-1, 0), V(0, 1)]

        if self._is_available(vec):
            self.pos_next += vec
        else:
            return
        while (self._is_available(vec)
               and not self._is_available(all_headings[(all_headings.index(vec) + 1) % 4])
               and not self._is_available(all_headings[(all_headings.index(vec) + 3) % 4])
               and not self.pos_next == self.maze.end):
            # the condition: there is one available cell in the front, and there is no branch at the current cell
            # and the current cell is not the end of the maze
            self.pos_next += vec

        # initialize movement animation
        self.movement_intp = ReversedQuad(step=5 * abs(sum(self.pos_next - self.pos)))
        self.movement_vec = self.pos_to_surf(self.pos_next) - self.pos_to_surf(self.pos)
        self.disp_state |= DispState.MOVING

    def draw(self, surface):
        if self.disp_state & DispState.MOVING:
            if self.movement_intp.get() != 1:
                self.cur_anim.set_position(self.pos_to_surf() + self.movement_vec * self.movement_intp.get())
                self.movement_intp.update()
            else:
                self.disp_state ^= DispState.MOVING
                self.pos = self.pos_next
                self.movement_intp.set(0)
                self.movement_vec = V(0, 0)
        if self.disp_state & DispState.ROTATING:
            fid = self.cur_anim.get_frame_id()
            pos = self.cur_anim.get_position()
            self.cur_anim = self.anim_dict[self._heading]
            self.cur_anim.set_frame_id(fid)
            self.cur_anim.set_position(pos)
            self.disp_state ^= DispState.ROTATING
        if self.disp_state == DispState.IDLE:  # must be "==" !
            self.cur_anim.set_position(self.pos_to_surf())

        self.cur_anim.step()
        self.cur_anim.draw(surface, size=[self._game.cell_width * 1.2, self._game.cell_width * 1.2])

    def directly_draw(self, surface, pos, size=None):
        pos0 = self.cur_anim.get_position()
        self.cur_anim.set_position(pos)
        self.cur_anim.draw(surface, size=size if size else self.size)
        self.cur_anim.set_position(pos0)
        self.cur_anim.step()


class MazeGame(GameScreen):
    MAZE_EDGE_COLOR = (255, 255, 255)
    BG_COLORS = ((204, 128, 204), (108, 150, 200), (200, 175, 64), (100, 204, 100))
    limited_vision = False
    MAX_MAZE_WIDTH = 10
    MAX_MAZE_HEIGHT = 10
    SCORE_DICT = {
        GameMode.SINGLE: {"easy": 1, "normal": 2, "hard": 3},
        GameMode.DOUBLE: {
        }
    }

    def __init__(self, gamemode=GameMode.SINGLE,
                 size_preset="medium", difficulty="normal", players=None, start_edge=None, end_edge=None,
                 pause_cb=None, sound_switch_cb=None, resume_cb=None, menu_cb=None):
        """start edge and end edge: 0-3, 0 for top, clockwise
            :param pause_cb: called when the HUD pause button is hit, no arguments
            :param sound_switch_cb: called when the sound button is toggled, no arguments
            :param resume_cb: called when the pause screen RESUME button is hit, no arguments
            :param menu_cb: called when the pause screen MENU button is hit, no arguments
        """
        # common
        self._time_str = None
        self._versus_over = False
        self.gamemode = gamemode
        self.size_preset = size_preset
        self.difficulty = difficulty
        side_min, side_max = SIZE_PRESETS[size_preset]
        self.field_width = random.randint(side_min, side_max)
        self.field_height = random.randint(side_min, side_max)

        self.maze = Maze((self.field_width, self.field_height),
                         start_edge=start_edge,
                         end_edge=end_edge,
                         diff_preset=difficulty)
        self.inst = self.maze.draw_instructions()

        self.start_edge = self.maze.start_edge
        self.end_edge = self.maze.end_edge

        # display related
        self.maze_surf = pg.Surface(pg.display.get_window_size(), pg.SRCALPHA)
        self.bg_color = random.choice(self.BG_COLORS)
        self.region = V(0, 0)
        self.cell_width = 0
        self.maze_edge_width = 0
        self.timer = Timer()
        self._time_surf = None
        self.time_surface()
        self.timer_pos_x = 0

        # game logic related
        self.players = []
        if players is None:
            self.players.append(Player(self, pos0=self.maze.start))
            if gamemode == GameMode.DOUBLE:
                self.place_versus_players()
        else:
            self.players = players
        if gamemode == GameMode.SINGLE:
            self.players[0].pos = self.maze.start
            self.players[0].pos_next = self.maze.start

        elif gamemode == GameMode.DOUBLE:  # (two-player mode) predator on the entrance, prey at random
            self.place_versus_players()

        self.pause_cb = pause_cb
        self.sound_switch_cb = sound_switch_cb
        self.resume_cb = resume_cb
        self.menu_cb = menu_cb
        self.hud = HUD(pg.display.get_window_size(),
                       game_mode=gamemode,
                       pause_cb=pause_cb,
                       sound_switch_cb=sound_switch_cb,
                       fetch_scores_cb=self.fetch_scores)
        # (two-player mode) the versus HUD: the role tag under each label, then points and deaths
        if gamemode == GameMode.DOUBLE:
            self.hud = VersusHUD(pg.display.get_window_size(),
                                 game_mode=gamemode,
                                 pause_cb=pause_cb,
                                 sound_switch_cb=sound_switch_cb,
                                 fetch_scores_cb=self.fetch_scores)
            self.hud.fetch_roles_cb = self.fetch_roles
            self.hud.fetch_points_cb = self.fetch_points
        # (single player) the solo HUD drops the skull counter and shows the score as "pts N"
        if gamemode == GameMode.SINGLE:
            self.hud = SinglePlayerHUD(pg.display.get_window_size(),
                                       game_mode=gamemode,
                                       pause_cb=pause_cb,
                                       sound_switch_cb=sound_switch_cb,
                                       fetch_scores_cb=self.fetch_scores)
            self.hud.fetch_points_cb = self.fetch_points
        self.pause_screen = PauseScreen(pg.display.get_window_size(),
                                        resume_cb=resume_cb,
                                        menu_cb=menu_cb,
                                        sound_switch_cb=sound_switch_cb)
        self.resize(pg.display.get_window_size())

        game_start = pg.event.Event(pg.USEREVENT + 1,
                                    {'gamemode': gamemode,
                                     'size': (self.field_width, self.field_height),
                                     'difficulty': difficulty})
        pg.event.post(game_start)

    def fetch_scores(self):
        # HUD info source: per-player (eaten, eat) counts
        if not self.players:
            return [(0, 0)]
        return [(p.eaten, p.eat) for p in self.players]

    def fetch_roles(self):
        """(two-player mode) HUD info source: the role of each player, for the role tags."""
        names = {PlayerType.PREDATOR: "PREDATOR", PlayerType.PREY: "PREY"}
        return [names.get(p.player_type, "") for p in self.players]

    def draw_maze(self, surf=None):
        """draw the maze on "self.maze_surf" property."""
        surf = self.maze_surf if surf is None else surf
        surf.fill((0, 0, 0, 0))
        # self.inst = self.maze.draw_instructions()
        for row in range(self.field_height * 2 + 1):
            for col in range(self.field_width * 2 + 1):
                op = self.inst[row][col]
                if row % 2 == 0 and col % 2 == 1 and op == 0:
                    pg.draw.line(surf,
                                 self.MAZE_EDGE_COLOR,
                                 (int(self.region[0] + self.cell_width * (col // 2)),
                                  int(self.region[1] + self.cell_width * (row // 2))),
                                 (int(self.region[0] + self.cell_width * (col // 2) + self.cell_width),
                                  int(self.region[1] + self.cell_width * (row // 2))),
                                 width=self.maze_edge_width)
                elif row % 2 == 1 and col % 2 == 0 and op == 0:
                    pg.draw.line(surf,
                                 self.MAZE_EDGE_COLOR,
                                 (int(self.region[0] + self.cell_width * (col // 2)),
                                  int(self.region[1] + self.cell_width * (row // 2))),
                                 (int(self.region[0] + self.cell_width * (col // 2)),
                                  int(self.region[1] + self.cell_width * (row // 2) + self.cell_width)),
                                 width=self.maze_edge_width)

                # add round corners
                if self.maze_edge_width > 2:
                    # center coordinate plus (1, 1) to align the circles with the lines
                    # (ways line() and circle() calculate coordinate are different)
                    pg.draw.circle(surf,
                                   self.MAZE_EDGE_COLOR,
                                   (int(self.region[0] + self.cell_width * (col // 2) + 1),
                                    int(self.region[1] + self.cell_width * (row // 2)) + 1),
                                   int(self.maze_edge_width / 2))
        self.draw_one_way_doors(surf)
        Shadow(surf, (self.maze_edge_width // 2, self.maze_edge_width // 2))

    # (one-way doors) marker hyperparameters
    DOOR_COLOR = (255, 214, 120)  # amber, so a one-way passage stands out from the white walls
    DOOR_SIZE_RATIO = 0.42  # arrow length, as a fraction of the cell width

    def draw_one_way_doors(self, surf=None):
        """(one-way doors) draw an arrow in every one-way passage, pointing the only way it may be
        walked. Drawn together with the maze, so the arrows follow resizes on their own."""
        if not self.maze.one_way_doors:
            return
        surf = self.maze_surf if surf is None else surf
        for start, end in self.maze.one_way_doors:
            direction = V(end) - V(start)
            side = V(-direction[1], direction[0])
            mid = (cell_to_surf(self, start) + cell_to_surf(self, end)) * 0.5
            size = max(4, int(self.cell_width * self.DOOR_SIZE_RATIO))
            tip = mid + direction * size
            head = mid + direction * (size * 0.15)
            pg.draw.line(surf, self.DOOR_COLOR, mid - direction * size, head,
                         width=max(2, int(size * 0.34)))
            pg.draw.polygon(surf, self.DOOR_COLOR,
                            (tip, side * (size * 0.6) + head, -side * (size * 0.6) + head))

    @property
    def time(self):
        return self.timer.get()

    def start_timing(self):
        self.timer.start()

    def pause_timing(self):
        self.timer.pause()
        print("pause timing")

    def resume_timing(self):
        self.timer.resume()
        print("resume timing")

    def place_versus_players(self):
        """(two-player mode) apply the spawn rule of the versus mode: the predator starts on the
        entrance of the maze while the prey starts on a random cell; any movement left over from
        the previous maze is cancelled."""
        self._versus_over = False
        if len(self.players) < 2:
            return
        predator, prey = versus_pair(self.players)
        predator.pos = predator.pos_next = V(self.maze.start)
        predator.heading = VERSUS_ENTRANCE_HEADINGS.get(self.start_edge, Cell.GO_DOWN)
        prey.pos = prey.pos_next = pick_prey_spawn(self.maze, self.maze.start)
        for p in (predator, prey):
            p.disp_state = DispState.IDLE
            p.movement_vec = V(0, 0)

    def versus_score(self):
        """(two-player mode) what one round is worth, scored with the very rule of the single player
        mode and its base values (the versus table of SCORE_DICT is still empty). Only the player
        who won the round is paid: the predator for a catch, the prey for an escape."""
        return int(self.SCORE_DICT[GameMode.SINGLE][self.difficulty]
                   * self.field_width * self.field_height * self.maze.p_len
                   / self.timer.get())

    def game_logic(self):
        """The logic of the whole game, arranges all the sub logic and provides a handle for the main Game class"""
        if self.gamemode == GameMode.SINGLE:
            if self.players[0].pos == self.maze.end:
                score = int(self.SCORE_DICT[self.gamemode][self.difficulty]
                            * self.field_width
                            * self.field_height
                            * self.maze.p_len
                            / self.timer.get())
                self.players[0].score += score
                game_end = pg.event.Event(pg.USEREVENT + 2,
                                          {'gamemode': self.gamemode,
                                           'size': (self.field_width, self.field_height),
                                           'difficulty': self.difficulty})
                pg.event.post(game_end)
        elif self.gamemode == GameMode.DOUBLE:  # (two-player mode) the chase rules live below
            if self._versus_over or len(self.players) < 2:
                return
            predator, prey = versus_pair(self.players)
            if versus_touching(predator, prey):
                self._versus_over = True
                predator.score += self.versus_score()  # the catch pays the predator only
                pg.event.post(pg.event.Event(pg.USEREVENT + 8))  # the prey dies: the ghost transition
            elif prey.pos == self.maze.end:
                self._versus_over = True
                prey.score += self.versus_score()  # the escape pays the prey only
                game_end = pg.event.Event(pg.USEREVENT + 2,  # the prey escapes: the regular transition
                                          {'gamemode': self.gamemode,
                                           'size': (self.field_width, self.field_height),
                                           'difficulty': self.difficulty})
                pg.event.post(game_end)

    def resize(self, size):
        """update the screen size variables, call every time the screen size changes"""
        self.maze_surf = pg.Surface(size, pg.SRCALPHA)
        self.cell_width = min(size[0] / (self.field_width * 1.2), size[1] / (self.field_height * 1.2))
        self.maze_edge_width = max(int(self.cell_width // 6), 1)
        maze_size = (self.cell_width * self.field_width, self.cell_width * self.field_height)
        self.region = ((size[0] - maze_size[0]) / 2, (size[1] - maze_size[1]) / 2)
        self.timer_pos_x = (pygame.display.get_window_size()[0] - self._time_surf.get_size()[0] - 5) / 2
        self.draw_maze()
        # sync HUD / pause screen with the new size (they are created after the first resize)
        hud = getattr(self, 'hud', None)
        if hud is not None:
            hud.resize(size)
        pause_screen = getattr(self, 'pause_screen', None)
        if pause_screen is not None:
            pause_screen.resize(size)

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if self.gamemode == GameMode.DOUBLE and len(self.players) > 1:
                    # (two-player mode) player 2 walks with WASD while the arrows keep driving player 1
                    if event.key == pg.K_d:
                        self.players[1].move(Cell.GO_RIGHT)
                        events.remove(event)
                    elif event.key == pg.K_a:
                        self.players[1].move(Cell.GO_LEFT)
                        events.remove(event)
                    elif event.key == pg.K_w:
                        self.players[1].move(Cell.GO_UP)
                        events.remove(event)
                    elif event.key == pg.K_s:
                        self.players[1].move(Cell.GO_DOWN)
                        events.remove(event)
                if event.key == pg.K_RIGHT:
                    self.players[0].move(Cell.GO_RIGHT)
                    events.remove(event)
                elif event.key == pg.K_LEFT:
                    self.players[0].move(Cell.GO_LEFT)
                    events.remove(event)
                elif event.key == pg.K_UP:
                    self.players[0].move(Cell.GO_UP)
                    events.remove(event)
                elif event.key == pg.K_DOWN:
                    self.players[0].move(Cell.GO_DOWN)
                    events.remove(event)
                elif event.key == pg.USEREVENT + 6:
                    self.resume_timing()
        self.game_logic()
        return events

    # (limited vision) how far a player can see, in cells, when the menu switches the mode on
    VISION_RADIUS_CELLS = 3.5

    def draw_vision_fog(self, surface):
        """(limited vision) cover the maze with the background colour everywhere the players
        cannot see, so only the structure within their sight stays visible. The players themselves
        are drawn after this and stay on screen, and no fog is drawn at all in full vision."""
        if not self.limited_vision:
            return
        fog = pg.Surface(surface.get_size(), pg.SRCALPHA)
        fog.fill((*self.bg_color, 255))
        radius = max(1, int(self.cell_width * self.VISION_RADIUS_CELLS))
        for p in self.players:
            center = p.cur_anim.get_position()
            pg.draw.circle(fog, (0, 0, 0, 0), (int(center[0]), int(center[1])), radius)
        surface.blit(fog, (0, 0))

    def fetch_points(self):
        """(single player) HUD info source: the score of each player, shown as "pts N"."""
        return [p.score for p in self.players]

    # (timer) the elapsed time of the maze, centred between the two HUD panels
    TIME_FONT_SIZE = 46  # a bit larger than the HUD text, so the time reads at a glance
    TIME_COLOR = (255, 255, 255)
    TIME_SHADOW_COLOR = (0, 0, 0, 110)  # keeps the digits readable over the white walls
    TIME_SHADOW_OFFSET = (2, 3)

    def time_surface(self):
        """(timer) the elapsed time of this maze (utils.Timer) as a ready to blit surface with a
        soft shadow. The digits are only rendered again when the string changes, which also keeps
        the time standing still while the game is paused."""
        text = self.timer.get_str()
        cached = getattr(self, "_time_surf", None)
        if cached is None:
            font = make_font(self.TIME_FONT_SIZE)
            body = font.render(text, True, self.TIME_COLOR)
            offset = self.TIME_SHADOW_OFFSET
            surf = pg.Surface((body.get_width() + offset[0], body.get_height() + offset[1]),
                              pg.SRCALPHA)
            surf.blit(body, (0, 0))
            self._time_str = text
            self._time_surf = surf
            self.timer_pos_x = (pygame.display.get_window_size()[0] - self._time_surf.get_size()[0] - 5) / 2
            # DO NOT write the "Shadow..." statement outside the if-else clause, or unexpected bad thing will happen
            # the reason is not clear now, we may find out the other day
            Shadow(self._time_surf, self.TIME_SHADOW_OFFSET)
        elif text != getattr(self, "_time_str", None):
            self._time_surf.fill((0, 0, 0, 0), special_flags=pg.BLEND_RGBA_MULT)
            body = make_font(self.TIME_FONT_SIZE).render(text, True, self.TIME_COLOR)
            self._time_str = text
            self._time_surf.blit(body, (0, 0))
            Shadow(self._time_surf, self.TIME_SHADOW_OFFSET)
        return self._time_surf

    def timer_pos(self):
        """timer position: centred on the screen, on the row of the HUD panels"""
        timer = self._time_surf
        hud = getattr(self, "hud", None)
        label = getattr(hud, "_p1_label", None)
        if label is not None:
            row_y, row_h = hud.MARGIN, label.get_height()
        else:  # before the HUD exists: use the free strip above the maze
            row_y, row_h = 0, int(self.region[1])
        y = row_y + (row_h - timer.get_height()) // 2
        y = min(y, int(self.region[1]) - timer.get_height() - 2)
        return V(self.timer_pos_x, max(0, y))

    def draw_timer(self, surface):
        """(timer) blit the elapsed time of the maze"""
        timer = self.time_surface()
        pos = self.timer_pos()
        surface.blit(timer, (pos[0], pos[1]))

    def draw(self, surface, plot_only=False):
        surface.fill(self.bg_color)
        surface.blit(self.maze_surf, (0, 0))
        self.draw_vision_fog(surface)
        if not plot_only:
            for p in self.players:
                p.draw(surface)
        self.draw_timer(surface)


class GameGameTrans(GameScreen):
    PHASE_TIMES = (40, 40, 40)  # index 0 for phase 0, 1 for phase 3, 2 for phase 2
    STATS_COLOR = (255, 255, 255)
    STATS_LINE_GAP = 12  # vertical gap between the three stat lines
    STATS_ENTER_DURATION = 20  # frames for the fly-in entrance animation
    STATS_FLY_DISTANCE = 120  # pixels the stats travel during the fly-in
    STATS_PADDING = 40  # padding from screen edge when calc pos

    def __init__(self, old_game: MazeGame):
        """A fancy transition between two maze games."""
        super().__init__()

        # players
        self.maze1 = old_game
        self.players: list[Player] = old_game.players
        if old_game.gamemode == GameMode.SINGLE:
            self.prey = self.players[0]
            self.predator = None
        else:
            self.predator, self.prey = versus_pair(self.players)

        self.end_edge = self.maze1.end_edge

        # player heading
        if self.end_edge == 2:
            self.prey.heading = Cell.GO_DOWN
            self.start_edge = 0
        elif self.end_edge == 0:
            self.prey.heading = Cell.GO_UP
            self.start_edge = 2
        elif self.end_edge == 1:
            self.prey.heading = Cell.GO_RIGHT
            self.start_edge = 3
        elif self.end_edge == 3:
            self.prey.heading = Cell.GO_LEFT
            self.start_edge = 1

        if self.predator:
            self.predator.heading = self.prey.heading

        self.maze2 = self.next_game = MazeGame(gamemode=self.maze1.gamemode,
                                               size_preset=self.maze1.size_preset,
                                               difficulty=self.maze1.difficulty,
                                               players=self.maze1.players,
                                               start_edge=self.start_edge,
                                               pause_cb=self.maze1.pause_cb,
                                               sound_switch_cb=self.maze1.sound_switch_cb,
                                               resume_cb=self.maze1.resume_cb,
                                               menu_cb=self.maze1.menu_cb)

        # basic surf
        self.surface0 = pg.Surface(pg.display.get_window_size(), pg.SRCALPHA)
        self.surface1 = pg.Surface(pg.display.get_window_size(), pg.SRCALPHA)
        self.surface2 = pg.Surface(pg.display.get_window_size(), pg.SRCALPHA)
        old_game.draw(self.surface1, plot_only=True)
        self.path_surf = self.surface0.copy().convert(self.surface0)

        # animation related
        self.surface0.fill(self.maze1.bg_color)
        self.life = 0
        self._ani_p = 0  # 0 for fading the old, 1 for options, 2 for introducing the new
        self.pre_p3 = 0
        self._blit_pos = 0, 0
        self._start_color = self.maze1.bg_color
        self._end_color = self.maze2.bg_color

        self.p0 = []
        self.p1 = []
        self.p2 = []
        self._calc_points()

        self.color_anim = ChangeColor(
            self.surface0,
            start_color=self._start_color,
            end_color=self._end_color,
            duration=self.PHASE_TIMES[2],
            interpolation=Linear
        )
        end = self.maze1.maze.end
        self.p0_fade = RoundMaskFade(self.surface1,
                                     self.PHASE_TIMES[0] // 2,
                                     V(int(self.maze1.region[0] + self.maze1.cell_width * (end[0] + 0.5) + 1),
                                       int(self.maze1.region[1] + self.maze1.cell_width * (end[1] + 0.5)) + 1),
                                     Quad)

        self.direction = [V(0, -1), V(1, 0), V(0, 1), V(-1, 0)][self.end_edge]
        self.p0_fade.animate_now(initial_phase=1, direction=-1)
        self.p2_fade = None

        # path animation
        self.intp0 = Quad(self.PHASE_TIMES[0] * 3 // 4)
        self.intp1 = DoubleQuad(self.PHASE_TIMES[2])
        self.intp2 = Quad(self.PHASE_TIMES[1] // 2, initial_phase=1, direction=-1)
        self.chase_intp = Quad(self.PHASE_TIMES[2] // 2, initial_phase=1, direction=-1)
        self.escape_intp = Quad(self.PHASE_TIMES[2] // 2)

        self.offset = V(0, 0)
        self.line_width = self.maze1.maze_edge_width
        self.line_width0 = self.line_width
        self.line_width2 = self.maze2.maze_edge_width
        self.p_size0 = self.maze1.cell_width * 1.2
        self.p_size1 = self.maze2.cell_width * 1.2
        self.max_offset = max(*pg.display.get_window_size())
        self.line_length = sum(pg.display.get_window_size())

        # stats text animation state (built lazily on the first stats frame)
        self._stats_surf = None  # pre-rendered surface holding the three text lines
        self._stats_pos = V(0, 0)  # final blit position of the stats block
        self._stats_enter = None  # fly-in interpolation
        self._stats_fade = None  # Fade effect started when pre_p3 flips to 1

    def resize(self, size):
        self.maze1.resize(size)
        self.maze2.resize(size)
        self.surface0 = pg.Surface(pg.display.get_window_size(), pg.SRCALPHA)
        self.surface1 = self.maze1.maze_surf.copy()
        self.surface2 = self.maze2.maze_surf.copy()

        if self._ani_p < 2:
            self._ani_p = 2
            self.life = 0
            for p in self.players:
                p.game = self.maze2

    def _calc_points(self):
        for maze, end in ((self.maze1, self.maze1.maze.end), (self.maze2, self.maze2.maze.start)):
            if end[0] == maze.maze.width - 1:
                p1 = end[0] + 1, end[1]
                p2 = end[0] + 1, end[1] + 1
            elif end[1] == maze.maze.height - 1:
                p1 = end[0], end[1] + 1
                p2 = end[0] + 1, end[1] + 1
            elif end[0] == 0:
                p1 = end[0], end[1]
                p2 = end[0], end[1] + 1
            elif end[1] == 0:
                p1 = end[0], end[1]
                p2 = end[0] + 1, end[1]
            else:
                raise ValueError("maze object has invalid end point")
            self.p0.append(V(int(maze.region[0] + maze.cell_width * end[0]) + maze.cell_width // 2,
                             int(maze.region[1] + maze.cell_width * end[1]) + maze.cell_width // 2))
            self.p1.append(V(int(maze.region[0] + maze.cell_width * p1[0]),
                             int(maze.region[1] + maze.cell_width * p1[1])))
            self.p2.append(V(int(maze.region[0] + maze.cell_width * p2[0]),
                             int(maze.region[1] + maze.cell_width * p2[1])))

    def _draw_path_0(self):
        self.path_surf.fill((0, 0, 0, 0), special_flags=pg.BLEND_RGBA_MULT)
        pg.draw.line(
            self.path_surf,
            MazeGame.MAZE_EDGE_COLOR,
            self.p1[0] + self.offset,
            self.p1[0] + self.offset + self.direction * self.line_length * self.intp0.get(),
            self.line_width
        )
        pg.draw.line(
            self.path_surf,
            MazeGame.MAZE_EDGE_COLOR,
            self.p2[0] + self.offset,
            self.p2[0] + self.offset + self.direction * self.line_length * self.intp0.get(),
            self.line_width
        )
        w = self.maze1.maze_edge_width // 2
        Shadow(self.path_surf, (w, w))

    def _draw_path_1(self):
        self.path_surf = pg.Surface(self.surface0.get_size(), pg.SRCALPHA).convert_alpha(self.surface0)
        # noinspection DuplicatedCode
        p1 = self.p1[0] + (self.p1[1] - self.p1[0]) * self.intp1.get()
        p2 = self.p2[0] + (self.p2[1] - self.p2[0]) * self.intp1.get()
        w, h = pg.display.get_window_size()
        if self.end_edge == 0:
            p1 = V(p1[0], 0)
            p2 = V(p2[0], 0)
        elif self.end_edge == 1:
            p1 = V(w, p1[1])
            p2 = V(w, p2[1])
        elif self.end_edge == 2:
            p1 = V(p1[0], h)
            p2 = V(p2[0], h)
        elif self.end_edge == 3:
            p1 = V(0, p1[1])
            p2 = V(0, p2[1])
        else:
            raise ValueError("end_edge must be 0, 1, 2, or 3")

        pg.draw.line(self.path_surf, MazeGame.MAZE_EDGE_COLOR, p1, p1 - self.direction * self.line_length,
                     self.line_width)
        pg.draw.line(self.path_surf, MazeGame.MAZE_EDGE_COLOR, p2, p2 - self.direction * self.line_length,
                     self.line_width)
        w = self.line_width // 2
        Shadow(self.path_surf, (w, w))

    def _draw_path_2(self):
        self.path_surf.fill((0, 0, 0, 0), special_flags=pg.BLEND_RGBA_MULT)
        pg.draw.line(
            self.path_surf,
            MazeGame.MAZE_EDGE_COLOR,
            self.p1[1] + self.offset,
            self.p1[1] + self.offset - self.direction * self.line_length * self.intp2.get(),
            self.line_width
        )
        pg.draw.line(
            self.path_surf,
            MazeGame.MAZE_EDGE_COLOR,
            self.p2[1] + self.offset,
            self.p2[1] + self.offset - self.direction * self.line_length * self.intp2.get(),
            self.line_width
        )
        w = self.maze2.maze_edge_width // 2
        Shadow(self.path_surf, (w, w))

    def handle_events(self, events: list[pg.event.Event]) -> list[pg.event.Event]:
        if self._ani_p == 0 and self.life == self.PHASE_TIMES[0]:  # enter phase 1
            self.life = 0
            self._ani_p += 1
            self.surface0.fill(self._start_color)
        elif self._ani_p == 2 and self.life == self.PHASE_TIMES[1]:  # enter the next game
            end = pg.event.Event(pg.USEREVENT + 3,
                                 {'new_game': self.maze2})
            pg.event.post(end)
        elif self._ani_p == 1:
            for event in events:
                if event.type == pg.KEYDOWN or event.type == pg.MOUSEBUTTONDOWN:
                    if not self.pre_p3 and self.life > 30:
                        pygame.event.post(pygame.event.Event(pygame.USEREVENT + 7, {"sound": rotate_sound}))
                        self.color_anim.animate_now()
                        # fade the stats out together with the background color change
                        if self._stats_surf is not None and self._stats_fade is None:
                            # snap an unfinished entrance to its final, fully opaque state
                            self._stats_enter = None
                            self._stats_surf.set_alpha(255)
                            self._stats_fade = Fade(self._stats_surf,
                                                    duration=self.PHASE_TIMES[2],
                                                    interpolation=Linear)
                            self._stats_fade.animate_now(initial_phase=1, direction=-1)
                        self.pre_p3 = 1
                        self.life = 0
            if self.pre_p3 and self.life == self.PHASE_TIMES[2]:  # enter phase 2
                self.life = 0
                self._ani_p += 1
                for p in self.players:
                    p.game = self.maze2
                self.next_game.draw(self.surface2, plot_only=True)
                self.p2_fade = RoundMaskFade(self.surface2, self.PHASE_TIMES[1] // 2, self.p0[1], Quad)
                self.p2_fade.animate_now()
                self.offset = V(int(self.intp2.get() * self.max_offset * self.direction[0]),
                                int(self.intp2.get() * self.max_offset * self.direction[1]))

        self.life += 1
        return events

    def draw(self, surface: pg.Surface) -> None:

        # phase 0: old game fades, player goes into a straight path
        if self._ani_p == 0:
            self.surface0.fill(self._start_color)
            self._draw_path_0()
            self.surface0.blit(self.path_surf, (0, 0))
            self.surface0.blit(self.surface1, self.offset)
            self.prey.directly_draw(self.surface0, self.p0[0], (self.p_size0,) * 2)
            if self.life >= self.PHASE_TIMES[0] // 4:
                self.intp0.update()
                self.offset = V(int(-self.intp0.get() * self.max_offset * self.direction[0]),
                                int(-self.intp0.get() * self.max_offset * self.direction[1]))
            surface.blit(self.surface0, (0, 0))

        # phase 1: the path becomes longer and throughout the screen, the score shown and game paused
        #          if oud game is a double-player game and prey escapes,
        #          prey goes out of the screen and predator shown in this phase
        elif self._ani_p == 1:
            surface.blit(self.surface0, (0, 0))
            if self.pre_p3:
                self.line_width = int(self.line_width0 + (self.line_width2 - self.line_width0) * self.intp1.get())
                p_size = int(self.p_size0 + (self.p_size1 - self.p_size0) * self.intp1.get())
                p_size = (p_size, p_size)
                p = self.p0[0] + (self.p0[1] - self.p0[0]) * self.intp1.get()
                self._draw_path_1()
                surface.blit(self.path_surf, (0, 0))
                self._draw_stats(surface)  # stats fading out via the Fade effect
                if self.next_game.gamemode == GameMode.DOUBLE:
                    self.predator.directly_draw(surface,
                                                p - self.direction * (self.chase_intp.get() * self.line_length), p_size)
                    self.prey.directly_draw(surface,
                                            p + self.direction * (self.escape_intp.get() * self.line_length * 2),
                                            p_size)
                else:
                    self.prey.directly_draw(surface, p, p_size)
                self.intp1.update()
                self.escape_intp.update()
                if self.life >= self.PHASE_TIMES[2] // 2:
                    self.chase_intp.update()
            else:
                surface.blit(self.surface0, (0, 0))
                surface.blit(self.path_surf, (0, 0))
                self.prey.directly_draw(surface, self.p0[0])
                self._draw_stats(surface)

        # phase 2: straight path disappears and new game shown
        elif self._ani_p == 2:
            self.surface0.fill(self._end_color)
            self._draw_path_2()
            self.surface0.blit(self.path_surf, (0, 0))
            if self.life == self.PHASE_TIMES[1] // 3:
                self.p2_fade.animate_now()
            if self.life > self.PHASE_TIMES[1] // 3:
                self.surface0.blit(self.surface2, self.offset)

            if self.next_game.gamemode == GameMode.DOUBLE:
                self.predator.directly_draw(self.surface0, self.p0[1])
            else:
                self.prey.directly_draw(self.surface0, self.p0[1])

            self.intp2.update()
            self.offset = V(int(self.intp2.get() * self.max_offset * self.direction[0]),
                            int(self.intp2.get() * self.max_offset * self.direction[1]))

            surface.blit(self.surface0, (0, 0))

    def _build_stats(self):
        """Pre-render the three stat lines onto self._stats_surf and compute the final
        blit position; called once on the first stats frame."""
        time_str = self.maze1.timer.get_str()
        score_str = f"Total score: {self.prey.score}"
        prompt_str = "exit: <Backspace>  continue: <other>"
        prop_font_size = sum(pygame.display.get_window_size()) // 100
        total_w = make_font(prop_font_size).size(prompt_str)
        sc_size = prop_font_size
        tm_size = prop_font_size
        while make_font(sc_size).size(score_str) < total_w:
            sc_size += 1
        while make_font(tm_size).size(time_str) < total_w:
            tm_size += 1
        fonts = [make_font(tm_size), make_font(sc_size), make_font(prop_font_size)]

        lines = [time_str, score_str, prompt_str]

        # render each line, then use the widest surface width as target_w
        rendered = [f.render(s, True, self.STATS_COLOR) for f, s in zip(fonts, lines)]
        widths = [r.get_width() for r in rendered]
        target_w = max(widths)
        heights = [r.get_height() for r in rendered]
        total_h = sum(heights) + self.STATS_LINE_GAP * (len(lines) - 1)

        # blit the three lines, each centered within target_w, onto one transparent surface
        stats_surf = pg.Surface((target_w + 3, total_h + 3), pg.SRCALPHA)
        y_cursor = 0
        for i, r in enumerate(rendered):
            stats_surf.blit(r, ((target_w - r.get_width()) // 2, y_cursor))
            y_cursor += heights[i] + self.STATS_LINE_GAP
        self._stats_surf = stats_surf

        # compute the three spaces formed by the two parallel lines
        sw, sh = pg.display.get_window_size()
        # noinspection DuplicatedCode
        a1 = self.p1[0] + (self.p1[1] - self.p1[0]) * self.intp1.get()
        a2 = self.p2[0] + (self.p2[1] - self.p2[0]) * self.intp1.get()
        if self.end_edge == 0:
            a1, a2 = V(a1[0], 0), V(a2[0], 0)
        elif self.end_edge == 1:
            a1, a2 = V(sw, a1[1]), V(sw, a2[1])
        elif self.end_edge == 2:
            a1, a2 = V(a1[0], sh), V(a2[0], sh)
        elif self.end_edge == 3:
            a1, a2 = V(0, a1[1]), V(0, a2[1])

        if self.end_edge in (0, 2):  # vertical lines -> split by x
            x1, x2 = sorted([int(a1[0]), int(a2[0])])
            spaces = [(0, 0, x1, sh), (x1, 0, x2 - x1, sh), (x2, 0, sw - x2, sh)]
        else:  # horizontal lines -> split by y
            y1, y2 = sorted([int(a1[1]), int(a2[1])])
            spaces = [(0, 0, sw, y1), (0, y1, sw, y2 - y1), (0, y2, sw, sh - y2)]

        bx, by, bw, bh = max(spaces, key=lambda s: s[2] * s[3])

        # align with player along the free axis, then clamp into the space
        player_x, player_y = int(self.p0[0][0]), int(self.p0[0][1])
        if self.end_edge in (1, 3):  # horizontal lines -> align x with player
            top_x = player_x - target_w // 2
            top_y = by + (bh - total_h) // 2
        else:  # vertical lines -> align y with player
            top_x = bx + (bw - target_w) // 2
            top_y = player_y - total_h // 2

        # clamp so the text block stays within the largest space and on-screen
        top_x = max(bx, min(top_x, bx + bw - target_w))
        top_y = max(by, min(top_y, by + bh - total_h))
        top_x = max(self.STATS_PADDING, min(top_x, sw - target_w - self.STATS_PADDING))
        top_y = max(self.STATS_PADDING, min(top_y, sh - total_h - self.STATS_PADDING))
        self._stats_pos = V(int(top_x), int(top_y))

        # start the fly-in interpolation
        self._stats_enter = ReversedQuad(self.STATS_ENTER_DURATION)
        Shadow(self._stats_surf, (3, 3))

    def _draw_stats(self, surface):
        """Blit the stats block; handles the fly-in entrance and hands opacity over to
        the Fade effect once pre_p3 flips to 1."""
        if self._stats_surf is None:
            self._build_stats()

        # entrance: fly in from the opposite side of the player's facing and fade in
        fly = V(0, 0)
        if self._stats_enter is not None and self._stats_fade is None:
            self._stats_enter.update()
            p = self._stats_enter.get()
            if p >= 1.0:
                self._stats_enter = None
                p = 1.0
            fly = V(int(-self.direction[0] * self.STATS_FLY_DISTANCE * (1 - p)),
                    int(-self.direction[1] * self.STATS_FLY_DISTANCE * (1 - p)))
            self._stats_surf.set_alpha(int(p * 255))
        elif self._stats_fade is None:
            self._stats_surf.set_alpha(255)
        # while self._stats_fade is active it owns the surface's per-pixel opacity

        surface.blit(self._stats_surf,
                     (self._stats_pos[0] + fly[0], self._stats_pos[1] + fly[1]))

    def get_new_game(self):
        return self.maze2


class BlackScreenTrans(GameScreen):
    HALF_DURATION = 20

    def __init__(self, old_screen, color=(0, 0, 0), _manu=None, **game_preset):
        self.phase = 0
        self.fid = 0
        self.surf = pygame.Surface(pygame.display.get_window_size(), pygame.SRCALPHA)
        self.surf.fill(color)
        self.anim = RoundMaskFade(self.surf, duration=self.HALF_DURATION, interpolation=Quad, invert=True)
        self.anim.animate_now(initial_phase=1, direction=-1)
        self.old_screen = old_screen
        if _manu:
            _manu.resize(pygame.display.get_window_size())
        if isinstance(old_screen, WelcomeScreen):
            self.new_sc = MazeGame(**game_preset)
            try:
                for p in game_preset["players"]:
                    p.game = self.new_sc
            except KeyError:
                pass
        else:
            self.new_sc = _manu

    def resize(self, size: tuple[int, int] | V) -> None:
        ph, di = self.anim.phase, self.anim.direction
        self.old_screen.resize(size)
        self.new_sc.resize(size)
        self.surf = pygame.Surface(pygame.display.get_window_size())
        self.anim = RoundMaskFade(self.surf, duration=self.HALF_DURATION - self.fid, interpolation=Quad, invert=True)
        self.anim.animate_now(initial_phase=ph, direction=di)

    def handle_events(self, events: list[pg.event.Event]) -> list[pg.event.Event]:
        if self.phase == 1 and self.fid == self.HALF_DURATION:
            if type(self.old_screen) is WelcomeScreen:
                event = pygame.event.Event(pygame.USEREVENT + 4)
                pygame.event.post(event)
            else:
                event = pygame.event.Event(pg.USEREVENT + 5)
                pygame.event.post(event)
        return events

    def draw(self, surface: pg.Surface) -> None:
        if self.phase == 0 and self.fid == self.HALF_DURATION:
            self.phase = 1
            self.fid = 0
            self.anim = RoundMaskFade(self.surf, duration=self.HALF_DURATION - self.fid, invert=True)
            self.anim.animate_now()
        if self.phase == 0:
            self.old_screen.draw(surface)
        else:
            self.new_sc.draw(surface)
        surface.blit(self.surf, (0, 0))
        self.fid += 1

    def get_new_screen(self):
        return self.new_sc


# ---------------------------------------------------------------------------
# (limited vision) the sight mode the menu switches on, and (single player) the solo HUD
# ---------------------------------------------------------------------------

VISION_PRESETS = ["full", "limited"]  # the options of the VISION row of the menu


class SinglePlayerHUD(HUD):
    """(single player) the solo HUD: the skull counter is dropped and the score of the player is
    drawn as "pts N" right after the P1 label instead."""

    PTS_FONT_SIZE = 24
    PTS_COLOR = (255, 255, 255)
    PTS_GAP = 12  # gap between the label and the "pts N" line

    def _points_text(self, index):
        """(single player) the rendered "pts N" line of one player"""
        return make_font(self.PTS_FONT_SIZE).render(f"pts {self._points(index)}", True, self.PTS_COLOR)

    def _draw_player_row(self, surface, x, y, label, scores, label_on_right=False):
        """(single player) the solo mode keeps the label only, so the counters of the versus mode
        (the skull among them) are left out, and the score follows the label instead."""
        if self.game_mode != GameMode.SINGLE:
            return super()._draw_player_row(surface, x, y, label, scores, label_on_right)
        super()._draw_player_row(surface, x, y, label, [], label_on_right)
        text = self._points_text(0)
        surface.blit(text, (x + label.get_width() + self.PTS_GAP,
                            y + (label.get_height() - text.get_height()) // 2))


class VersusHUD(HUD):
    """(two-player mode) the versus HUD. Under each P1 / P2 label sits the role tag of that player
    and then two rows: the points on top and the death count below. The eat counter of the old
    layout is gone, because a round only ever pays the one player who won it."""

    # layout hyperparameters
    TAG_FONT_RATIO = 0.42  # tag text height, as a fraction of the player label height
    TAG_PAD_X = 14  # horizontal padding inside a tag
    TAG_PAD_Y = 6  # vertical padding inside a tag
    ROW_FONT_SIZE = 24  # points / death rows, kept smaller than the timer
    ROW_GAP = 6  # gap between the label, the tag and the two rows
    ROW_ICON_GAP = 6  # gap between the skull and its count
    ROW_COLOR = (255, 255, 255)

    def _row_text(self, text):
        """one line of the stacked block: white text with a soft shadow"""
        font = make_font(self.ROW_FONT_SIZE)
        body = font.render(text, True, self.ROW_COLOR)
        shadow = font.render(text, True, MazeGame.TIME_SHADOW_COLOR)
        offset = MazeGame.TIME_SHADOW_OFFSET
        surf = pg.Surface((body.get_width() + offset[0], body.get_height() + offset[1]), pg.SRCALPHA)
        surf.blit(shadow, offset)
        surf.blit(body, (0, 0))
        return surf

    def _tag_surface(self, role, label_h):
        """the role pill of one player. The text is rendered plain: pygame's synthetic bold is what
        smeared the letters of the first version, so the size alone carries the emphasis now."""
        text = make_font(int(label_h * self.TAG_FONT_RATIO)).render(role, True, palette[-1])
        w = text.get_width() + self.TAG_PAD_X * 2
        h = text.get_height() + self.TAG_PAD_Y * 2
        tag = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(tag, main_color, tag.get_rect(), border_radius=h // 2)
        tag.blit(text, ((w - text.get_width()) // 2, (h - text.get_height()) // 2))
        return tag

    def _deaths_surface(self, index):
        """the death row of one player: the skull and count of deaths"""
        scores = self._fetch_scores()
        count = scores[index][0] if index < len(scores) else 0
        icon = self._kill_icon
        text = make_font(self.ROW_FONT_SIZE).render(f"x {count}", True, self.ROW_COLOR)
        w = icon.get_width() + self.ROW_ICON_GAP + text.get_width()
        h = max(icon.get_height(), text.get_height())
        surf = pg.Surface((w, h), pg.SRCALPHA)
        surf.blit(icon, (0, (h - icon.get_height()) // 2))
        surf.blit(text, (icon.get_width() + self.ROW_ICON_GAP, (h - text.get_height()) // 2))
        return surf

    def _row_positions(self, index):
        """(two-player mode) the role tag and the two data rows of one player as (surface, x, y),
        top to bottom and mirrored to the right hand side for P2. The drawing below and the tests
        share this layout."""
        width = self.size[0]
        label = self._p2_label if index else self._p1_label
        on_right = index == 1
        left = width - self.MARGIN - label.get_width() if on_right else self.MARGIN
        right = width - self.MARGIN
        surfaces = []
        role = self._role_label(index)
        if role:
            surfaces.append(self._tag_surface(role, label.get_height()))
        surfaces.append(self._row_text(f"pts {self._points(index)}"))
        surfaces.append(self._deaths_surface(index))
        rows, cursor = [], self.MARGIN + label.get_height() + self.ROW_GAP
        for surf in surfaces:
            rows.append((surf, right - surf.get_width() if on_right else left, cursor))
            cursor += surf.get_height() + self.ROW_GAP
        return rows

    def _draw_player_row(self, surface, x, y, label, scores, label_on_right=False):
        """(two-player mode) the counters handed in by the base class are ignored: this draws the
        label with the role tag and the points / deaths rows below it, mirrored for P2."""
        if self.game_mode != GameMode.DOUBLE:
            return super()._draw_player_row(surface, x, y, label, scores, label_on_right)
        index = 1 if label_on_right else 0
        label_x = (surface.get_width() - self.MARGIN - label.get_width()) if label_on_right else self.MARGIN
        surface.blit(label, (label_x, y))
        for row, row_x, row_y in self._row_positions(index):
            surface.blit(row, (row_x, row_y))


# ---------------------------------------------------------------------------
# (two-player score) the result of a match that is left through the menu
# ---------------------------------------------------------------------------

class RecordsScreen(GameScreen):
    """(history) the games played so far: the newest solo runs with their time and score, and the
    settled versus matches with their winner. Any key returns to the menu, and CLEAR forgets every
    record, on disk as well."""

    TITLE = "RECORDS"
    HEADER = f"{'when':<16}   {'mode':<6}   result"
    TITLE_SIZE = 52
    ROW_SIZE = 23
    HINT_SIZE = 21
    LINE_GAP = 12
    PAD = 34
    PANEL_RADIUS = 28
    WIDTH_RATIO = 0.84  # the panel is at least that wide, so a short list still fills the screen
    HEIGHT_RATIO = 0.92  # ... and never taller than that: the list is cut to the rows that fit
    PANEL_COLOR = (0, 0, 0, 195)  # the menu gradient is light, so the list gets a dark panel
    ROW_BAND_COLOR = (255, 255, 255, 26)  # a faint band on every other row, to keep it readable
    TEXT_COLOR = (255, 255, 255)
    DIM_COLOR = (208, 224, 218)
    EMPTY_TEXT = "no games yet - go and play one"
    HINT_TEXT = "press any key to return"
    CLEAR_SIZE = (132, 46)
    FOOTER_GAP = 24  # room between the hint and the clear button of the footer row
    INPUT_LOCK = 15  # frames of ignored keys, so the key that opened this screen cannot close it

    def __init__(self, records, back_cb=None):
        self.records = records
        self.back_cb = back_cb
        self.size = pg.display.get_window_size()
        self.life = 0
        self.pos = (0, 0)
        self.clear_btn = Button("CLEAR RECORDS", style="solid", callback=self.clear)
        self._bg = None
        self._panel = None
        self.resize(self.size)

    def clear(self):
        """(history) forget every record, on disk as well"""
        self.records.clear()
        self._build()

    def resize(self, size: tuple[int, int] | V) -> None:
        self.size = tuple(size)
        # the same gradient the menu uses, so that the two screens look like one another
        self._bg = vertical_gradient(
            self.size,
            adjust_color(palette[-3], hue_offset=5, saturation_factor=0.8),
            adjust_color(palette[-3], hue_offset=-5, saturation_factor=0.8, brightness_factor=0.95))
        self._build()

    def _rows_that_fit(self, fixed_height, pitch, wanted):
        """how many rows the panel can show: the wanted number, or as many as fit on this screen"""
        room = int(self.size[1] * self.HEIGHT_RATIO) - fixed_height
        return max(1, min(wanted, room // max(1, pitch)))

    def _build(self):
        """lay the title, the table and the footer out in one panel"""
        rec_title = make_font(self.TITLE_SIZE).render(self.TITLE, True, self.TEXT_COLOR)
        best = self.records.best_single()
        head = [make_font(self.ROW_SIZE).render(f"best solo score: pts {best}", True,
                                                self.DIM_COLOR)] if best is not None else []
        hint = make_font(self.HINT_SIZE).render(self.HINT_TEXT, True, self.DIM_COLOR)
        columns = make_font(self.ROW_SIZE).render(self.HEADER, True, self.DIM_COLOR)
        btn_w, btn_h = self.CLEAR_SIZE
        footer_h = max(hint.get_height(), btn_h)

        wanted = self.records.shown()
        sample = make_font(self.ROW_SIZE).render(self.records.row_text(wanted[0]), True,
                                                 self.TEXT_COLOR) if wanted else make_font(self.ROW_SIZE).render(
            self.EMPTY_TEXT, True, self.DIM_COLOR)
        pitch = sample.get_height() + self.LINE_GAP
        fixed = (self.PAD * 2 + rec_title.get_height() + self.LINE_GAP * 2 + columns.get_height()
                 + self.LINE_GAP + sum(line.get_height() + self.LINE_GAP for line in head) + footer_h)
        shown = wanted[:self._rows_that_fit(fixed, pitch, len(wanted) or 1)]
        if shown:
            rows = [make_font(self.ROW_SIZE).render(self.records.row_text(entry), True, self.TEXT_COLOR)
                    for entry in shown]
        else:
            rows = [make_font(self.ROW_SIZE).render(self.EMPTY_TEXT, True, self.DIM_COLOR)]
            columns = None

        table_w = max([row.get_width() for row in rows]
                      + ([columns.get_width()] if columns is not None else []))
        content_w = max([rec_title.get_width(), table_w, hint.get_width() + self.FOOTER_GAP + btn_w]
                        + [line.get_width() for line in head])
        width = max(content_w + self.PAD * 2, int(self.size[0] * self.WIDTH_RATIO))
        body_h = sum(row.get_height() + self.LINE_GAP for row in rows)
        body_h += sum(line.get_height() + self.LINE_GAP for line in head)
        if columns is not None:
            body_h += columns.get_height() + self.LINE_GAP
        height = self.PAD * 2 + rec_title.get_height() + self.LINE_GAP * 2 + body_h + footer_h

        self._panel = pg.Surface((width, height), pg.SRCALPHA)
        pg.draw.rect(self._panel, self.PANEL_COLOR, self._panel.get_rect(),
                     border_radius=self.PANEL_RADIUS)

        y = self.PAD
        self._panel.blit(rec_title, ((width - rec_title.get_width()) // 2, y))
        y += rec_title.get_height() + self.LINE_GAP * 2
        for line in head:
            self._panel.blit(line, ((width - line.get_width()) // 2, y))
            y += line.get_height() + self.LINE_GAP
        # the table is one block, left aligned inside the panel, so that its columns line up
        left = max(self.PAD, (width - table_w) // 2)
        if columns is not None:
            self._panel.blit(columns, (left, y))
            y += columns.get_height() + self.LINE_GAP
        for index, row in enumerate(rows):
            if index % 2 and columns is not None:
                band = pg.Rect(self.PAD, y - 3, width - self.PAD * 2, row.get_height() + 6)
                pg.draw.rect(self._panel, self.ROW_BAND_COLOR, band, border_radius=9)
            self._panel.blit(row, (left, y))
            y += row.get_height() + self.LINE_GAP

        # the footer row: the hint in the middle, the clear button on the right hand side
        self._body_bottom = y  # where the table ended: the footer and its button come after it
        footer_y = height - self.PAD - footer_h
        self._panel.blit(hint, ((width - hint.get_width()) // 2,
                                footer_y + (footer_h - hint.get_height()) // 2))
        self.pos = ((self.size[0] - width) // 2, (self.size[1] - height) // 2)
        self.clear_btn.set_rect((self.pos[0] + width - self.PAD - btn_w,
                                 self.pos[1] + footer_y + (footer_h - btn_h) // 2, btn_w, btn_h))

    def handle_events(self, events: list[pg.event.Event]) -> list[pg.event.Event]:
        # the clear button first, everything else goes back to the menu
        for event in events:
            if self.clear_btn.handle_event(event):
                events.remove(event)
                continue
            if self.life >= self.INPUT_LOCK and event.type == pg.KEYDOWN:
                if self.back_cb is not None:
                    self.back_cb()
                break
        return events

    def draw(self, surface: pg.Surface) -> None:
        self.life += 1
        surface.blit(self._bg, (0, 0))
        self._panel.set_alpha(min(255, int(self.life / self.INPUT_LOCK * 255)))
        surface.blit(self._panel, self.pos)
        self.clear_btn.draw(surface)


class VersusResult(GameScreen):
    """(two-player score) shown when a versus match is left through the menu: the two scores and
    the winner, the one with the higher score. Any key goes on to the menu."""

    TITLE_SIZE = 64
    LINE_SIZE = 28
    PROMPT_SIZE = 24
    LINE_GAP = 18
    PANEL_COLOR = (0, 0, 0, 175)  # the maze backgrounds are light, so the text gets a dark panel
    PANEL_PAD = 46
    PANEL_RADIUS = 28
    INPUT_LOCK = 20  # frames of ignored keys, so the key that opened this screen cannot skip it

    def __init__(self, old_game, menu_screen):
        old_game.versus_settled = True  # the match is settled, the menu must not show this twice
        self.menu_screen = menu_screen
        self.bg = old_game.bg_color
        self.players = old_game.players
        self.scores = [p.score for p in old_game.players]
        self.deaths = [p.eaten for p in old_game.players]
        self.life = 0
        self.size = pg.display.get_window_size()
        self._build()

    def winner_text(self):
        """who won the match: the higher score, or nobody when the two are level"""
        if len(self.scores) < 2:
            return "MATCH OVER"
        if self.scores[0] == self.scores[1]:
            return "DRAW"
        return "P1 WINS" if self.scores[0] > self.scores[1] else "P2 WINS"

    def _build(self):
        # no synthetic bold here either: a large plain size stays crisp
        vs_title = make_font(self.TITLE_SIZE).render(self.winner_text(), True, palette[-1])
        lines = [make_font(self.LINE_SIZE).render(
            f"P{i + 1}    pts {self.scores[i]}    deaths {self.deaths[i]}", True, palette[-1])
            for i in range(len(self.scores))]
        prompt = make_font(self.PROMPT_SIZE).render("press any key to continue", True, palette[-1])
        width = max([vs_title.get_width()] + [line.get_width() for line in lines] + [prompt.get_width()])
        height = (vs_title.get_height() + self.LINE_GAP
                  + sum(line.get_height() + self.LINE_GAP for line in lines)
                  + prompt.get_height())
        self.panel = pg.Surface((width + self.PANEL_PAD * 2, height + self.PANEL_PAD * 2),
                                pg.SRCALPHA)
        pg.draw.rect(self.panel, self.PANEL_COLOR, self.panel.get_rect(),
                     border_radius=self.PANEL_RADIUS)
        y = self.PANEL_PAD
        for surf in [vs_title] + lines + [prompt]:
            self.panel.blit(surf, ((self.panel.get_width() - surf.get_width()) // 2, y))
            y += surf.get_height() + self.LINE_GAP
        self.pos = ((self.size[0] - self.panel.get_width()) // 2,
                    (self.size[1] - self.panel.get_height()) // 2)

    def resize(self, size: tuple[int, int] | V) -> None:
        self.size = tuple(size)
        self._build()

    def handle_events(self, events: list[pg.event.Event]) -> list[pg.event.Event]:
        if self.life >= self.INPUT_LOCK:
            for event in events:
                if event.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN):
                    pg.event.post(pg.event.Event(pg.USEREVENT + 5))  # and on to the menu
                    break
        return events

    def draw(self, surface: pg.Surface) -> None:
        self.life += 1
        surface.fill(self.bg)
        self.panel.set_alpha(min(255, int(self.life / self.INPUT_LOCK * 255)))
        surface.blit(self.panel, self.pos)


# ---------------------------------------------------------------------------
# (two-player mode) the predator & prey mode
#
# A match hands the two roles out at random. The predator always starts on the entrance of the
# maze while the prey starts on a random cell; if the prey reaches the exit before sharing a cell
# with the predator it wins the round and the roles stay, otherwise it dies and the roles swap.
# ---------------------------------------------------------------------------

# the direction a player faces when walking in from each edge (0 for top, clockwise)
VERSUS_ENTRANCE_HEADINGS = {0: Cell.GO_DOWN, 1: Cell.GO_LEFT, 2: Cell.GO_UP, 3: Cell.GO_RIGHT}
DIR_HEADINGS = {tuple(vec): cell for cell, vec in DIR_VECS.items()}  # the cell facing a direction
VERSUS_SPAWN_DIST_RATIO = 0.5  # the prey spawns at least that fraction of the maze diagonal away


def assign_versus_roles(p1, p2, rng=random):
    """(two-player mode) hand out the two roles at random, both orders being equally likely."""
    roles = [PlayerType.PREDATOR, PlayerType.PREY]
    rng.shuffle(roles)
    for player, role in zip((p1, p2), roles):
        player.set_player_type(role)


def versus_touching(predator, prey):
    """(two-player mode) whether the predator has caught the prey: the two sprites count as
    touching when the distance between the centres of what is drawn is smaller than half of their
    edge length. The centre of a sprite is the region of its animation, which is exactly the point
    "Player.draw" puts it on, so the rule follows the picture the players see - including the frames
    of a slide, where a player passes over the other one without ever sharing a cell."""
    here = predator.cur_anim.get_position()
    there = prey.cur_anim.get_position()
    return math.hypot(here[0] - there[0], here[1] - there[1]) < min(predator.size[0], prey.size[0]) / 2


def versus_pair(players):
    """(two-player mode) split a player list into (predator, prey) by the current roles."""
    predator = next((p for p in players if p.player_type == PlayerType.PREDATOR), None)
    prey = next((p for p in players if p.player_type != PlayerType.PREDATOR), None)
    return predator, prey


def pick_prey_spawn(maze, avoid, rng=random):
    """(two-player mode) pick the prey's spawning cell: random, but never on the predator's cell
    nor on the exit, and far enough from the predator to leave it a chance to run."""
    blocked = (tuple(avoid), tuple(maze.end))
    min_dist = max(1, int(VERSUS_SPAWN_DIST_RATIO * (maze.width + maze.height)))
    candidates, fallback = [], []
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in blocked:
                continue
            fallback.append(V(x, y))
            if abs(x - avoid[0]) + abs(y - avoid[1]) >= min_dist:
                candidates.append(V(x, y))
    if candidates:
        return rng.choice(candidates)
    if fallback:
        return rng.choice(fallback)
    return V(avoid)


def cell_to_surf(game, cell):
    """the position of a maze cell's center in a game's surface, mirroring Player.pos_to_surf for
    a game the player no longer belongs to."""
    return V(int(game.region[0] + game.cell_width * (cell[0] + 0.5) + 1),
             int(game.region[1] + game.cell_width * (cell[1] + 0.5)) + 1)


class VersusDeathTrans(GameScreen):
    # (two-player mode) the round after the predator caught the prey: the frozen frame fades to
    # gray, the prey's ghost floats out of it, its death count goes up and the next maze is
    # prepared with the two roles swapped. Any key jumps straight into that maze.

    # hyperparameters
    GRAY_FADE_TIME = 120  # frames the frozen frame takes to turn gray
    GHOST_TIME = 120  # frames the ghost takes to float out
    GHOST_RISE_RATIO = 0.1  # rising distance, as a fraction of the window height
    GHOST_DRIFT_RATIO = 0.22  # drift, as a fraction of the rising distance
    GHOST_WOBBLE = 8  # wobble amplitude, in pixels
    GHOST_COLOR = (238, 242, 245, 255)  # the ghost is the prey's silhouette, in a pale gray
    INPUT_LOCK = 20  # frames of ignored keys, so a held key cannot skip the scene
    DEATH_FONT_SIZE = 28
    PROMPT_FONT_SIZE = 24
    PROMPT_COLOR = (255, 255, 255)
    LINE_GAP = 12
    PROMPT_BOTTOM_RATIO = 0.86  # the death counter sits with its bottom at that fraction of the height

    def __init__(self, old_game: MazeGame):
        self.maze1 = old_game
        self.players: list[Player] = old_game.players
        self.predator, self.prey = versus_pair(self.players)

        # freeze the catch before the next maze moves everyone around: both players are drawn
        # exactly where the contact rule found them, which is also where they were last seen
        self._catcher_sprite = self.predator.cur_anim.image.copy()
        self._catcher_pos = V(self.predator.cur_anim.get_position())
        self._catcher_cell = V(self.predator.pos)  # used when a resize rebuilds the frozen frame
        self._ghost_sprite = self.prey.cur_anim.image.copy()
        self._ghost_cell = V(self.prey.pos)
        self._ghost_start = V(self.prey.cur_anim.get_position())
        self.deaths = self.prey.eaten + 1

        # count the catch, then swap the two roles for the next maze
        self.prey.eaten += 1
        self.predator.eat += 1
        self.prey.set_player_type(PlayerType.PREDATOR)
        self.predator.set_player_type(PlayerType.PREY)

        # the next maze keeps the presets; its entrance edge is random, because nobody left the
        # maze through an edge this time
        self.maze2 = self.next_game = MazeGame(gamemode=old_game.gamemode,
                                               size_preset=old_game.size_preset,
                                               difficulty=old_game.difficulty,
                                               players=old_game.players,
                                               pause_cb=old_game.pause_cb,
                                               sound_switch_cb=old_game.sound_switch_cb,
                                               resume_cb=old_game.resume_cb,
                                               menu_cb=old_game.menu_cb)
        for p in self.players:
            p.game = self.maze2

        # animation related
        self.frozen = None
        self.gray = None
        self.ghost = None
        self.ghost_pos = V(0, 0)
        self._build_frozen()
        self.ghost_pos = self._ghost_start  # the ghost floats out of the exact spot it died on
        self.prompt = self._build_prompt()
        self._gray_intp = DoubleQuad(self.GRAY_FADE_TIME)
        self._ghost_intp = DoubleQuad(self.GHOST_TIME)
        self.life = 0

    def _build_frozen(self):
        """render the frozen frame (the maze as it was, plus the predator that made the catch),
        its gray version and the ghost sprite; also used when the window is resized."""
        size = pg.display.get_window_size()
        self.frozen = pg.Surface(size)
        self.frozen.fill(self.maze1.bg_color)
        self.frozen.blit(self.maze1.maze_surf, (0, 0))
        sprite_size = (int(self.maze1.cell_width * 1.2),) * 2
        catcher = pg.transform.smoothscale(self._catcher_sprite, sprite_size)
        catcher_pos = (self._catcher_pos if self._catcher_pos is not None
                       else cell_to_surf(self.maze1, self._catcher_cell))
        self.frozen.blit(catcher, catcher.get_rect(center=(catcher_pos[0], catcher_pos[1])))
        self.gray = pg.transform.grayscale(self.frozen)

        self.ghost = pygame.transform.smoothscale(icons_dict["ghost"], (self.maze1.cell_width * 0.8,) * 2)
        self.ghost_pos = cell_to_surf(self.maze1, self._ghost_cell)

    def _build_prompt(self):
        """pre-render the death counter and the any-key hint as one centered block."""
        icon = pg.transform.smoothscale(icons_dict["dead_icon"].convert_alpha(), (34, 34))
        count = make_font(self.DEATH_FONT_SIZE).render(f"x {self.deaths}", True, self.PROMPT_COLOR)
        hint = make_font(self.PROMPT_FONT_SIZE).render("press any key to continue", True,
                                                       self.PROMPT_COLOR)
        counter_w = icon.get_width() + 6 + count.get_width()
        w = max(counter_w, hint.get_width())
        h = icon.get_height() + self.LINE_GAP + hint.get_height()
        prompt = pg.Surface((w, h), pg.SRCALPHA)
        prompt.blit(icon, ((w - counter_w) // 2, 0))
        prompt.blit(count, ((w - counter_w) // 2 + icon.get_width() + 6,
                            (icon.get_height() - count.get_height()) // 2))
        prompt.blit(hint, ((w - hint.get_width()) // 2, icon.get_height() + self.LINE_GAP))
        return prompt

    def resize(self, size: tuple[int, int] | V) -> None:
        self.maze1.resize(size)
        self.maze2.resize(size)
        self._catcher_pos = None  # a rebuilt frame falls back to the cell the predator stood on
        self._build_frozen()

    def handle_events(self, events: list[pg.event.Event]) -> list[pg.event.Event]:
        # any key jumps straight into the next maze, once the input lock is over
        for event in events:
            if event.type == pg.KEYDOWN and self.life >= self.INPUT_LOCK:
                pg.event.post(pg.event.Event(pg.USEREVENT + 3, {'new_game': self.maze2}))
                break
        return events

    def draw(self, surface: pg.Surface) -> None:
        self._gray_intp.update()
        self._ghost_intp.update()
        self.life += 1

        surface.blit(self.frozen, (0, 0))
        self.gray.set_alpha(int(170 * self._gray_intp.get()))
        surface.blit(self.gray, (0, 0))

        # the ghost floats up and out while fading away
        p = self._ghost_intp.get()
        rise = int(p * self.GHOST_RISE_RATIO * surface.get_height())
        drift = int(p * self.GHOST_DRIFT_RATIO * rise)
        wobble = int(math.sin(p * math.pi * 3) * self.GHOST_WOBBLE)
        self.ghost.set_alpha(int((1 - p) * 255))
        surface.blit(self.ghost, self.ghost.get_rect(center=(self.ghost_pos[0] + drift + wobble,
                                                             self.ghost_pos[1] - rise)))

        # the death counter and the hint fade in with the ghost
        self.prompt.set_alpha(int(p * 255))
        surface.blit(self.prompt, ((surface.get_width() - self.prompt.get_width()) // 2,
                                   int(surface.get_height() * self.PROMPT_BOTTOM_RATIO)
                                   - self.prompt.get_height()))

    def get_new_game(self):
        return self.maze2


if __name__ == '__main__':

    # noinspection PyUnusedLocal
    def test_callback(*args):
        print("test_callback")


    def test(test_idx=1):
        pg.init()
        screen = pg.display.set_mode((800, 600), pg.RESIZABLE)
        set_theme((200, 120, 0))
        clock = pg.time.Clock()

        if test_idx == 1:
            sc = WelcomeScreen((800, 600),
                               sound_switch_cb=test_callback,
                               single_player_cb=test_callback,
                               double_player_cb=test_callback,
                               size_set_cb=test_callback,
                               diff_set_cb=test_callback
                               )
        elif test_idx == 2:
            sc = HUD((800, 600))
        elif test_idx == 3:
            sc = GameGameTrans(MazeGame())
        elif test_idx == 4:
            sc = HUD((800, 600), game_mode=GameMode.DOUBLE,
                     fetch_scores_cb=lambda: [(3, 5), (2, 7)])
        elif test_idx == 5:
            sc = PauseScreen((800, 600))
        else:
            sc = MazeGame()
        while True:
            clock.tick(60)
            event_ls = pg.event.get()
            event_ls = sc.handle_events(event_ls)
            for event in event_ls:
                if event.type == pg.QUIT:
                    pg.quit()
                    exit()
                elif event.type == pg.WINDOWSIZECHANGED:
                    sc.resize(pg.display.get_window_size())
                elif event.type == pg.USEREVENT + 3:
                    print(event)

            screen.fill("gray")
            sc.draw(screen)

            pg.display.flip()


    test(3)
