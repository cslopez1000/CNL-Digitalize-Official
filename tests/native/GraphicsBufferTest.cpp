#include "../../source/Engine/Graphics/OpenGL/Objects.hpp"
#include <stdexcept>
#include <iostream>
namespace {
int allocations=0,updates=0,deletes=0; GLsizeiptr allocated=0;
void APIENTRY Create(GLsizei,GLuint* id) { *id=42; }
void APIENTRY Allocate(GLuint,GLsizeiptr bytes,const void*,GLenum) { ++allocations; allocated=bytes; }
void APIENTRY Update(GLuint,GLintptr offset,GLsizeiptr bytes,const void*) { if(offset || bytes>allocated) throw std::runtime_error("Out-of-bounds upload"); ++updates; }
void APIENTRY Delete(GLsizei,const GLuint*) { ++deletes; }
void Check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
}
int main() {
    glad_glCreateBuffers=Create; glad_glNamedBufferData=Allocate; glad_glNamedBufferSubData=Update; glad_glDeleteBuffers=Delete;
    crocker::engine::gl::Buffer b; float data[200]{};
    b.Upload(nullptr,0); Check(allocations==0,"Empty VAO initialization must not allocate storage");
    b.Upload(data,64); b.Upload(data,128); b.Upload(data,32);
    Check(allocations==1 && updates==3,"Small draws reuse storage");
    b.Upload(data,sizeof(data)); Check(allocations==2,"Larger draw grows storage");
    b.Release(); b.Release(); Check(deletes==1 && b.capacity==0 && b.id==0,"Release is idempotent and resets capacity");
    b.Upload(data,64); Check(allocations==3,"Context recreation allocates fresh storage"); b.Release();
    std::cout<<"Mock GL: buffer reuse, growth, bounds and context recreation passed\n";
}
