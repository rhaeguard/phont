#version 330

uniform vec2 pixelCoord;

void main()
{
    gl_Position = vec4(pixelCoord, 0.0, 0.0);
}