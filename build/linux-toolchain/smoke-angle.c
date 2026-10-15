#include <EGL/egl.h>
#include <GLES2/gl2.h>
int main(void) { EGLDisplay d = eglGetDisplay(EGL_DEFAULT_DISPLAY); EGLint a,b; if (!eglInitialize(d,&a,&b)) return 1; glClear(GL_COLOR_BUFFER_BIT); return eglTerminate(d) ? 0 : 2; }
