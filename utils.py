import math
import pyray as rl

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
) -> int:  
    # find t
    a = p0.y - 2*p1.y + p2.y
    b = 2*p1.y - 2*p0.y
    c = p0.y - pixel.y

    if a == 0:
        return [], False

    factor = b**2 - 4*a*c
    if factor < 0:
        return [], False
    
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

    # if factor == 0:
    #     count = 1

    if count == 1:
        x = x1 or x2
        return [rl.Vector2(int(x), int(pixel.y))], check_if_on_transition(p0, p1, p2, pixel)
    
    if count == 2:
        return [rl.Vector2(int(x1), int(pixel.y)), rl.Vector2(x2, int(pixel.y))], check_if_on_transition(p0, p1, p2, pixel)
    
    return [], False

# if __name__ == "__main__":
#     p0 = rl.Vector2(-4, 2)
#     p2 = rl.Vector2(8, 0.5)
#     p1 = rl.Vector2(-0.97, 6.22)
#     pixel = rl.Vector2(0, 3)
#     r = check_if_intersects_bezier(
#         p0, p1, p2, pixel
#     )

#     print(r)