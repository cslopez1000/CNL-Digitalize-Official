#version 460 core
layout(location = 0) in vec2 position;
out float ndcY;
void main() { ndcY = position.y; gl_Position = vec4(position, 0.0, 1.0); }
