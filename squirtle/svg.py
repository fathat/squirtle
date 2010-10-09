"""Squirtle mini-library for SVG rendering in Pyglet.

Example usage:
    import squirtle
    my_svg = squirtle.SVG('filename.svg')
    my_svg.draw(100, 200, angle=15)
    
"""

from pyglet.gl import *
try:
    import xml.etree.ElementTree
    from xml.etree.cElementTree import parse
except:
    import elementtree.ElementTree
    from elementtree.ElementTree import parse
import re
import math
from ctypes import CFUNCTYPE, POINTER, byref, cast, c_char_p
import sys
import string
import shader
import ctypes

from matrix import *
from parse import *
from gradient import *

print  cast(glGetString(GL_SHADING_LANGUAGE_VERSION), c_char_p).value

tess = gluNewTess()
gluTessNormal(tess, 0, 0, 1)
gluTessProperty(tess, GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_NONZERO)

if sys.platform == 'win32':
    from ctypes import WINFUNCTYPE
    c_functype = WINFUNCTYPE
else:
    c_functype = CFUNCTYPE
    
callback_types = {GLU_TESS_VERTEX: c_functype(None, POINTER(GLvoid)),
                  GLU_TESS_BEGIN: c_functype(None, GLenum),
                  GLU_TESS_END: c_functype(None),
                  GLU_TESS_ERROR: c_functype(None, GLenum),
                  GLU_TESS_COMBINE: c_functype(None, POINTER(GLdouble), POINTER(POINTER(GLvoid)), POINTER(GLfloat), POINTER(POINTER(GLvoid)))}

def set_tess_callback(which):
    def set_call(func):
        cb = callback_types[which](func)
        gluTessCallback(tess, which, cast(cb, CFUNCTYPE(None)))
        return cb
    return set_call
    
BEZIER_POINTS = 20
CIRCLE_POINTS = 24
TOLERANCE = 0.001

