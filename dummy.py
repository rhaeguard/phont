def midpoint(a: rl.Vector2, b: rl.Vector2) -> rl.Vector2:
    s = rl.vector2_add(a, b)
    return rl.vector2_scale(s, 0.5)

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