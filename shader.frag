#version 330

#define MAX_POLYLINE_COUNT 20

in vec2 fragTexCoord;

uniform sampler2D texture0;

uniform vec2 offset;
uniform vec2 polylines[MAX_POLYLINE_COUNT*MAX_POLYLINE_COUNT]; // each contour has a set of polylines
uniform int count_contour;
uniform int count_polyline;

out vec4 finalColor;

float isLeft(vec2 P0, vec2 P1, vec2 P2) {
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
    vec2 realCoords = fragTexCoord * dimensions + offset;

    int windingNumber = 0;
    for (int c=0; c < count_contour; c++) {
        windingNumber += polygonWindingNumber(realCoords, c);
    }

    if (windingNumber == 0) {
        discard;
    } else {
        finalColor = vec4(1.0, 0.0, 0.0, 1.0);
    }
}