def setup_gl():
    """Set various pieces of OpenGL state for better rendering of SVG.
    
    """
    glEnable(GL_LINE_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


class SvgPath(object):
    def __init__(self, path, stroke, polygon, fill, transform, path_id, desc):
        self.path = path if path else []
        self.stroke = stroke
        self.polygon = polygon
        self.fill = fill
        self.transform = transform
        self.id = path_id
        self.description = desc
                               
class TriangulationError(Exception):
    """Exception raised when triangulation of a filled area fails. For internal use only."""
    pass

class SVG(object):
    """Opaque SVG image object.
    
    Users should instantiate this object once for each SVG file they wish to 
    render.
    
    """
    
    _disp_list_cache = {}
    def __init__(self, filename, anchor_x=0, anchor_y=0, bezier_points=BEZIER_POINTS, circle_points=CIRCLE_POINTS):
        """Creates an SVG object from a .svg or .svgz file.
        
            `filename`: str
                The name of the file to be loaded.
            `anchor_x`: float
                The horizontal anchor position for scaling and rotations. Defaults to 0. The symbolic 
                values 'left', 'center' and 'right' are also accepted.
            `anchor_y`: float
                The vertical anchor position for scaling and rotations. Defaults to 0. The symbolic 
                values 'bottom', 'center' and 'top' are also accepted.
            `bezier_points`: int
                The number of line segments into which to subdivide Bezier splines. Defaults to 10.
            `circle_points`: int
                The number of line segments into which to subdivide circular and elliptic arcs. 
                Defaults to 10.
                
        """
        self.paths = []
        self.filename = filename
        self.bezier_points = bezier_points
        self.circle_points = circle_points
        self.bezier_coefficients = []
        self.gradients = GradientContainer()
        self.generate_disp_list()
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y

    def _set_anchor_x(self, anchor_x):
        self._anchor_x = anchor_x
        if self._anchor_x == 'left':
            self._a_x = 0
        elif self._anchor_x == 'center':
            self._a_x = self.width * .5
        elif self._anchor_x == 'right':
            self._a_x = self.width
        else:
            self._a_x = self._anchor_x
    
    def _get_anchor_x(self):
        return self._anchor_x
    
    anchor_x = property(_get_anchor_x, _set_anchor_x)
    
    def _set_anchor_y(self, anchor_y):
        self._anchor_y = anchor_y
        if self._anchor_y == 'bottom':
            self._a_y = 0
        elif self._anchor_y == 'center':
            self._a_y = self.height * .5
        elif self._anchor_y == 'top':
            self._a_y = self.height
        else:
            self._a_y = self.anchor_y

    def _get_anchor_y(self):
        return self._anchor_y
        
    anchor_y = property(_get_anchor_y, _set_anchor_y)
    
    def generate_disp_list(self):
        if (self.filename, self.bezier_points) in self._disp_list_cache:
            self.disp_list, self.width, self.height = self._disp_list_cache[self.filename, self.bezier_points]
        else:
            if open(self.filename, 'rb').read(3) == '\x1f\x8b\x08': #gzip magic numbers
                import gzip
                f = gzip.open(self.filename, 'rb')
            else:
                f = open(self.filename, 'rb')
            self.tree = parse(f)
            self.parse_doc()
            self.disp_list = glGenLists(1)
            glNewList(self.disp_list, GL_COMPILE)
            self.render_slowly()
            glEndList()
            self._disp_list_cache[self.filename, self.bezier_points] = (self.disp_list, self.width, self.height)

    def draw(self, x, y, z=0, angle=0, scale=1):
        """Draws the SVG to screen.
        
        :Parameters
            `x` : float
                The x-coordinate at which to draw.
            `y` : float
                The y-coordinate at which to draw.
            `z` : float
                The z-coordinate at which to draw. Defaults to 0. Note that z-ordering may not 
                give expected results when transparency is used.
            `angle` : float
                The angle by which the image should be rotated (in degrees). Defaults to 0.
            `scale` : float
                The amount by which the image should be scaled, either as a float, or a tuple 
                of two floats (xscale, yscale).
        
        """
        glPushMatrix()
        glTranslatef(x, y, z)
        if angle:
            glRotatef(angle, 0, 0, 1)
        if scale != 1:
            try:
                glScalef(scale[0], scale[1], 1)
            except TypeError:
                glScalef(scale, scale, 1)
        if self._a_x or self._a_y:  
            glTranslatef(-self._a_x, -self._a_y, 0)
        glCallList(self.disp_list)
        glPopMatrix()

    def render_slowly(self):
        self.n_tris = 0
        self.n_lines = 0
        for svgpath in self.paths:
            path = svgpath.path
            stroke = svgpath.stroke
            tris = svgpath.polygon
            fill = svgpath.fill
            transform = svgpath.transform
            if tris:
                self.n_tris += len(tris)/3
                g = None
                if isinstance(fill, str):
                    g = self.gradients[fill]
                    fills = [g.interp(x) for x in tris]
                else:
                    fills = [fill for x in tris]
                
                glPushMatrix()
                glMultMatrixf(as_c_matrix(transform.to_mat4()))
                if g: g.apply_shader(transform)
                glBegin(GL_TRIANGLES)
                for vtx, clr in zip(tris, fills):
                    #vtx = transform(vtx)
                    if not g: glColor4ub(*clr)
                    else: glColor4f(1,1,1,1)
                    glVertex3f(vtx[0], vtx[1], 0)
                glEnd()
                glPopMatrix()
                if g: g.unapply_shader()
            if path:
                for loop in path:
                    self.n_lines += len(loop) - 1
                    loop_plus = []
                    for i in xrange(len(loop) - 1):
                        loop_plus += [loop[i], loop[i+1]]
                    if isinstance(stroke, str):
                        g = self.gradients[stroke]
                        strokes = [g.interp(x) for x in loop_plus]
                    else:
                        strokes = [stroke for x in loop_plus]
                    glPushMatrix()
                    glMultMatrixf(as_c_matrix(transform.to_mat4()))
                    glBegin(GL_LINES)
                    for vtx, clr in zip(loop_plus, strokes):
                        
                        #vtx = transform(vtx)
                        glColor4ub(*clr)
                        glVertex3f(vtx[0], vtx[1], 0)
                    glEnd()
                    glPopMatrix()
                                     
    def parse_float(self, txt):
        if txt.endswith('px'):
            return float(txt[:-2])
        else:
            return float(txt)
    

    def parse_doc(self):
        self.paths = []
        self.width = self.parse_float(self.tree._root.get("width", '0'))
        self.height = self.parse_float(self.tree._root.get("height", '0'))
        if self.height:
            self.transform = Matrix([1, 0, 0, 1, 0, 0])
        else:
            x, y, w, h = (self.parse_float(x) for x in parse_list(self.tree._root.get("viewBox")))
            self.transform = Matrix([1, 0, 0, 1, 0, 0])
            self.height = h
            self.width = w
        self.opacity = 1.0
        for e in self.tree._root.getchildren():
            try:
                self.parse_element(e)
            except Exception, ex:
                print 'Exception while parsing element', e
                raise
            
    def parse_element(self, e):
        default = object()
        self.fill = parse_color(e.get('fill'), default)
        self.stroke = parse_color(e.get('stroke'), default)
        oldopacity = self.opacity
        self.opacity *= float(e.get('opacity', 1))
        fill_opacity = float(e.get('fill-opacity', 1))
        stroke_opacity = float(e.get('stroke-opacity', 1))
        self.path_id = e.get('id', '')
        self.path_description = e.get('title', '')

        
        oldtransform = self.transform
        self.transform = self.transform * Matrix(e.get('transform'))
        
        style = e.get('style')
        if style:
            sdict = parse_style(style)
            if 'fill' in sdict:
                self.fill = parse_color(sdict['fill'])
            if 'fill-opacity' in sdict:
                fill_opacity *= float(sdict['fill-opacity'])
            if 'stroke' in sdict:
                self.stroke = parse_color(sdict['stroke'])
            if 'stroke-opacity' in sdict:
                stroke_opacity *= float(sdict['stroke-opacity'])
        if self.fill == default:
            self.fill = [0, 0, 0, 255]
        if self.stroke == default:
            self.stroke = [0, 0, 0, 0]  
        if isinstance(self.stroke, list):
            self.stroke[3] = int(self.opacity * stroke_opacity * self.stroke[3])
        if isinstance(self.fill, list):
            self.fill[3] = int(self.opacity * fill_opacity * self.fill[3])                 
        if isinstance(self.stroke, list) and self.stroke[3] == 0: self.stroke = self.fill #Stroked edges antialias better
        
        if e.tag.endswith('path'):
            pathdata = e.get('d', '')               
            pathdata = re.findall("([A-Za-z]|-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", pathdata)
            def pnext():
                return (float(pathdata.pop(0)), float(pathdata.pop(0)))

            self.new_path()
            opcode = ''
            while pathdata:
                prev_opcode = opcode
                if pathdata[0] in string.letters:
                    opcode = pathdata.pop(0)
                else:
                    opcode = prev_opcode
                
                if opcode == 'M':
                    self.set_position(*pnext())
                elif opcode == 'm':
                    mx, my = pnext()
                    self.set_position(self.x + mx, self.y + my)
                elif opcode == 'C':
                    self.curve_to(*(pnext() + pnext() + pnext()))
                elif opcode == 'c':
                    mx = self.x
                    my = self.y
                    x1, y1 = pnext()
                    x2, y2 = pnext()
                    x, y = pnext()
                    
                    self.curve_to(mx + x1, my + y1, mx + x2, my + y2, mx + x, my + y)
                elif opcode == 'S':
                    self.curve_to(2 * self.x - self.last_cx, 2 * self.y - self.last_cy, *(pnext() + pnext()))
                elif opcode == 's':
                    mx = self.x
                    my = self.y
                    x1, y1 = 2 * self.x - self.last_cx, 2 * self.y - self.last_cy
                    x2, y2 = pnext()
                    x, y = pnext()
                    
                    self.curve_to(x1, y1, mx + x2, my + y2, mx + x, my + y)
                elif opcode == 'A':
                    rx, ry = pnext()
                    phi = float(pathdata.pop(0))
                    large_arc = int(pathdata.pop(0))
                    sweep = int(pathdata.pop(0))
                    x, y = pnext()
                    self.arc_to(rx, ry, phi, large_arc, sweep, x, y)
                elif opcode in 'zZ':
                    self.close_path()
                elif opcode == 'L':
                    self.line_to(*pnext())
                elif opcode == 'l':
                    x, y = pnext()
                    self.line_to(self.x + x, self.y + y)
                elif opcode == 'H':
                    x = float(pathdata.pop(0))
                    self.line_to(x, self.y)
                elif opcode == 'h':
                    x = float(pathdata.pop(0))
                    self.line_to(self.x + x, self.y)
                elif opcode == 'V':
                    y = float(pathdata.pop(0))
                    self.line_to(self.x, y)
                elif opcode == 'v':
                    y = float(pathdata.pop(0))
                    self.line_to(self.x, self.y + y)
                else:
                    self.warn("Unrecognised opcode: " + opcode)
            self.end_path()
        elif e.tag.endswith('rect'):
            x = float(e.get('x'))
            y = float(e.get('y'))
            h = float(e.get('height'))
            w = float(e.get('width'))
            self.new_path()
            self.set_position(x, y)
            self.line_to(x+w,y)
            self.line_to(x+w,y+h)
            self.line_to(x,y+h)
            self.line_to(x,y)
            self.end_path()
        elif e.tag.endswith('polyline') or e.tag.endswith('polygon'):
            pathdata = e.get('points')
            pathdata = re.findall("(-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", pathdata)
            def pnext():
                return (float(pathdata.pop(0)), float(pathdata.pop(0)))
            self.new_path()
            while pathdata:
                self.line_to(*pnext())
            if e.tag.endswith('polygon'):
                self.close_path()
            self.end_path()
        elif e.tag.endswith('line'):
            x1 = float(e.get('x1'))
            y1 = float(e.get('y1'))
            x2 = float(e.get('x2'))
            y2 = float(e.get('y2'))
            self.new_path()
            self.set_position(x1, y1)
            self.line_to(x2, y2)
            self.end_path()
        elif e.tag.endswith('circle'):
            cx = float(e.get('cx'))
            cy = float(e.get('cy'))
            r = float(e.get('r'))
            self.new_path()
            for i in xrange(self.circle_points):
                theta = 2 * i * math.pi / self.circle_points
                self.line_to(cx + r * math.cos(theta), cy + r * math.sin(theta))
            self.close_path()
            self.end_path()
        elif e.tag.endswith('ellipse'):
            cx = float(e.get('cx'))
            cy = float(e.get('cy'))
            rx = float(e.get('rx'))
            ry = float(e.get('ry'))
            self.new_path()
            for i in xrange(self.circle_points):
                theta = 2 * i * math.pi / self.circle_points
                self.line_to(cx + rx * math.cos(theta), cy + ry * math.sin(theta))
            self.close_path()
            self.end_path()
        elif e.tag.endswith('linearGradient'):
            self.gradients[e.get('id')] = LinearGradient(e, self)
        elif e.tag.endswith('radialGradient'):
            self.gradients[e.get('id')] = RadialGradient(e, self)
        for c in e.getchildren():
            try:
                self.parse_element(c)
            except Exception, ex:
                print 'Exception while parsing element', c
                raise
        self.transform = oldtransform
        self.opacity = oldopacity                        

    def new_path(self):
        self.x = 0
        self.y = 0
        self.close_index = 0
        self.path = []
        self.loop = [] 
        
    def close_path(self):
        self.loop.append(self.loop[0][:])
        self.path.append(self.loop)
        self.loop = []
        
    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.loop.append([x,y])
    
    def arc_to(self, rx, ry, phi, large_arc, sweep, x, y):
        # This function is made out of magical fairy dust
        # http://www.w3.org/TR/2003/REC-SVG11-20030114/implnote.html#ArcImplementationNotes
        x1 = self.x
        y1 = self.y
        x2 = x
        y2 = y
        cp = math.cos(phi)
        sp = math.sin(phi)
        dx = .5 * (x1 - x2)
        dy = .5 * (y1 - y2)
        x_ = cp * dx + sp * dy
        y_ = -sp * dx + cp * dy
        r2 = (((rx * ry)**2 - (rx * y_)**2 - (ry * x_)**2)/
	      ((rx * y_)**2 + (ry * x_)**2))
        if r2 < 0: r2 = 0
        r = math.sqrt(r2)
        if large_arc == sweep:
            r = -r
        cx_ = r * rx * y_ / ry
        cy_ = -r * ry * x_ / rx
        cx = cp * cx_ - sp * cy_ + .5 * (x1 + x2)
        cy = sp * cx_ + cp * cy_ + .5 * (y1 + y2)
        def angle(u, v):
            a = math.acos((u[0]*v[0] + u[1]*v[1]) / math.sqrt((u[0]**2 + u[1]**2) * (v[0]**2 + v[1]**2)))
            sgn = 1 if u[0]*v[1] > u[1]*v[0] else -1
            return sgn * a
        
        psi = angle((1,0), ((x_ - cx_)/rx, (y_ - cy_)/ry))
        delta = angle(((x_ - cx_)/rx, (y_ - cy_)/ry), 
                      ((-x_ - cx_)/rx, (-y_ - cy_)/ry))
        if sweep and delta < 0: delta += math.pi * 2
        if not sweep and delta > 0: delta -= math.pi * 2
        n_points = max(int(abs(self.circle_points * delta / (2 * math.pi))), 1)
        
        for i in xrange(n_points + 1):
            theta = psi + i * delta / n_points
            ct = math.cos(theta)
            st = math.sin(theta)
            self.line_to(cp * rx * ct - sp * ry * st + cx,
                         sp * rx * ct + cp * ry * st + cy)

    def curve_to(self, x1, y1, x2, y2, x, y):
        if not self.bezier_coefficients:
            for i in xrange(self.bezier_points+1):
                t = float(i)/self.bezier_points
                t0 = (1 - t) ** 3
                t1 = 3 * t * (1 - t) ** 2
                t2 = 3 * t ** 2 * (1 - t)
                t3 = t ** 3
                self.bezier_coefficients.append([t0, t1, t2, t3])
        self.last_cx = x2
        self.last_cy = y2
        for i, t in enumerate(self.bezier_coefficients):
            px = t[0] * self.x + t[1] * x1 + t[2] * x2 + t[3] * x
            py = t[0] * self.y + t[1] * y1 + t[2] * y2 + t[3] * y
            self.loop.append([px, py])

        self.x, self.y = px, py

    def line_to(self, x, y):
        self.set_position(x, y)

    def end_path(self):
        self.path.append(self.loop)
        if self.path:
            path = []
            for orig_loop in self.path:
                if not orig_loop: continue
                loop = [orig_loop[0]]
                for pt in orig_loop:
                    if (pt[0] - loop[-1][0])**2 + (pt[1] - loop[-1][1])**2 > TOLERANCE:
                        loop.append(pt)
                path.append(loop)
            self.paths.append(SvgPath(path if self.stroke else None, self.stroke,
                               self.triangulate(path) if self.fill else None, self.fill,
                               self.transform, self.path_id, self.path_description))
        self.path = []

    def triangulate(self, looplist):
        tlist = []
        self.curr_shape = []
        spareverts = []

        @set_tess_callback(GLU_TESS_VERTEX)
        def vertexCallback(vertex):
            vertex = cast(vertex, POINTER(GLdouble))
            self.curr_shape.append(list(vertex[0:2]))

        @set_tess_callback(GLU_TESS_BEGIN)
        def beginCallback(which):
            self.tess_style = which

        @set_tess_callback(GLU_TESS_END)
        def endCallback():
            if self.tess_style == GL_TRIANGLE_FAN:
                c = self.curr_shape.pop(0)
                p1 = self.curr_shape.pop(0)
                while self.curr_shape:
                    p2 = self.curr_shape.pop(0)
                    tlist.extend([c, p1, p2])
                    p1 = p2
            elif self.tess_style == GL_TRIANGLE_STRIP:
                p1 = self.curr_shape.pop(0)
                p2 = self.curr_shape.pop(0)
                while self.curr_shape:
                    p3 = self.curr_shape.pop(0)
                    tlist.extend([p1, p2, p3])
                    p1 = p2
                    p2 = p3
            elif self.tess_style == GL_TRIANGLES:
                tlist.extend(self.curr_shape)
            else:
                self.warn("Unrecognised tesselation style: %d" % (self.tess_style,))
            self.tess_style = None
            self.curr_shape = []

        @set_tess_callback(GLU_TESS_ERROR)
        def errorCallback(code):
            ptr = gluErrorString(code)
            err = ''
            idx = 0
            while ptr[idx]: 
                err += chr(ptr[idx])
                idx += 1
            self.warn("GLU Tesselation Error: " + err)

        @set_tess_callback(GLU_TESS_COMBINE)
        def combineCallback(coords, vertex_data, weights, dataOut):
            x, y, z = coords[0:3]
            data = (GLdouble * 3)(x, y, z)
            dataOut[0] = cast(pointer(data), POINTER(GLvoid))
            spareverts.append(data)
        
        data_lists = []
        for vlist in looplist:
            d_list = []
            for x, y in vlist:
                v_data = (GLdouble * 3)(x, y, 0)
                d_list.append(v_data)
            data_lists.append(d_list)
        gluTessBeginPolygon(tess, None)
        for d_list in data_lists:    
            gluTessBeginContour(tess)
            for v_data in d_list:
                gluTessVertex(tess, v_data, v_data)
            gluTessEndContour(tess)
        gluTessEndPolygon(tess)
        return tlist       

    def warn(self, message):
        print "Warning: SVG Parser (%s) - %s" % (self.filename, message)
