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
) -> bool:
    return False

def check_if_on_transition(
    p0: rl.Vector2, 
    p1: rl.Vector2, # control
    p2: rl.Vector2,
    pixel: rl.Vector2,
) -> bool:
    """
    it is counter-clockwise if:
    - p0.y > p1.y
    - if above is the same, p0.x > p1.x

    it is clockwise if:
    - p0.y < p1.y
    - if above is the same, p0.x < p1.x
    """
    is_counter_clockwise = False
    if p0.y >= p1.y:
        if p0.y == p1.y:
            is_counter_clockwise = p0.x > p1.x
        else:
            is_counter_clockwise = True
    return is_counter_clockwise

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
        p0 = p0
        p1 = p2
        if p1.y - p0.y == 0:
            return []
        
        t = (pixel.y - p0.y) / (p1.y - p0.y)
        if t >= 0 and t <= 1:
            x = t * p1.x + (1-t) * p0.x
            if x >= pixel.x:
                return [rl.Vector2(x, pixel.y)]
        return []

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
    """
    p0 = rl.Vector2(1028.0,516.0)
    p1 = rl.Vector2(1030.0,510.0)
    p2 = rl.Vector2(1030.0,504.0)
    pixel = rl.Vector2(1000, 508.7)

    p0 = rl.Vector2(1030.0,504.0)
    p1 = rl.Vector2(1030.0,498.0)
    p2 = rl.Vector2(1030.0,492.0)
    pixel = rl.Vector2(1000, 496.7)

    r = check_if_intersects_bezier(
        p0, p1, p2, pixel
    )

    for vv in r:
        print(vv.x, vv.y)