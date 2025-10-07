# Stub file for scipy.optimize
# This is to help PyRight resolve scipy.optimize imports

from typing import Any, Callable

def fsolve(func: Callable[..., Any], x0: Any, args: tuple[Any, ...] = (), **kwargs: Any) -> Any: ...
def brentq(f: Callable[[float], float], a: float, b: float, **kwargs: Any) -> float: ...