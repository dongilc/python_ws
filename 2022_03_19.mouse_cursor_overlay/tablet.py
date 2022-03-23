from cgkit import wintab
from cgkit.wintab.constants import *

class Point:
    ''' A class that respresents stylus data. '''
    def __init__(self, packet, stylus):
        ''' Initialize a new Point given a Wintab packet and the stylus originating it. '''
        self.t = packet.time
        self.x = packet.x * float(stylus.window.winfo_screenwidth()) / float(stylus.context.inextx) - stylus.window.winfo_rootx()
        self.y = stylus.window.winfo_screenheight() - packet.y * float(stylus.window.winfo_screenheight()) / float(stylus.context.inexty)  - stylus.window.winfo_rooty() # Y coordinate is flipped
        self.p = packet.normalpressure/float(stylus.max_pressure)
        self.button = packet.buttons
        self.cursor = {1: 'pen', 2: 'eraser'}[packet.cursor]
        
    def __repr__(self):
        s = '<t:%d x:%f y:%f p:%f %s' % (self.t, self.x, self.y, self.p, self.cursor)
        if self.button != 0:
            s += ' b:%d' % self.button
        s += '>'
        return s
        
class Stylus:
    def __init__(self, window, callback, max_pressure=1024, update_ms=1):
        ''' Create a new stylus for the given Tk window. 'callback' is the function to be called for each new point. '''
        self.window = window
        self.callback = callback
        self.max_pressure = max_pressure
        self.update_ms = update_ms
        
        self.context = wintab.Context()
        self.context.pktdata = (PK_TIME | PK_X | PK_Y | PK_NORMAL_PRESSURE | PK_BUTTONS | PK_CURSOR)
        self.context.open(self.window.winfo_id(), True)
        
        # schedule an update of the Stylus
        self.window.after(self.update_ms, self.update)
        
    def update(self):
        ''' Get new points from the buffer and invoke the callback for each one. '''
        packetExtents = self.context.queuePacketsEx()
        
        if packetExtents[0] is not None and packetExtents[1] is not None:
            packets = self.context.packetsGet(packetExtents[1]-packetExtents[0])
            for p in packets:
                self.callback(Point(p, self))
                
        # reschedule the update of the Stylus
        self.window.after(self.update_ms, self.update)