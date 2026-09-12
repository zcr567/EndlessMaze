"""
Simple property adjustments & animated effects for pygame surfaces.

The skeleton is written by ZCR, and implementations are written by ZYY.
"""
import sys

import pygame


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
        self._phase = initial_phase
        self.direction = direction
        self.step = step

    def clear(self):
        self._phase = 0

    def set(self, value: int | float):
        if 0 <= value <= 1:
            self._phase = value
        else:
            raise ValueError("parameter 'value' must be between 0 and 1.")

    def get(self):
        return self._phase

    def switch(self):
        self.direction = -self.direction

    def update(self):
        raise NotImplementedError


class Linear(Interpolation):
    # 这个已经写好了，可供参考
    def update(self):
        self._phase = trim(self._phase + 1 / self.step * self.direction)
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
        self._current_step = trim(self._current_step + self.direction, 0, self.step)
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
        self._current_step = trim(self._current_step + self.direction, 0, self.step)
        t = self._current_step / self.step
        self._phase = 1 - (1 - t) ** 2
        return self._phase

class DoubleQuad(Interpolation):
    #双二次平滑：用Smoothstep = t²(3 - 2t)近似sin

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
        self._current_step = trim(self._current_step + self.direction, 0, self.step)
        t = self._current_step / self.step
        self._phase = t * t * (3 - 2 * t)
        return self._phase



class Effect:
    def __init__(self, surface: pygame.Surface, *args, interpolation=Linear, **kwargs):
        self.surface = surface
        self.interpolation = interpolation
        self._cur_interpolation = None

    def animate_now(self, step: int, initial_phase: int | float = 0, direction: int = 1):
        self._cur_interpolation = self.interpolation(step, initial_phase, direction)

    def update(self):
        if self._cur_interpolation is not None:
            self._cur_interpolation.update()
        else:
            return


# 可以把动画持续时间也放到形参
class ChangeColor(Effect):
    def __init__(self, surface: pygame.Surface, color, interpolation=Linear):
        super(ChangeColor, self).__init__(surface, interpolation=interpolation)
        self.color = color

    def update(self):
        raise NotImplementedError
        # TODO: implement the function


if __name__ == '__main__':
    # 测试用的窗口，可以在里面塞各种想要测试的代码
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    # 初始化

    # 初始化
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        # 每循环调用的代码

        # 每循环调用的代码
