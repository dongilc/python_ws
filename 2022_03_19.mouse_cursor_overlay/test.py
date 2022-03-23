from tkinter import *
from tablet import Stylus

# create a window with a canvas to draw onto
window = Tk()
window.title('Tablet test')
canvas = Canvas(window)

# define a callback for drawing points
def draw(p):
    ''' Draw a point as a circle with a radius proportional to the pressure. '''
    if p.button == 1:
        x, y, r = p.x, p.y, p.p*10
        canvas.create_oval(x-r, y-r, x+r, y+r, outline='black', width=1)
        canvas.pack(fill=BOTH, expand=1)
        
# create the stylus object, binding the callback
stylus = Stylus(window, callback=draw)

# start the application
window.mainloop()