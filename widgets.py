"""
A simple widget module for pygame.

The skeleton is written by ZCR, and implementations are written by ZYY.
"""
import pygame

focused = []
root_widgets = []
d_circle_counter = 0  # for display


# TODO: 做完记着把TODO删了（我是不是在说废话）


class Widget:
    """base class for widgets"""
    def __new__(cls, *args, **kwargs):
        if cls is Widget:
            raise RuntimeError("Cannot instantiate a widget directly")
        return object.__new__(cls)

    def __init__(self):
        # when overriding this, guarantee the super() call occurred
        # at the very beginning or the subclass codes will be overridden
        self.children = []
        self.parent = None
        self.surface = None
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._focus = False
        self._x = 0
        self._y = 0

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value
        self.rect.x = value

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value
        self.rect.y = value

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val: bool):
        if val != self._focus:
            self._focus = val
            if val:
                focused.append(self)
            else:
                focused.remove(self)

    def update(self):
        for child in reversed(self.children):
            child.update()

    def add_child(self, widget):
        if isinstance(widget, Widget) and widget not in self.children:
            self.children.append(widget)
            widget.parent = self

    def remove_child(self, widget):
        if widget in self.children:
            self.children.remove(widget)
            widget.parent = None

    def draw(self, surface=None):
        target_surface = surface or (self.parent.surface if self.parent else None)
        if target_surface:
            self.surface = target_surface

            for child in self.children:
                child.draw(target_surface)

    def handle_events(self, events) -> list:

        for child in reversed(self.children):
            events = child.handle_events(events)
        return events

    def set_as_root(self):
        root_widgets.append(self)

    def cancel_root(self):
        root_widgets.remove(self)


class Container(Widget):
    def __init__(self):
        """A widget container. It is invisible but can hold multiple widgets as its children.
        All of its children's x and y coordinates should be larger than 0, or they will not be fully displayed.
        (Note that the class doesn't check this!)

        About adding and moving children:
            - Adding a widget as its child doesn't move it
            - Moving the container (by setting the x and y property) moves all of its children"""
        super().__init__()

    @property
    def x(self):
        """the widget's X coordinate, any adjustment will be applied to the children's"""
        return self._x

    @x.setter
    def x(self, value):
        delta = value - self._x
        self._x = value
        self.rect.x = value
        for widget in self.children:
            widget.x += delta

    @property
    def y(self):
        """the widget's Y coordinate, any adjustment will be applied to the children's"""
        return self._y

    @y.setter
    def y(self, value):
        delta = value - self._y
        self._y = value
        self.rect.y = value
        for widget in self.children:
            widget.y += delta




class Label(Widget):
    """a simple label widget to show texts"""

    def __init__(self, text="", font: pygame.font.Font = None, color='black', alignment='left'):
        super().__init__()
        self._text = text
        self._font_color = color
        self._alignment = alignment
        self._font = font
        self._rendered_text = None
        self._update_rendered_text()
        self._x = 0
        self._y = 0
        self.width = self._rendered_text.get_width() if self._rendered_text else 0
        self.height = self._rendered_text.get_height() if self._rendered_text else 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def add_child(self, widget):
        raise TypeError('Label objects cannot have children')

    @property
    def text(self):
        """text to be shown"""
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self._update_rendered_text()

        self.width = self._rendered_text.get_width() if self._rendered_text else 0
        self.height = self._rendered_text.get_height() if self._rendered_text else 0

    @property
    def font_color(self):
        return self._font_color

    @font_color.setter
    def font_color(self, value):
        self._font_color = value
        self._update_rendered_text()

    @property
    def alignment(self):
        return self._alignment

    @alignment.setter
    def alignment(self, value):
        allowed_alignments = ['left', 'center', 'right']
        if value not in allowed_alignments:
            raise ValueError(f"alignment must be one of {allowed_alignments}")
        self._alignment = value
        self._update_rendered_text()

    def _update_rendered_text(self):
        if self._font and self._text:
            self._rendered_text = self._font.render(self._text, True, self._font_color)
        else:
            self._rendered_text = None

    def update(self):
        self._update_rendered_text()
        self.width = self._rendered_text.get_width() if self._rendered_text else 0
        self.height = self._rendered_text.get_height() if self._rendered_text else 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface=None):
        target_surface = surface or (self.parent.surface if self.parent else None)
        if target_surface and self._rendered_text:
            if self._alignment == 'left':
                x = self.x
            elif self._alignment == 'center':
                x = self.x + (self.width - self._rendered_text.get_width()) // 2
            else:  # right
                x = self.x + self.width - self._rendered_text.get_width()

            y = self.y + (self.height - self._rendered_text.get_height()) // 2
            target_surface.blit(self._rendered_text, (x, y))
        super().draw(surface)


class ImageButton(Widget):
    pass
    # TODO: 实现一个简单按钮类，鼠标点击会变成 pressed 状态，释放后又变回 normal，可以参照 ImageToggleButton 的实现
    # 这个类主要会用到开始，退出等按钮上


