"""
A simple widget module for pygame written by zyw.
"""

import sys

import pygame

from Resources import icons_dict, main_font_path, title as title_surf
from maze import Maze, SIZE_PRESETS, DIFFICULTY_PRESETS
from utils import adjust_color

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
    print(palette)


def make_font(size, bold=False):
    key = (size, bold)
    font = _font_cache.get(key)
    if font is None:
        font = pygame.font.Font(main_font_path, int(size))
        font.set_bold(bold)
        _font_cache[key] = font
    return font


def icon_coloring(surface, color):
    img = surface.copy().convert_alpha()
    img.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return img


def vertical_gradient(size, top_color, bottom_color):
    w, h = size
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / (h - 1)
        color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (w, y))
    return surf


class ButtonBase:
    def __init__(self, callback=None):
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.enabled = True
        self.pressed = False
        self.callback = callback

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)

    def _hovered(self):
        return self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())

    def handle_event(self, event):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                if self.callback is not None:
                    self.callback(self)
                    return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pressed = False
        return False


class Button(ButtonBase):

    def __init__(self, text="", icon=None, style="ghost", enabled=True, on_light=False, callback=None):
        """
        A rounded button that can hold text or icon.
            :param style: Literal["solid"|"ghost"]
                "solid" (filled teal, white content)
                "ghost" (frosted white, teal content)
            :param on_light: in case of ghost buttons being placed on a white background
            :param callback: callback function, accepting 1 positional argument "button", any of its return will be
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
            pygame.draw.rect(surface, fill, self.rect, border_radius=radius)
            content_color = palette[-1]
        elif self.on_light:
            # ghost button on a white panel: a light mist-teal fill keeps it visible
            if self.pressed:
                fill = (215, 230, 225)
            elif self._hovered():
                fill = (225, 240, 235)
            else:
                fill = (235, 240, 240)
            pygame.draw.rect(surface, fill, self.rect, border_radius=radius)
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
            pill = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(pill, (255, 255, 255, alpha), pill.get_rect(), border_radius=radius)
            surface.blit(pill, self.rect)

        # lay out icon + text as one centered group
        parts = []
        if self.icon is not None:
            icon_size = int(self.rect.height * 0.46)
            parts.append(pygame.transform.smoothscale(self.icon, (icon_size, icon_size)))
        if self.text:
            parts.append(make_font(int(self.rect.height * 0.40)).render(self.text, True, content_color))
        gap = 10
        total_w = sum(p.get_width() for p in parts) + gap * (len(parts) - 1)
        x = self.rect.centerx - total_w // 2
        for p in parts:
            surface.blit(p, (x, self.rect.centery - p.get_height() // 2))
            x += p.get_width() + gap


class IconButton(ButtonBase):
    def __init__(self, icon: pygame.Surface, size=44, callback=None, enabled=True):
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
        self.rect = pygame.Rect(0, 0, size, size)
        self.pressed = False
        self.enabled = enabled

    def draw(self, surface):
        if self.pressed:
            alpha = 200
        elif self._hovered():
            alpha = 255
        else:
            alpha = 220
        circle = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(circle, (255, 255, 255, alpha), (self.size // 2, self.size // 2), self.size // 2)
        surface.blit(circle, self.rect)
        icon_size = int(self.size * 0.56)
        icon = pygame.transform.smoothscale(self.icon, (icon_size, icon_size))
        surface.blit(icon, (self.rect.centerx - icon_size // 2, self.rect.centery - icon_size // 2))


class IconToggleButton(IconButton):
    _group_dict = {}

    def __init__(self, icon: pygame.Surface, icon_pressed=None, group=None, size=64, callback=None, enabled=True,
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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                new_state = not self.pressed
                if new_state is False:
                    if self.allow_all_release:
                        self.pressed = False
                        if self.callback is not None:
                            self.callback(self)
                    else:
                        return False
                else:
                    for btn in self._group_dict[self.group]:
                        btn.pressed = False
                    self.pressed = True
                if self.callback is not None:
                    self.callback(self)
                    return True
        return False

    def draw(self, surface):
        if self.pressed and self.icon_pressed is None:
            alpha = 175
        elif self._hovered():
            alpha = 255
        else:
            alpha = 220
        # circle = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        # pygame.draw.circle(circle, (255, 255, 255, alpha), (self.size // 2, self.size // 2), self.size // 2)
        # surface.blit(circle, self.rect)
        icon_size = int(self.size * 0.56)
        if self.pressed and self.icon_pressed is not None:
            icon = pygame.transform.smoothscale(self.icon_pressed, (icon_size, icon_size))
        else:
            icon = pygame.transform.smoothscale(self.icon, (icon_size, icon_size))
        surface.blit(icon, (self.rect.centerx - icon_size // 2, self.rect.centery - icon_size // 2))


class OptionSelector:
    # A labeled [<] current option [>] stepper laid out in one row.

    def __init__(self, label, options: list[str], index=0, callback=None):
        self.label = label
        self.options = options
        self.index = index
        self.rect = pygame.Rect(0, 0, 10, 10)
        self._pill_rect = pygame.Rect(0, 0, 10, 10)
        self._left_rect = pygame.Rect(0, 0, 10, 10)
        self._right_rect = pygame.Rect(0, 0, 10, 10)
        self._pressed = None
        self.callback = callback

    @property
    def value(self):
        return self.options[self.index]

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)
        h = self.rect.height
        pill_w = int(self.rect.width * 0.58)
        self._pill_rect = pygame.Rect(self.rect.right - pill_w, self.rect.y, pill_w, h)
        self._left_rect = pygame.Rect(self._pill_rect.x, self.rect.y, h, h)
        self._right_rect = pygame.Rect(self._pill_rect.right - h, self.rect.y, h, h)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._left_rect.collidepoint(event.pos):
                self._pressed = "left"
            elif self._right_rect.collidepoint(event.pos):
                self._pressed = "right"
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            hit = self._pressed
            self._pressed = None
            if hit == "left" and self._left_rect.collidepoint(event.pos):
                self._step(-1)
                if self.callback is not None:
                    self.callback(self)
                return True
            if hit == "right" and self._right_rect.collidepoint(event.pos):
                self._step(1)
                if self.callback is not None:
                    self.callback(self)
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
        pill = pygame.Surface(self._pill_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(pill, (255, 255, 255, 220), pill.get_rect(),
                         border_radius=self._pill_rect.height // 2)
        surface.blit(pill, self._pill_rect)

        # current option
        font = make_font(int(self.rect.height * 0.40))
        text = font.render(self.options[self.index].upper(), True, main_color)
        surface.blit(text, (self._pill_rect.centerx - text.get_width() // 2,
                            self._pill_rect.centery - text.get_height() // 2))

        # arrows
        for side, rect in (("left", self._left_rect), ("right", self._right_rect)):
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            color = palette[5] if self._pressed == side or hovered else palette[4]
            cx, cy = rect.center
            w, hh = self.rect.height * 0.10, self.rect.height * 0.16
            if side == "right":
                points = ((cx - w, cy - hh), (cx + w, cy), (cx - w, cy + hh))
            else:
                points = ((cx + w, cy - hh), (cx - w, cy), (cx + w, cy + hh))
            pygame.draw.polygon(surface, color, points)


class WelcomeScreen:
    # The main menu

    DECO_COLS = 40
    DECO_ROWS = 30

    def __init__(self,
                 size,
                 sound_switch_cb=None,
                 single_player_cb=None,
                 double_player_cb=None,
                 size_set_cb=None,
                 diff_set_cb=None):
        self.size = size
        self.sound_on = True

        # decorative faint maze behind the menu
        self._deco = Maze((self.DECO_COLS, self.DECO_ROWS),
                          start=(0, 0), end=(self.DECO_COLS - 1, self.DECO_ROWS - 1))
        self._deco_inst = self._deco.draw_instructions()
        self._deco_surf = None

        self.sound_btn = IconToggleButton(icon_coloring(icons_dict["sound_on"], main_color),
                                          icon_coloring(icons_dict["sound_off"], main_color),
                                          size=46, callback=sound_switch_cb)
        self.single_btn = Button("SINGLE PLAYER", icon=icons_dict["play"], style="solid", callback=single_player_cb)
        self.double_btn = Button("TWO PLAYER - SOON", style="ghost", enabled=False, callback=double_player_cb)

        # maze option selectors; option keys follow the maze preset dictionaries
        self.size_selector = OptionSelector("SIZE", list(SIZE_PRESETS), index=1, callback=size_set_cb)
        self.diff_selector = OptionSelector("DIFFICULTY", list(DIFFICULTY_PRESETS), index=1, callback=diff_set_cb)
        self._card_rect = pygame.Rect(0, 0, 10, 10)

        self.bg = None
        self.title_img = None
        self.title_pos = (0, 0)
        self.title_shadow = None
        self.hint_img = None
        self.hint_pos = (0, 0)
        self.resize(size)

    @property
    def difficulty(self):
        return self.diff_selector.value

    def resize(self, size):
        self.size = size
        w, h = size
        self.bg = vertical_gradient(
            size,
            adjust_color(palette[-3],
                         hue_offset=10,
                         saturation_factor=0.8),
            adjust_color(palette[-3],
                         hue_offset=-10,
                         saturation_factor=0.8,
                         brightness_factor=0.95))
        self._render_deco()

        # title: up to 86% of the width and 13% of the height, keeps aspect
        aspect = title_surf.get_width() / title_surf.get_height()
        title_h = min(int(h * 0.13), int(w * 0.86 / aspect))
        title_w = int(title_h * aspect)
        self.title_img = pygame.transform.smoothscale(title_surf.convert_alpha(), (title_w, title_h))
        shadow = title_surf.copy().convert_alpha()
        shadow.fill((45, 85, 75, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.title_shadow = pygame.transform.smoothscale(shadow, (title_w, title_h))
        self.title_shadow.set_alpha(60)
        self.title_pos = ((w - title_w) // 2, int(h * 0.15) - title_h // 2)

        # options card
        cx = w // 2
        btn_w = min(int(w * 0.66), 320)
        card_h = min(150, max(96, int(h * 0.18)))
        card_top = int(h * 0.335)
        self._card_rect = pygame.Rect(cx - btn_w // 2, card_top, btn_w, card_h)
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

    def _render_deco(self):
        # Render the faint decorative maze, centered behind the menu.
        w, h = self.size
        cols, rows = self.DECO_COLS, self.DECO_ROWS
        cw = max(w / cols, h / rows)
        edge_w = max(4, int(cw // 8))
        mw, mh = cw * cols, cw * rows
        ox, oy = (w - mw) / 2, (h - mh) / 2 + h * 0.01
        self._deco_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        line_color = (255, 255, 255, 46)
        inst = self._deco_inst
        for row in range(rows * 2 + 1):
            for col in range(cols * 2 + 1):
                op = inst[row][col]
                x = int(ox + cw * (col // 2))
                y = int(oy + cw * (row // 2))
                if row % 2 == 0 and col % 2 == 1 and op == 0:
                    pygame.draw.line(self._deco_surf, line_color, (x, y), (x + int(cw), y), edge_w)
                elif row % 2 == 1 and col % 2 == 0 and op == 0:
                    pygame.draw.line(self._deco_surf, line_color, (x, y), (x, y + int(cw)), edge_w)
                if row % 2 == 0 and col % 2 == 0 and edge_w > 2:
                    pygame.draw.circle(self._deco_surf, line_color, (x, y), edge_w // 2)

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
        surface.blit(self.bg, (0, 0))
        surface.blit(self._deco_surf, (0, 0))
        surface.blit(self.title_shadow, (self.title_pos[0] + 3, self.title_pos[1] + 5))
        surface.blit(self.title_img, self.title_pos)

        # options card
        card = pygame.Surface(self._card_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(card, (255, 255, 255, 150), card.get_rect(), border_radius=22)
        surface.blit(card, self._card_rect)
        self.size_selector.draw(surface)
        self.diff_selector.draw(surface)

        self.double_btn.draw(surface)
        self.single_btn.draw(surface)
        self.sound_btn.draw(surface)
        surface.blit(self.hint_img, self.hint_pos)


class HUD:
    # In-game heads-up display: score pill, pause / sound buttons, pause panel.

    def __init__(self,
                 size,
                 sound_switch_cb=None):
        self.size = size
        self.sound_on = True
        self.paused = False

        self.pause_btn = IconButton(icon_coloring(icons_dict["pause"], main_color), size=42)
        self.sound_btn = IconToggleButton(icon_coloring(icons_dict["sound_on"], main_color),
                                          icon_coloring(icons_dict["sound_off"], main_color),
                                          size=46, callback=sound_switch_cb)

        self.resume_btn = Button("RESUME", icon=icons_dict["play"], style="solid")
        self.menu_btn = Button("MENU", style="ghost", on_light=True)

        self._score_icon = None
        self._panel_rect = None
        self._panel_title = None
        self._panel_hint = None
        self.resize(size)

    def set_paused(self, paused):
        self.paused = paused

    # -- layout --
    def resize(self, size):
        self.size = size
        w, h = size
        s = self.pause_btn.size
        self.pause_btn.set_rect((w - s - 16, 16, s, s))
        self.sound_btn.set_rect((w - s * 2 - 28, 16, s, s))
        self._score_icon = pygame.transform.smoothscale(
            icons_dict["eat_icon_v1"].convert_alpha(), (26, 26))

        # pause panel
        pw, ph = min(int(w * 0.78), 380), 250
        self._panel_rect = pygame.Rect((w - pw) // 2, (h - ph) // 2, pw, ph)
        btn_w, btn_h = int(pw * 0.62), 52
        bx = self._panel_rect.centerx - btn_w // 2
        self.resume_btn.set_rect((bx, self._panel_rect.y + 100, btn_w, btn_h))
        self.menu_btn.set_rect((bx, self._panel_rect.y + 100 + btn_h + 18, btn_w, btn_h))
        self._panel_title = make_font(30).render("PAUSED", True, main_color)
        self._panel_hint = make_font(16).render("PRESS ESC TO RESUME", True, HINT_TEXT)

    # -- events / drawing --
    def handle_events(self, events):
        for event in events:
            if self.paused:
                if self.resume_btn.handle_event(event):
                    return "resume"
                if self.menu_btn.handle_event(event):
                    return "quit_to_menu"
            else:
                if self.pause_btn.handle_event(event):
                    return "pause"
                if self.sound_btn.handle_event(event):
                    return "toggle_sound"
        return None

    def draw(self, surface, score=0):
        # score pill (top-left)
        text = make_font(20).render(f"x {score}", True, main_color)
        pad = 9
        pill_w = pad * 2 + self._score_icon.get_width() + 6 + text.get_width()
        pill_h = 40
        pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pygame.draw.rect(pill, (255, 255, 255, 220), pill.get_rect(), border_radius=pill_h // 2)
        surface.blit(pill, (16, 16))
        surface.blit(self._score_icon, (16 + pad, 16 + (pill_h - self._score_icon.get_height()) // 2))
        surface.blit(text, (16 + pad + self._score_icon.get_width() + 6,
                            16 + (pill_h - text.get_height()) // 2))

        if self.paused:
            self._draw_pause_panel(surface)
        else:
            self.pause_btn.draw(surface)
            self.sound_btn.draw(surface)

    def _draw_pause_panel(self, surface):
        w, h = self.size
        scrim = pygame.Surface((w, h), pygame.SRCALPHA)
        scrim.fill((35, 58, 52, 120))
        surface.blit(scrim, (0, 0))

        r = self._panel_rect
        panel = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 255, 255, 245), panel.get_rect(), border_radius=24)
        surface.blit(panel, r)

        surface.blit(self._panel_title,
                     (r.centerx - self._panel_title.get_width() // 2, r.y + 34))
        surface.blit(self._panel_hint,
                     (r.centerx - self._panel_hint.get_width() // 2, r.y + 72))
        self.resume_btn.draw(surface)
        self.menu_btn.draw(surface)


if __name__ == '__main__':

    def test_callback(widget):
        print(widget)
        print()


    def test(test_idx=1):
        pygame.init()
        screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        set_theme((200, 120, 0))
        if test_idx == 1:
            sc = WelcomeScreen((800, 600),
                               sound_switch_cb=test_callback,
                               single_player_cb=test_callback,
                               double_player_cb=test_callback,
                               size_set_cb=test_callback,
                               diff_set_cb=test_callback
                               )
        else:
            sc = HUD((800, 600))
        while True:
            event_ls = pygame.event.get()
            event_ls = sc.handle_events(event_ls)
            for event in event_ls:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.WINDOWSIZECHANGED:
                    sc.resize(pygame.display.get_window_size())

            screen.fill("gray")
            sc.draw(screen)

            pygame.display.flip()


    test(1)
