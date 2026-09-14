"""
Simple property adjustments & animated effects for pygame surfaces.

The skeleton is written by ZCR, and implementations are written by ZYY.
"""
import math
from weakref import ref as weakref

import pygame

__all__ = ["Linear", "Quad", "ReversedQuad", "DoubleQuad", "ChangeColor", "Shadow", "Fade", "RoundMaskFade"]

_all_effects: list[weakref] = []


def trim(value, min_val=0, max_val=1):
    """Trim a value to make sure it is between min_val and max_val."""
    if min_val > max_val:
        raise ValueError("min_val must be no more than max_val")
    return min(max(value, min_val), max_val)


class Interpolation:
    def __init__(self, step: int, initial_phase: int | float = 0, direction: int = 1):
        """Base class for interpolation objects.
        :param step: total steps the interpolation should take from 0 to 1.
        :param initial_phase: initial _phase of the interpolation.
        :param direction: direction of the interpolation, 1 for ascending, -1 for descending."""
        if direction not in (-1, 1):
            raise ValueError("direction must be either 1 or -1")
        if initial_phase < 0 or initial_phase > 1:
            raise ValueError("initial_phase must be between 0 and 1")
        if step <= 0 or not isinstance(step, int):
            raise ValueError("step must be an integer larger than 1")
        self._phase_prev = initial_phase
        self._phase = initial_phase
        self._direction = 1 if direction >= 0 else -1
        self.step = step

    @property
    def direction(self):
        return self._direction

    def clear(self):
        self._phase = 0

    def set(self, value: int | float):
        if 0 <= value <= 1:
            self._phase = value
        else:
            raise ValueError("parameter 'value' must be between 0 and 1.")

    def is_end(self):
        return (self._phase == 1 if self._direction == 1 else self._phase == 0) and self._phase == self._phase_prev

    def get(self):
        return self._phase

    def get_delta(self):
        return self._phase - self._phase_prev

    def switch(self):
        self._direction = -self._direction

    def update(self):
        raise NotImplementedError


class Linear(Interpolation):
    # 这个已经写好了，可供参考
    def update(self):
        self._phase_prev = self._phase
        self._phase = trim(self._phase + 1 / self.step * self._direction)
        return self._phase


class Quad(Interpolation):
    # 二次函数型，先慢后快
    def __init__(self, step, initial_phase=0, direction=1):
        super().__init__(step, initial_phase, direction)
        self._current_step = round((initial_phase ** 0.5) * step)

    def clear(self):
        super().clear()
        self._current_step = 0

    def set(self, value):
        super().set(value)
        self._current_step = round((value ** 0.5) * self.step)

    def update(self):
        self._phase_prev = self._phase
        self._current_step = trim(self._current_step + self._direction, 0, self.step)
        t = self._current_step / self.step
        self._phase = t ** 2
        return self._phase


class ReversedQuad(Interpolation):
    # Quad 的图像中心对称， 先快后慢
    def __init__(self, step, initial_phase=0, direction=1):
        super().__init__(step, initial_phase, direction)
        self._current_step = round((1 - (1 - initial_phase) ** 0.5) * step)

    def clear(self):
        super().clear()
        self._current_step = 0

    def set(self, value):
        super().set(value)
        self._current_step = round((1 - (1 - value) ** 0.5) * self.step)

    def update(self):
        self._phase_prev = self._phase
        self._current_step = trim(self._current_step + self._direction, 0, self.step)
        t = self._current_step / self.step
        self._phase = 1 - (1 - t) ** 2
        return self._phase


class DoubleQuad(Interpolation):
    # 双二次平滑：用Smoothstep = t²(3 - 2t)近似sin

    def __init__(self, step, initial_phase=0, direction=1):
        super().__init__(step, initial_phase, direction)
        # 三次方程反推不精确，线性近似
        self._current_step = round(initial_phase * step)

    def clear(self):
        super().clear()
        self._current_step = 0

    def set(self, value):
        super().set(value)
        self._current_step = round(value * self.step)

    def update(self):
        self._phase_prev = self._phase
        self._current_step = trim(self._current_step + self._direction, 0, self.step)
        t = self._current_step / self.step
        self._phase = t * t * (3 - 2 * t)
        return self._phase


class Effect:
    _NEAR_END_THR = 1e-3

    def __init__(self,
                 surface: pygame.Surface,
                 *args,
                 duration=30,
                 interpolation: type[Interpolation] = Linear,
                 **kwargs):
        """Base class for all effects. All the effects accept a pygame.Surface object and modify it in-place.
        :param duration: duration of the effect, in frames."""
        self._surface = surface
        self._duration = duration
        self._interpolation = interpolation
        self._cur_interpolation = None
        _all_effects.append(weakref(self))

    @property
    def animating(self):
        return self._cur_interpolation is not None

    @property
    def phase(self):
        if self._cur_interpolation is None:
            return 0
        else:
            return self._cur_interpolation.get()

    def animate_now(self, step: int | None = None, initial_phase: int | float = 0, direction: int = 1):
        self._cur_interpolation = self._interpolation(self._duration if step is None else step, initial_phase,
                                                      direction)

    def update(self):
        if self._cur_interpolation is not None:
            self._cur_interpolation.update()
            if self._cur_interpolation.is_end():
                self._cur_interpolation = None
        else:
            return


