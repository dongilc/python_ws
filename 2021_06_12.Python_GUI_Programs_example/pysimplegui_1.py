import PySimpleGUI as sg
import ctypes
import platform

def make_dpi_aware():
    if platform.system() == "Windows":
        if platform.release() == "7":
            ctypes.windll.user32.SetProcessDPIAware()
        elif platform.release() >= 8:
            ctypes.windll.shcore.SetProcessDpiAwareness(True)
    elif platform.system() == "Linux":
        ctypes.windll.shcore.SetProcessDpiAwareness(True)

sg.theme('DarkAmber')    # Keep things interesting for your users

layout = [[sg.Text('Persistent window')],      
          [sg.Input(key='-IN-')],      
          [sg.Button('Read'), sg.Exit()]]      

window = sg.Window('Window that stays open', layout)      

make_dpi_aware()

while True:                             # The Event Loop
    event, values = window.read() 
    print(event, values)       
    if event == sg.WIN_CLOSED or event == 'Exit':
        break      

window.close()