"""
    Mock implementation of sonic_platform package for unit testing
"""

from sonic_platform_base.psu_base import PsuBase


class Psu(PsuBase):
    def __init__(self):
        super(PsuBase, self).__init__()