class ImageToggleButton(Widget):
    """use an image as a toggle button
    the image passed to the __init__ method will be used when the button`s state is 'normal'
    and other images will be generated automatically.
    if some buttons belong to the same group, only one of them is in 'pressed' state.
    """

    # TODO: change the toggle display effect
    # 这个按钮类也有两个状态，区别是这里按下后改变状态并且保持，而不是变成pressed。主要会用到游戏的各种按钮，比如暂停/开始, 声音开/关

    # 类级别的编组注册表
    _groups = {}

    def __init__(self,
                 image,
                 pressed_image=None,
                 disabled_image=None,
                 group: str = None,
                 enabled=True,
                 allow_all_release=True,
                 toggle_effect=None):  # TODO: 这里只加了一个参数，没有完善逻辑。默认效果就是按下变成深色，看看能不能加一点比较丝滑的效果（如果需要新的效果类型，就写在effects）
        super().__init__()
        self._original_image = image
        self._enabled = enabled
        self._pressed = False
        self.allow_all_release = allow_all_release

        self._normal_image = image
        self._pressed_image = self._adjust_brightness(image, 0.7) if pressed_image is None else pressed_image
        self._disabled_image = self._convert_to_grayscale(image) if disabled_image is None else disabled_image

        self._on_press = None
        self._on_release = None

        self.width = image.get_width()
        self.height = image.get_height()
        self.rect = pygame.rect.Rect(self.x, self.y, self.width, self.height)
        self.toggle_effect = toggle_effect

        self._group = group
        if group:
            if group not in ImageToggleButton._groups:
                ImageToggleButton._groups[group] = []
            ImageToggleButton._groups[group].append(self)

    def add_child(self, widget):
        raise TypeError('ImageToggleButton cannot have children')

    @staticmethod
    def _adjust_brightness(surface, factor):
        bright_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        bright_surface.fill((255 * factor, 255 * factor, 255 * factor, 255))
        bright_surface.blit(surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return bright_surface

    @staticmethod
    def _convert_to_grayscale(surface):
        gray_surface = pygame.transform.grayscale(surface)
        return gray_surface.convert_alpha()

    @property
    def state(self):
        """possible states: 'pressed', 'released', 'disabled_pressed', 'disabled_released'"""
        if not self._enabled:
            return "disabled_pressed" if self._pressed else "disabled_released"
        return "pressed" if self._pressed else "released"

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def pressed(self):
        return self._pressed

    @pressed.setter
    def pressed(self, value):
        if self._enabled and self._pressed != value:
            self._pressed = value
            if value:
                if self._group and self._group in ImageToggleButton._groups:
                    for button in ImageToggleButton._groups[self._group]:
                        if button != self and button.pressed:
                            button.pressed = False
                if self._on_press:
                    self._on_press()
            else:
                if self._on_release:
                    self._on_release()

    @property
    def image(self):
        return self._original_image

    @image.setter
    def image(self, value):
        self._original_image = value
        self._normal_image = value
        self._pressed_image = self._adjust_brightness(value, 0.7)
        self._disabled_image = self._convert_to_grayscale(value)

        # 更新尺寸
        self.width = value.get_width()
        self.height = value.get_height()

    def set_on_press(self, callback):
        self._on_press = callback

    def set_on_release(self, callback):
        self._on_release = callback

    def update(self):
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def handle_events(self, events):
        if self._enabled:
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.rect.collidepoint(event.pos):
                        events.remove(event)
                        if not (self.pressed and not self.allow_all_release) or not self.pressed:
                            self.pressed = not self.pressed
                            if self.pressed:
                                if self._on_press is not None:
                                    self._on_press()
                            else:
                                if self._on_release is not None:
                                    self._on_release()

        events = super().handle_events(events)
        return events

    def draw(self, surface=None):
        target_surface = surface or (self.parent.surface if self.parent else None)
        if target_surface:
            if not self._enabled:
                current_image = self._disabled_image
            else:
                current_image = self._pressed_image if self._pressed else self._normal_image

            target_surface.blit(current_image, (self.x, self.y))


class ProgressBar(Widget):
    # TODO: complete the class
    def __init__(self, parent):
        super().__init__()


def update_widgets(events, surface):

    for w in root_widgets:
        events = w.handle_events(events)
        w.draw(surface)
    return events


def draw_widgets(surface):
    global d_circle_counter
    d_circle_counter += 1
    if d_circle_counter == 72:
        d_circle_counter = 0
    for w in root_widgets:
        w.draw(surface)


def handle_events(events):
    for w in root_widgets:
        events = w.handle_events(events)
    return events


def test():
    import pygame
    pygame.init()
    test_font = pygame.font.Font('Resources/Fonts/impact.ttf', 20)
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Widgets Test")

    root = Container()
    root.set_as_root()

    label = Label(text='hello world', font=test_font)
    root.add_child(label)

    img = pygame.image.load('Resources/Images/icons/_play.png')
    img = pygame.transform.smoothscale(img, (50, 50))
    button = ImageToggleButton(img, group='test1')
    button.x = 100
    root.add_child(button)

    root.x = 200
    root.y = 300

    running = True
    clock = pygame.time.Clock()

    while running:
        screen.fill((108, 255, 108))
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        update_widgets(events, screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == '__main__':
    test()
