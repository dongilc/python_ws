from math import e
from shutil import ExecError
import pyglet
import pyglet.window.key
from pyglet import shapes

window = pyglet.window.Window(style=pyglet.window.Window.WINDOW_STYLE_TRANSPARENT)#WINDOW_STYLE_OVERLAY)
window.set_fullscreen(True)

tablets = pyglet.input.get_tablets()
canvases = []
circle = shapes.Circle(x = 100, y = 100, radius = 8, color=(255, 255, 0))
circle.opacity = 32

if tablets:
    print('Tablets:')
    for i, tablet in enumerate(tablets):
        print('  (%d) %s' % (i + 1, tablet.name))
    print('Press number key to open corresponding tablet device.')
else:
    print('No tablets found.')

# key press event   
@window.event
def on_key_press(symbol, modifier):
    # key "e" get press
    if symbol == pyglet.window.key.SPACE:
        window.close()

@window.event
def on_draw():
    window.clear()
    circle.draw()

@window.event
def on_mouse_press(x, y, button, modifiers):
    pass
    #print('on_mouse_press(%r, %r, %r, %r)' % (x, y, button, modifiers))

@window.event
def on_mouse_release(x, y, button, modifiers):
    pass
    #print('on_mouse_release(%r, %r, %r, %r)' % (x, y, button, modifiers))

@window.event
def on_mouse_release(x, y, button, modifiers):
    pass
    #print('on_mouse_release(%r, %r, %r, %r)' % (x, y, button, modifiers))

@window.event
def on_mouse_motion(x, y, dx, dy):
    circle.x = x
    circle.y = y
    #print('on_mouse_motion(%r, %r, %r, %r)' % (x, y, dx, dy))

pyglet.app.run()