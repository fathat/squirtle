Squirtle SVG mini-library version 0.2.4
=======================================


Squirtle is a mini-library for rendering SVGs from Python, using the Pyglet
multimedia library. It is designed to have a very simple interface, which allows
it to integrate easily into existing applications.

Example usage:
    import squirtle

    squirtle.setup_gl()

    my_svg = squirtle.SVG('filename.svg', anchor_x='center', anchor_y='center')
    my_svg.draw(100, 200, angle=15, scale=3)

Setting up
----------

To set up Squirtle, simply import the module and, once an OpenGL context has 
been created, call squirtle.setup_gl(). Usually in Pyglet this means something
like:

    import pyglet
    import squirtle

    win = pyglet.window.Window()
    squirtle.setup_gl()

If you are working with raw OpenGL calls as part of your application, you may
wish to incorporate the code from squirtle.setup_gl() into your own setup 
function. See the source code for further details.

Creating an SVG
---------------

SVG objects are instantiated simply by calling

    my_svg = squirtle.SVG(filename)

The filename argument can point to either an SVG or gzipped SVG (SVGZ) file.

There are also a collection of optional keyword arguments which can be used to
control the SVG created. For example:

    my_svg = squirtle.SVG('image.svg', anchor_x='center', anchor_y='center')

The anchor_x and anchor_y properties determine which point on the SVG is
considered to be the 'origin' when transforming and drawing. They default to the
bottom left corner. Anchor positions can be specified either numerically (in
pixels) or as symbolic names such as 'top', 'center', 'bottom', 'left' or 
'right'. They can also be modified after creation like so:

    my_svg = squirtle.SVG('image.svg')
    my_svg.anchor_x = my_svg.width * .75
    my_svg.anchor_y = 20

Note that the coordinate system used by Pyglet and the native SVG coordinate
system are flipped with respect to each other. All coordinates used in Squirtle
are in Pyglet-style (y increases upward) coordinates.

Two other options control the degree of subdivision used when rendering curves.
For example:

    my_svg = squirtle.SVG(filename, bezier_points=5, circle_points=12)

The bezier_points and circle_points options control the degree of subdivision
used on Bezier splines and elliptical arcs respectively. They default to 10 and
24. These properties cannot be changed after creation.

Drawing an SVG
--------------

At its most basic, rendering an SVG is as simple as:

    my_svg.draw(x, y)

This will render the given SVG, such that its (anchor_x, anchor_y) position is 
at screen coordinates (x, y). There are, of course, options which can be used to
modify the behaviour of this rendering. For example:

    my_svg.draw(x, y, z=-1)

This will draw the given SVG at a z-coordinate of -1, i.e. behind any other 
images which have been rendered. Note that using this to full effect requires
enabling OpenGL depth testing, and that SVGs with transparency may not render
correctly in this way.

The main advantages of SVG come from being able to freely rotate and scale
without loss of quality:

    my_svg.draw(x, y, angle=15, scale=3)

The angle and scale options control, rather obviously, the angle and scale at
which the SVG is rendered. Both options work around the pivot point given by
(anchor_x, anchor_y). Rotation is given in degrees counter-clockwise, and scale
is a simple multiplicative factor. It is also possible to give a 2-tuple of
scale values in order to scale anisotropically. For example, in order to flip
an SVG horizontally:

    my_svg.draw(x, y, scale=(-1, 1))

Limitations
-----------

Squirtle is at present quite limited in the SVG which it can render. Basic
geometric shapes, paths, polygons, etc work fine. Solid fills work, as do both
linear and radial gradients. Note that gradients may render slightly oddly due
to vertex colouring.

Significant aspects of the SVG specification which have not been implemented
include patterned fills, variable line widths, text and the symbol system.

Patches to improve on any of these limitations are greatly welcomed.

Changes since 0.2
-----------------

Fix errors in arc calculation.
Fix default winding rule for complex curves.
Fix support for SVGs created by Intaglio and some versions of Inkscape.
Improve efficiency when tesselating.
Fix crash bug on Win32 systems.

Changes since 0.1 (initial release)
-----------------------------------

Triangulation now uses the GLU tesselator functions, rather than the Python
code used previously. This should result in increased performance, as well as
allowing for more complex shapes.

Bugfixes for empty style definitions, and for radial gradients with inherited
properties.

Colophon
--------
Squirtle is released under a BSD license, which can be found in the accompanying
file LICENSE.txt

Bug reports, patches, etc, welcome to martin@supereffective.org
