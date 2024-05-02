import math
import pyray as rl

def should_skip_segment(data: list[rl.Vector2], pixel: rl.Vector2) -> bool:
    y_min = data[0].y
    y_max = data[0].y
    x_max = data[0].x
    for v in data:
        y_min = min(y_min, v.y)
        y_max = max(y_max, v.y)
        x_max = max(x_max, v.x)
    print(y_min, y_max, x_max, pixel.x, pixel.y)
    print(y_min > pixel.y, y_max < pixel.y, x_max < pixel.x)
    return y_min > pixel.y or y_max < pixel.y or x_max < pixel.x

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

    # print(t1, t2, factor, a, b, c)

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

if __name__ == "__main__":
    """
(148.0, 787.0)   ['(148.0, 787.0)', '(156.0, 776.0)', '(166.0, 768.0)'] (150.0, 787.0)

(234.537, 788.0) ['(223.0, 779.0)', '(236.0, 790.0)', '(253.0, 800.0)'] (150.0, 788.0)
(372.996, 788.0) ['(368.0, 791.0)', '(401.0, 772.0)', '(422.0, 739.0)'] (150.0, 788.0)
(435.718, 788.0) ['(441.0, 784.0)', '(401.0, 815.0)', '(351.0, 832.0)'] (150.0, 788.0)

['(140.0, 805.0)', '(140.0, 798.0)', '(148.0, 787.0)']
    """

    p0 = rl.Vector2(140.0, 805.0)
    p1 = rl.Vector2(140.0, 798.0)
    p2 = rl.Vector2(148.0, 787.0)
    pixel = rl.Vector2(150.0, 788.0)
    # pixel = rl.Vector2(165.0, 616.0)

    r = check_if_intersects_bezier(
        p0, p1, p2, pixel
    )

    for vv in r:
        if vv is None:
            print("None!")
        else:
            print(vv.x, vv.y)

    print(should_skip_segment([p0, p1, p2], pixel))