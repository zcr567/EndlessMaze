"""
A simple widget module for pygame first version written by zyw and refactored by zcr .
"""

import random
from enum import IntEnum, IntFlag

import pygame
import pygame as pg

from Resources import *
from effects import Linear, Quad, DoubleQuad, ReversedQuad, Shadow, ChangeColor, RoundMaskFade
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
                 diff_set_cb=None):
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
        self.double_btn = Button("TWO PLAYER - SOON", style="ghost", callback=double_player_cb)

        # maze option selectors; option keys follow the maze preset dictionaries
        self.size_selector = OptionSelector("SIZE", list(SIZE_PRESETS), index=1, callback=size_set_cb)
        self.diff_selector = OptionSelector("DIFFICULTY", list(DIFFICULTY_PRESETS), index=1, callback=diff_set_cb)
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

        s = self.sound_btn.size
        self.sound_btn.set_rect((w - s - 22, 22, s, s))

        self.hint_img = make_font(max(14, int(h * 0.022))).render(
            "MADE BY ZCR & ZYW", True, palette[-1])
        self.hint_img.set_alpha(255)
        self.hint_pos = (cx - self.hint_img.get_width() // 2, h - self.hint_img.get_height() - 26)

    def handle_events(self, events):
        # Process one frame's events, return an action string or None.
        for event in events:
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

        self.double_btn.draw(surface)
        self.single_btn.draw(surface)
        self.sound_btn.draw(surface)
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
                GameMode.DOUBLE shows the skull and the eat icon for both players
            :param pause_cb: called when the pause button is hit, no arguments
            :param sound_switch_cb: called when the sound button is toggled, no arguments
            :param fetch_scores_cb: called every frame to fetch per-player scores,
                expected to return [(eaten, eat), ...] in player order
        """
        self.size = size
        # GameMode is defined below in this module, so the default is resolved here
        self.game_mode = GameMode.SINGLE if game_mode is None else game_mode
        self.fetch_scores_cb = fetch_scores_cb

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

    def _scale_label(self, key, label_h):
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
    prey = 2


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
        self.resize(pg.display.get_window_size())
        self.timer = Timer()

        # game logic related
        self.players = []
        if players is None:
            if gamemode == GameMode.SINGLE:
                self.players.append(Player(self, pos0=self.maze.start))
            elif gamemode == GameMode.DOUBLE:
                pass
        else:
            self.players = players
        if gamemode == GameMode.SINGLE:
            self.players[0].pos = self.maze.start
            self.players[0].pos_next = self.maze.start
        # HUD and pause screen as attributes of the maze game;
        # created after players so fetch_scores has real data to read
        self.pause_cb = pause_cb
        self.sound_switch_cb = sound_switch_cb
        self.resume_cb = resume_cb
        self.menu_cb = menu_cb
        self.hud = HUD(pg.display.get_window_size(),
                       game_mode=gamemode,
                       pause_cb=pause_cb,
                       sound_switch_cb=sound_switch_cb,
                       fetch_scores_cb=self.fetch_scores)
        self.pause_screen = PauseScreen(pg.display.get_window_size(),
                                        resume_cb=resume_cb,
                                        menu_cb=menu_cb,
                                        sound_switch_cb=sound_switch_cb)
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
        Shadow(surf, (self.maze_edge_width // 2, self.maze_edge_width // 2))

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

    def game_logic(self):
        if self.gamemode == GameMode.SINGLE:
            if self.players[0].pos == self.maze.end:
                score = int(self.SCORE_DICT[self.gamemode][self.difficulty]
                            * self.field_width
                            * self.field_height
                            * self.maze.p_len
                            / self.timer.get())
                self.players[0].score += score
                print(self.players[0].score)
                game_end = pg.event.Event(pg.USEREVENT + 2,
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

    def draw(self, surface):
        surface.fill(self.bg_color)
        surface.blit(self.maze_surf, (0, 0))
        for p in self.players:
            p.draw(surface)


class GameGameTrans(GameScreen):
    PHASE_TIMES = (40, 40, 40)  # index 0 for phase 0, 1 for phase 3, 2 for phase 2

    def __init__(self, old_game: MazeGame):
        """A fancy transition between two maze games."""
        super().__init__()

        # basic
        self.maze1 = old_game
        self.players: list[Player] = old_game.players
        self.end_edge = self.maze1.end_edge

        # generate new mase game
        if self.end_edge == 2:
            self.players[0].heading = Cell.GO_DOWN
            self.start_edge = 0
        elif self.end_edge == 0:
            self.players[0].heading = Cell.GO_UP
            self.start_edge = 2
        elif self.end_edge == 1:
            self.players[0].heading = Cell.GO_RIGHT
            self.start_edge = 3
        elif self.end_edge == 3:
            self.players[0].heading = Cell.GO_LEFT
            self.start_edge = 1
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
        self.surface1 = self.maze1.maze_surf.copy().convert(self.surface0)
        self.surface2 = self.maze2.maze_surf.copy().convert(self.surface0)
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
        start = self.maze2.maze.start
        self.p2_fade = RoundMaskFade(self.surface2,
                                     self.PHASE_TIMES[1] // 2,
                                     V(int(self.maze2.region[0] + self.maze2.cell_width * (start[0] + 0.5) + 1),
                                       int(self.maze2.region[1] + self.maze2.cell_width * (start[1] + 0.5)) + 1),
                                     Quad)

        # path animation
        self.intp0 = Quad(self.PHASE_TIMES[0] * 3 // 4)
        self.intp1 = DoubleQuad(self.PHASE_TIMES[2])
        self.intp2 = Quad(self.PHASE_TIMES[1] // 2, initial_phase=1, direction=-1)
        self.offset = V(0, 0)
        self.line_width = self.maze1.maze_edge_width
        self.line_width0 = self.line_width
        self.line_width2 = self.maze2.maze_edge_width
        self.p_size0 = self.maze1.cell_width * 1.2
        self.p_size1 = self.maze2.cell_width * 1.2
        self.max_offset = max(*pg.display.get_window_size())
        self.line_length = sum(pg.display.get_window_size())

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
        if self._ani_p == 0 and self.life == self.PHASE_TIMES[0]:
            self.life = 0
            self._ani_p += 1
            self.surface0.fill(self._start_color)
        elif self._ani_p == 2 and self.life == self.PHASE_TIMES[1]:
            end = pg.event.Event(pg.USEREVENT + 3,
                                 {'new_game': self.maze2})
            pg.event.post(end)
        elif self._ani_p == 1:
            for event in events:
                if event.type == pg.KEYDOWN or event.type == pg.MOUSEBUTTONDOWN:
                    if not self.pre_p3:
                        pygame.event.post(pygame.event.Event(pygame.USEREVENT + 7, {"sound": rotate_sound}))
                        self.color_anim.animate_now()
                        self.pre_p3 = 1
                        self.life = 0
            if self.pre_p3 and self.life == self.PHASE_TIMES[2]:
                self.life = 0
                self._ani_p += 1
                for p in self.players:
                    p.game = self.maze2
        self.life += 1
        return events

    def draw(self, surface: pg.Surface) -> None:
        if self._ani_p == 0:
            self.surface0.fill(self._start_color)
            self._draw_path_0()
            self.surface0.blit(self.path_surf, (0, 0))
            self.surface0.blit(self.surface1, self.offset)
            self.players[0].directly_draw(self.surface0, self.p0[0])
            if self.life >= self.PHASE_TIMES[0] // 4:
                self.intp0.update()
                self.offset = V(int(-self.intp0.get() * self.max_offset * self.direction[0]),
                                int(-self.intp0.get() * self.max_offset * self.direction[1]))
            surface.blit(self.surface0, (0, 0))
        elif self._ani_p == 1:
            surface.blit(self.surface0, (0, 0))
            if self.pre_p3:
                self.line_width = int(self.line_width0 + (self.line_width2 - self.line_width0) * self.intp1.get())
                p_size = int(self.p_size0 + (self.p_size1 - self.p_size0) * self.intp1.get())
                p_size = (p_size, p_size)
                p = self.p0[0] + (self.p0[1] - self.p0[0]) * self.intp1.get()
                self._draw_path_1()
                surface.blit(self.path_surf, (0, 0))
                self.players[0].directly_draw(surface, p, p_size)

                self.intp1.update()
            else:
                surface.blit(self.surface0, (0, 0))
                surface.blit(self.path_surf, (0, 0))
                self.players[0].directly_draw(surface, self.p0[0])
        elif self._ani_p == 2:
            self.surface0.fill(self._end_color)
            self._draw_path_2()
            self.surface0.blit(self.path_surf, (0, 0))
            if self.life == self.PHASE_TIMES[1] // 3:
                self.p2_fade.animate_now()
            if self.life > self.PHASE_TIMES[1] // 3:
                self.surface0.blit(self.surface2, self.offset)
            self.players[0].directly_draw(self.surface0, self.p0[1])

            self.intp2.update()
            self.offset = V(int(self.intp2.get() * self.max_offset * self.direction[0]),
                            int(self.intp2.get() * self.max_offset * self.direction[1]))

            surface.blit(self.surface0, (0, 0))

    def get_new_game(self):
        return self.maze2


class ManuGameTrans(GameScreen):
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
