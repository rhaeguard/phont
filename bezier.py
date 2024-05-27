import pyray as rl

def bezier_flat_enough(p1: rl.Vector2, control: rl.Vector2, p2: rl.Vector2) -> bool:
    """
    if the control point is close enough to the line, curve is considered flat.

    Reference: https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line#Line_defined_by_two_points

    Quick explanation: 
        - Cross product of 2 vectors gives us the parallelogram enclosed by those vectors.
        - The distance from control point to the line is the altitude
        - Cross_Product_Area = Line_Distance * Altitude => Altitude = Cross_Product_Area / Line_Distance
    """
    
    dist = rl.vector_2distance(p1, p2)
    if dist == 0.0:
        return True
    
    cross_product = abs(
        (p2.x - p1.x)*(control.y - p1.y) - (control.x - p1.x) * (p2.y - p1.y)
    )

    altitude = cross_product / dist
    return altitude <= 1

def midpoint(a: rl.Vector2, b: rl.Vector2) -> rl.Vector2:
    return rl.Vector2(
        (a.x + b.x) / 2,
        (a.y + b.y) / 2
    )

def produce_bezier_lines(
    p0: rl.Vector2,
    p1: rl.Vector2,
    p2: rl.Vector2,
) -> list[rl.Vector2]:
    if bezier_flat_enough(p0, p1, p2):
        return [p0, p2]
    else:
        m1 = midpoint(p0, p1)
        m2 = midpoint(p1, p2)
        m3 = midpoint(m1, m2)

        a = produce_bezier_lines(p0, m1, m3)
        b = produce_bezier_lines(m3, m2, p2)
        return a + b
