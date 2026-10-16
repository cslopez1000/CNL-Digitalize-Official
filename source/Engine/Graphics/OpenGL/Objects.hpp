#pragma once
#include <glad/glad.h>
#include <cstddef>
#include <algorithm>
#include <limits>
#include <stdexcept>
namespace crocker::engine::gl {
// Handles are released by RenderContext::Release while its context is current.
// They deliberately make no GL calls from uncontrolled static/destructor order.
struct Buffer {
    GLuint id = 0;
    std::size_t capacity = 0;
    void Upload(const void* data, std::size_t bytes) {
        if (bytes > static_cast<std::size_t>(std::numeric_limits<GLsizeiptr>::max()))
            throw std::length_error("OpenGL buffer exceeds addressable size");
        if (!id) glCreateBuffers(1, &id);
        // Retain storage between draws. Grow geometrically to avoid reallocating
        // for every grid/curve/label. SubData remains synchronized by the driver;
        // do not use unsynchronized mapping without fences.
        if (bytes > capacity) {
            const auto limit = static_cast<std::size_t>(std::numeric_limits<GLsizeiptr>::max());
            const auto grown = capacity <= limit / 2 ? capacity * 2 : limit;
            capacity = std::max(bytes, std::max(std::size_t{256}, grown));
            glNamedBufferData(id, static_cast<GLsizeiptr>(capacity), nullptr, GL_DYNAMIC_DRAW);
        }
        if (bytes && data) glNamedBufferSubData(id, 0, static_cast<GLsizeiptr>(bytes), data);
    }
    void Release() { if (id) glDeleteBuffers(1, &id); id = 0; capacity = 0; }
};
struct VertexArray {
    GLuint id = 0;
    void Create() { if (!id) glCreateVertexArrays(1, &id); }
    void Release() { if (id) glDeleteVertexArrays(1, &id); id = 0; }
};
struct Texture2D {
    GLuint id = 0;
    void Release() { if (id) glDeleteTextures(1, &id); id = 0; }
};
}
