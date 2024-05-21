#version 330

#define MAX_POLYLINE_COUNT 20

in vec2 fragTexCoord;

uniform sampler2D texture0;

uniform vec3 color;
uniform vec2 offset;
uniform vec2 polylines[MAX_POLYLINE_COUNT*MAX_POLYLINE_COUNT]; // each contour has a set of polylines
uniform int count_contour;
uniform int count_polyline;

out vec4 finalColor;

float isLeft(vec2 P0, vec2 P1, vec2 P2) {
    /*
    Using cross product to find if the point is in CW or CCW direction compared to the line
    */
    return (P1.x - P0.x) * (P2.y - P0.y) - (P2.x -  P0.x) * (P1.y - P0.y);
}

int polygonWindingNumber(vec2 point, int contour) {
    int windingNumber = 0;

    for (int p=0; p < count_polyline-1; p++) {
        vec2 a = polylines[contour * count_polyline + p];
        vec2 b = polylines[contour * count_polyline + p + 1];
        if (b.x == -666) {
            break;
        }

        if (a.y <= point.y) {
            if (b.y > point.y) {
                if (isLeft(a, b, point) > 0) {
                    windingNumber += 1;
                }
            }
        } else {
            if (b.y <= point.y) {
                if (isLeft(a, b, point) < 0) {
                    windingNumber -= 1;
                }
            }
        }
    }

    return windingNumber;
}

void main()
{
    ivec2 dimensions = textureSize(texture0, 0);
    vec2 realCoords = floor(fragTexCoord * dimensions + offset);

    float alpha = 0.0;

    for (float sy=0.25; sy < 1.0; sy += 0.25) {
        for (float sx=0.25; sx < 1.0; sx += 0.25) {
            vec2 point = realCoords + vec2(sx, sy);
            int windingNumber = 0;
            for (int c=0; c < count_contour; c++) {
                windingNumber += polygonWindingNumber(point, c);
            }
            if (windingNumber != 0) {
                alpha += 0.111;
            }
        }
    }

    finalColor = vec4(color, alpha);
}