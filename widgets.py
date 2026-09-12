"""
A simple widget module for pygame.

The skeleton is written by ZCR, and implementations are written by ZYY.
"""
import pygame


class Widget(pygame.Surface):
    def __new__(cls, *args, **kwargs):
        return pygame.Surface(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raise NotImplementedError

    def draw(self, surface):
        raise NotImplementedError

    def update(self, delta):
        raise NotImplementedError

class Animation:
    def __init__(self, surface):
        pass