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

if __name__ == "__main__":
    """
(165.271, 616.0) ['(155.0, 669.0)', '(155.0, 625.0)', '(178.0, 594.0)'] (165.0, 616.0)
(237.921, 616.0) ['(251.0, 579.0)', '(235.0, 605.0)', '(235.0, 653.0)'] (165.0, 616.0)
(423.828, 616.0) ['(431.0, 627.0)', '(414.0, 599.0)', '(387.0, 575.0)'] (165.0, 616.0)
(526.202, 616.0) ['(512.0, 578.0)', '(529.0, 607.0)', '(529.0, 646.0)'] (165.0, 616.0)


(237.747, 617.0) ['(251.0, 579.0)', '(235.0, 605.0)', '(235.0, 653.0)'] (165.0, 617.0)
(424.522, 617.0) ['(431.0, 627.0)', '(414.0, 599.0)', '(387.0, 575.0)'] (165.0, 617.0)
(526.395, 617.0) ['(512.0, 578.0)', '(529.0, 607.0)', '(529.0, 646.0)'] (165.0, 617.0)

(237.58, 618.0) ['(251.0, 579.0)', '(235.0, 605.0)', '(235.0, 653.0)'] (165.0, 618.0)
(425.207, 618.0) ['(431.0, 627.0)', '(414.0, 599.0)', '(387.0, 575.0)'] (165.0, 618.0)
(526.581, 618.0) ['(512.0, 578.0)', '(529.0, 607.0)', '(529.0, 646.0)'] (165.0, 618.0)
    """

    p0 = rl.Vector2(155.0, 669.0)
    p1 = rl.Vector2(155.0, 625.0)
    p2 = rl.Vector2(178.0, 594.0)
    pixel = rl.Vector2(165.0, 618.0)
    # pixel = rl.Vector2(165.0, 616.0)

    r = check_if_intersects_bezier(
        p0, p1, p2, pixel
    )

    for vv in r:
        if vv is None:
            print("None!")
        else:
            print(vv.x, vv.y)