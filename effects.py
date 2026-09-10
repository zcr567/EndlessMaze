"""
Simple property adjustments & animated effects for pygame surfaces.

The skeleton is written by ZCR, and implementations are written by ZYY.
"""

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
        if 0 < value < 1:
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
    def update(self):
        raise NotImplementedError
        # TODO: implement the function


class ReversedQuad(Interpolation):
    # Quad 的图像中心对称， 先快后慢
    def update(self):
        raise NotImplementedError
        # TODO: implement the function


class DoubleQuad(Interpolation):
    # 双二次函数，平滑变换（本来想用sin，但是开销有点大）
    def update(self):
        raise NotImplementedError
        # TODO: implement the function


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


class ChangeColor(Effect):
    def __init__(self, surface: pygame.Surface, color, interpolation=Linear):
        super(ChangeColor, self).__init__(surface, interpolation=interpolation)
        self.color = color

    def update(self):
        raise NotImplementedError
        # TODO: implement the function
