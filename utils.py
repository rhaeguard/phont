import math
import pyray as rl

class GlyphContour:
    def __init__(
        self,
        segments: list[list[tuple[int, int]]]
    ) -> None:
        self.segments = segments
        self.polylines: list[rl.Vector2] = []


def check_if_intersects_line(
    p0: rl.Vector2, 
    p1: rl.Vector2, 
    pixel: rl.Vector2,   
) -> list[rl.Vector2]:
    if p1.y - p0.y == 0:
        if pixel.y == p1.y:
            if p0.x > p1.x:
                return [rl.Vector4(p1.x, p1.y, p0.x, p0.y)]
            return [rl.Vector4(p0.x, p0.y, p1.x, p1.y)]
        return []
    
    t = (pixel.y - p0.y) / (p1.y - p0.y)
    if t >= 0 and t <= 1:
        x = t * p1.x + (1-t) * p0.x
        return [rl.Vector2(x, pixel.y)]
    return []


def check_if_intersects_bezier(
    p0: rl.Vector2, 
    p1: rl.Vector2, # control
    p2: rl.Vector2, 
    pixel: rl.Vector2,
) -> list[rl.Vector2]:  
    # find t
    a = p0.y - 2*p1.y + p2.y
    b = 2*p1.y - 2*p0.y
    c = p0.y - pixel.y

    if a == 0:
        return check_if_intersects_line(p0, p2, pixel)

    factor = b**2 - 4*a*c
    if factor < 0:
        return []
    
    factor = math.sqrt(factor)

    t1 = (-b + factor) / (2*a)
    t2 = (-b - factor) / (2*a)
    x1, x2 = None, None

    count = 0
    if t1 >= 0 and t1 <= 1:
        x1 = (1 - 2*t1 + t1**2) * p0.x + (2*t1 - 2*t1**2) * p1.x + p2.x * t1**2
        count += 1
    
    if t2 >= 0 and t2 <= 1:
        x2 = (1 - 2*t2 + t2**2) * p0.x + (2*t2 - 2*t2**2) * p1.x + p2.x * t2**2
        count += 1

    if count == 1:
        x = x1 or x2
        return [rl.Vector2(x, pixel.y)]
    
    if count == 2:
        if factor == 0:
            return [rl.Vector2(x1, pixel.y)]
        else:
            return [rl.Vector2(x1, pixel.y), rl.Vector2(x2, pixel.y)]
    return []


def v4_to_v2s(v4) -> tuple[rl.Vector2, rl.Vector2]:
    return (rl.Vector2(v4.x, v4.y), rl.Vector2(v4.z, v4.w))


def is_v2(v):
    return "Vector2" in str(v)


def v2_to_string(v) -> str:
    if is_v2(v):
        return f"({round(v.x, ndigits=3)}, {round(v.y, ndigits=3)})"
    return f"({round(v.x, ndigits=3)}, {round(v.y, ndigits=3)}, {round(v.z, ndigits=3)}, {round(v.w, ndigits=3)})"


def sign(value):
    if value == 0:
        return 0
    return -1 if value < 0 else 1