from __future__ import annotations
import functools
from typing import Callable

class LockableUI:
    _point_controls_locked: int = 0
    
    @staticmethod
    def _takes_lock(fn: Callable):
        @functools.wraps(fn)
        def wrapper(self: LockableUI, *args, **kwargs):
            self._point_controls_locked += 1
            res = fn(self, *args, **kwargs)
            self._point_controls_locked -= 1
            return res
        return wrapper
    
    @staticmethod
    def _no_lock(fn: Callable):
        @functools.wraps(fn)
        def wrapper(self: LockableUI, *args, **kwargs):
            if self._point_controls_locked:
                return
            return fn(self, *args, **kwargs)
        return wrapper
