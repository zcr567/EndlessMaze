"""
Low-level tool functions that all modules may use.
Author: ZCR
"""
from os.path import abspath
import sys


def resource_path(relative_path):
    """get the packaged resource directory (from previous projects, tested OK)"""
    if hasattr(sys, '_MEIPASS'):
        # packaged env
        # noinspection PyProtectedMember
        base_path = str(sys._MEIPASS)
    else:
        # development env
        base_path = abspath(".")
    return base_path + '/' + relative_path
