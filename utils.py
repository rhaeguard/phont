import math
import pyray as rl

class GlyphContour:
    def __init__(
        self,
        segments: list[list[tuple[int, int]]]
    ) -> None:
        self.segments = segments
        self.is_clockwise = None
        self.segment_vectors: list[list[rl.Vector2]] = []
        self.segment_directions: list[bool] = [] # is clockwise?


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
        if x >= pixel.x:
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
        if x1 >= pixel.x:
            count += 1
        else:
            x1 = None
    
    if t2 >= 0 and t2 <= 1:
        x2 = (1 - 2*t2 + t2**2) * p0.x + (2*t2 - 2*t2**2) * p1.x + p2.x * t2**2
        if x2 >= pixel.x:
            count += 1
        else:
            x2 = None

    if count == 1:
        x = x1 or x2
        return [rl.Vector2(x, pixel.y)]
    
    if count == 2:
        if factor == 0:
            return [rl.Vector2(x1, pixel.y)]
        else:
            return [rl.Vector2(x1, pixel.y), rl.Vector2(x2, pixel.y)]
    
    return []

if __name__ == "__main__":
    """
    ['[1028.0,516.0]', '[1030.0,510.0]', '[1030.0,504.0]']
    ['[1030.0,504.0]', '[1030.0,498.0]', '[1030.0,492.0]']

    ['[757.0,400.0]', '[756.0,389.0]', '[751.0,390.0]']
    ['[751.0,390.0]', '[746.0,390.0]', '[741.0,400.0]']

    ['147.0 - [153.0,512.0][153.0,512.0][147.0,512.0]', '153.0 - [153.0,512.0][153.0,512.0][147.0,512.0]'] skip
    ['280.0 - [280.0,464.0][280.0,464.0][394.0,464.0]', '394.0 - [280.0,464.0][280.0,464.0][394.0,464.0]'] skip
    ['295.0 - [394.0,512.0][394.0,512.0][295.0,512.0]', '394.0 - [394.0,512.0][394.0,512.0][295.0,512.0]'] skip
    """
    p0 = rl.Vector2(1028.0,516.0)
    p1 = rl.Vector2(1030.0,510.0)
    p2 = rl.Vector2(1030.0,504.0)
    pixel = rl.Vector2(1000, 508.7)

    p0 = rl.Vector2(1030.0,504.0)
    p1 = rl.Vector2(1030.0,498.0)
    p2 = rl.Vector2(1030.0,492.0)
    pixel = rl.Vector2(1000, 496.7)

    p0 = rl.Vector2(751.0,390.0)
    p1 = rl.Vector2(746.0,390.0)
    p2 = rl.Vector2(741.0,400.0)
    pixel = rl.Vector2(700, 390)

    p0 = rl.Vector2(757.0,400.0)
    p1 = rl.Vector2(756.0,389.0)
    p2 = rl.Vector2(751.0,390.0)
    pixel = rl.Vector2(700, 390)

    p0 = rl.Vector2(280.0,464.0, 280.0,464.0, 394.0,464.0)
    p1 = rl.Vector2(280.0,464.0)
    p2 = rl.Vector2(394.0,464.0)
    pixel = rl.Vector2(0, 464)

    r = check_if_intersects_bezier(
        p0, p1, p2, pixel
    )

    for vv in r:
        if vv is None:
            print("None!")
        else:
            print(vv.x, vv.y)