class ChangeColor(Effect):
    def __init__(self, surface: pygame.Surface, end_color, start_color=None, duration=30, interpolation=Linear):
        """Gradient animation effect. Solid color surfaces only."""
        # 调用父类初始化
        super().__init__(surface, interpolation=interpolation)
        if start_color is None:
            self.start_color = self._surface.get_at((0, 0))
        else:
            self.start_color = tuple(start_color)
        self.end_color = tuple(end_color)
        self.duration = duration
        self.interpolation = interpolation

    def update(self):
        super().update()
        if self._cur_interpolation is None:
            return
        t = self._cur_interpolation.get()
        current_color = (
            int(self.start_color[0] * (1 - t) + self.end_color[0] * t),
            int(self.start_color[1] * (1 - t) + self.end_color[1] * t),
            int(self.start_color[2] * (1 - t) + self.end_color[2] * t)
        )
        self._surface.fill(current_color)


class Shadow(Effect):
    def __init__(self, surface: pygame.Surface, offset: tuple[int, int], color=(0, 0, 0, 128), *args, **kwargs):
        """Generate a shadow below the surface, preserve enough padding for the source Surface,
         or the shadow will be trimmed.
         Note: Once the class is initialized, the shadow effect is generated. Calls to the method "update"
         with "Forced=True" will apply the effect one more time, which may be unexpected"""
        super().__init__(surface, *args, **kwargs)
        self._offset = offset
        self._color = color
        self._shadow_cache = self._generate_shadow()
        self._prev_surf = self._surface.copy()
        self.update(forced=True)

    def _generate_shadow(self) -> pygame.Surface:
        """generate a semi transparent shadow surface."""
        shadow_surf = pygame.mask.from_surface(self._surface, 127)
        shadow_surf = shadow_surf.to_surface(setcolor=self._color, unsetcolor=(0, 0, 0, 0))
        return shadow_surf

    def update(self, forced=False):
        """blit the shadow surface. Call the function multiple times will darken the shadow"""
        if forced:
            self._prev_surf = self._surface.copy()
            self._generate_shadow()
            ts = self._surface.copy()
            self._surface.fill((0, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self._surface.blit(self._shadow_cache, self._offset)
            self._surface.blit(ts, (0, 0))


class Fade(Effect):
    def __init__(self, surface, duration=30, interpolation=Linear):
        """Fade effect on a surface."""
        super().__init__(surface, duration=duration, interpolation=interpolation)
        self._original = self._surface.copy()

    def update(self):
        super().update()
        if self._cur_interpolation is None:
            return
        self._surface.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_SUB)
        self._surface.blit(self._original, (0, 0))

        self._surface.fill((255, 255, 255, round(self._cur_interpolation.get() * 255)),
                           special_flags=pygame.BLEND_RGBA_MULT)


class RoundMaskFade(Effect):
    def __init__(self, surface, duration=30, center=None, interpolation=Linear):
        super().__init__(surface, duration=duration, interpolation=interpolation)
        w, h = surface.get_size()
        if center is None:
            center = w // 2, h // 2
        self.center = center
        self._max_r = max(math.sqrt(center[0] ** 2 + center[1] ** 2),
                          math.sqrt(center[0] ** 2 + (h - center[1]) ** 2),
                          math.sqrt((w - center[0]) ** 2 + center[1] ** 2),
                          math.sqrt((w - center[0]) ** 2 + (h - center[1]) ** 2)) * 1.2
        self._original = self._surface.copy()
        self._mask_surf = pygame.Surface(self._original.get_size(), pygame.SRCALPHA)

    def update(self):
        super().update()
        if self._cur_interpolation is None:
            return
        self._mask_surf.fill((255, 255, 255, 0))
        pygame.draw.circle(self._mask_surf, (255, 255, 255, 255), self.center,
                           self._cur_interpolation.get() * self._max_r)
        self._surface.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_SUB)
        self._surface.blit(self._original, (0, 0))
        self._surface.blit(self._mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


def update_effects():
    """An important callback that updates all effects.
    Should be called every frame after the background is refreshed, and
    before any of the surface is drawn on the screen."""
    for effect_ref in _all_effects:
        try:
            effect_ref().update()
        except AttributeError:
            _all_effects.remove(effect_ref)


if __name__ == '__main__':
    import sys
    import random
    from Resources import title

    # 测试用的窗口，可以在里面塞各种想要测试的代码
    pygame.init()
    screen = pygame.display.set_mode((600, 800), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    color_anim = ChangeColor(screen, end_color=(255, 128, 0), duration=30)
    icon = pygame.transform.smoothscale_by(title, 0.2)
    icon_o = icon.copy()
    shadow_eff = Shadow(icon, (10, 10))
    fade_anim = RoundMaskFade(icon, duration=60, interpolation=Quad)

    loopvar = 0
    altvar = 1

    fade_anim.animate_now(initial_phase=1 if altvar == -1 else 0, direction=altvar)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                    pass

        # 每循环调用的代码
        screen.fill(screen.get_at((0, 0)))
        update_effects()

        screen.blit(icon, (150, 100))
        # 标题阴影时而正常时而变黑，是因为当ChangeColor不更新时，屏幕不每帧刷新，每次blit不会清理上次的标题，半透明阴影产生重叠

        loopvar = (loopvar + 1) % 180
        if loopvar == 0:
            pass
            color_anim = ChangeColor(
                screen,
                end_color=(random.randint(0, 255),
                           random.randint(0, 255),
                           random.randint(0, 255)),
                duration=30)
            color_anim.animate_now()
        if loopvar == 80:
            altvar = -altvar
            icon = icon_o.copy()
            shadow_eff = Shadow(icon, (10, 10))
            fade_anim = random.choice((Fade(icon, duration=10, interpolation=Quad),
                                       RoundMaskFade(icon, duration=10, interpolation=Linear)))
            fade_anim.animate_now(initial_phase=1 if altvar == -1 else 0, direction=altvar)

        pygame.display.flip()
        clock.tick(60)
