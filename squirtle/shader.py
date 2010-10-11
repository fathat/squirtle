from pyglet.graphics import *
from pyglet.gl import *
import ctypes

activeShader = None

class Shader(object):
    """An OpenGL shader object"""
    def __init__( self, shader_type, name="(unnamed shader)" ):
        self.shaderObject = glCreateShaderObjectARB( shader_type )
        self.name = name
        self.program = None
    
    def __del__ (self ):
        if self.program:
            self.program.detachShader( self )
            self.program = None
        
        glDeleteShader( self.shaderObject )
    
    def source( self, source_string ):
        c = ctypes
        buff = c.create_string_buffer(source_string)
        c_text = c.cast(c.pointer(c.pointer(buff)),
                        c.POINTER(c.POINTER(GLchar))) 
        glShaderSourceARB( self.shaderObject, 1, c_text, None )
    
    def compileShader( self ):
        glCompileShader( self.shaderObject )
        rval = ctypes.c_long()
        glGetObjectParameterivARB (self.shaderObject, GL_OBJECT_COMPILE_STATUS_ARB, ctypes.pointer(rval))
        if rval:
            print "%s compiled successfuly." % (self.name)
        else:
            print "Compile failed on shader %s: " % (self.name)
            self.printInfoLog( ) 
    
    
    def infoLog( self ):
        c = ctypes
        infoLogLength = c.c_long()
        glGetObjectParameterivARB(self.shaderObject,
                                  GL_OBJECT_INFO_LOG_LENGTH_ARB,
                                  ctypes.pointer(infoLogLength))
        buffer = c.create_string_buffer(infoLogLength.value)
        c_text = c.cast(c.pointer(buffer),
                        c.POINTER(GLchar)) 
        glGetInfoLogARB (self.shaderObject, infoLogLength.value, None, c_text)
        return c.string_at(c_text)
    
    def printInfoLog( self ):
        print self.infoLog()

class UniformVar(object):
    def __init__(self, set_function, name, *args ):
        self.setFunction = set_function
        self.name = name
        self.values = args
    
    def set(self):
        self.setFunction( self.name, *self.values )

class Program( object ):
    """An OpenGL shader program"""
    def __init__(self):
        self.programObject = glCreateProgramObjectARB()
        self.shaders = []
        self.uniformVars = {}
    
    def __del__(self):
        glDeleteObjectARB( self.programObject) 
    
    def attachShader( self, shader ):
        self.shaders.append( shader )
        shader.program = self
        glAttachObjectARB( self.programObject, shader.shaderObject )
    
    def detachShader( self, shader ):
        self.shaders.remove( shader )
        glDetachObjectARB( self.programObject, shader.shaderObject )
        print "Shader detached"
    
    def link( self ):
        glLinkProgramARB( self.programObject )
    
    def use( self ):
        global activeShader
        activeShader = self
        glUseProgramObjectARB( self.programObject )
        self.setVars()
        
    
    def stop(self):
        global activeShader
        glUseProgramObjectARB( 0 )
        activeShader = None
    
        
    def uniformi( self, name, *args ):
        argf = {1 : glUniform1iARB,
                2 : glUniform2iARB,
                3 : glUniform3iARB,
                4 : glUniform4iARB}
        f = argf[len(args)]
        def _set_uniform( name, *args ):
            location = glGetUniformLocationARB( self.programObject, name )
            f(location, *args)
        self.uniformVars[name] = UniformVar(_set_uniform, name, *args )
        if self == activeShader:
            self.uniformVars[name].set()      
    
    def uniformf( self, name, *args ):
        argf = {1 : glUniform1fARB,
                2 : glUniform2fARB,
                3 : glUniform3fARB,
                4 : glUniform4fARB}
        f = argf[len(args)]
        def _set_uniform( name, *args ):
            location = glGetUniformLocationARB( self.programObject, name )
            f(location, *args)
        self.uniformVars[name] = UniformVar(_set_uniform, name, *args )
        if self == activeShader:
            self.uniformVars[name].set()
    
    def uniformMatrixf(self, name, transpose, values):
        argf = {4 : glUniformMatrix2fvARB,
                9 : glUniformMatrix3fvARB,
                16 : glUniformMatrix4fvARB}
        f = argf[len(values)]
        def _set_uniform( name, values ):
            location = glGetUniformLocationARB( self.programObject, name )
            matrix_type = ctypes.c_float * len(values)
            matrix = matrix_type(*values)
            f(location, 1, transpose, cast(matrix, ctypes.POINTER(ctypes.c_float) ))
        self.uniformVars[name] = UniformVar(_set_uniform, name, values )
        if self == activeShader:
            self.uniformVars[name].set()
    
    def setVars(self):
        for name, var in self.uniformVars.iteritems():
            var.set()
    
    def printInfoLog( self ):
        print glGetInfoLogARB (self.programObject )


def MakePixelShaderFromSource ( src ):
    return MakeShaderFromSource( src, GL_FRAGMENT_SHADER_ARB )

def MakeVertexShaderFromSource ( src ):
    return MakeShaderFromSource( src, GL_VERTEX_SHADER_ARB )

def MakeShaderFromSource( src, shader_type ):
    shader =  Shader( shader_type )
    shader.source( src )
    shader.compileShader()
    return shader

def MakeProgramFromSourceFiles( vertex_shader_name, pixel_shader_name ):
    file = open( vertex_shader_name, "r")
    vs_src = file.tostring()
    file.close()
    file = open( pixel_shader_name, "r")
    ps_src = file.tostring()
    file.close()
    return MakeProgramFromSource( vs_src, ps_src )

def MakeProgramFromSource( vertex_shader_src, pixel_shader_src ):
    vs = MakeVertexShaderFromSource( vertex_shader_src )
    ps = MakePixelShaderFromSource ( pixel_shader_src )
    
    p = Program()
    p.attachShader( vs )
    p.attachShader( ps )
    p.link()
    p.use()
    return p

def DisableShaders():
    global activeShader 
    glUseProgramObjectARB( 0 )
    activeShader = None
