import os
from io import BytesIO
from PIL import Image, ImageDraw
import PySimpleGUI as sg

def add_files_in_folder(parent, dirname):
    files = os.listdir(dirname)
    for f in files:
        fullname = os.path.join(dirname, f)
        if os.path.isdir(fullname):
            treedata.Insert(parent, fullname, f, values=[0], icon=check[0])
            add_files_in_folder(fullname, fullname)
        else:
            treedata.Insert(parent, fullname, f, values=[
                            os.stat(fullname).st_size, 0], icon=check[0])

def double_click(tree, treedata):
    item = tree.Widget.selection()[0]
    key = tree.IdToKey[item]
    index = treedata.tree_dict[key].values[-1]
    index = (index + 1) % 3
    treedata.tree_dict[key].values[-1] = index
    tree.update(key=key, icon=check[index])

def icon(check):
    box = (32, 32)
    background = (255, 255, 255, 0)
    rectangle = (3, 3, 29, 29)
    line = ((9, 17), (15, 23), (23, 9))
    im = Image.new('RGBA', box, background)
    draw = ImageDraw.Draw(im, 'RGBA')
    draw.rectangle(rectangle, outline='black', width=3)
    if check == 1:
        draw.line(line, fill='black', width=3, joint='curve')
    elif check == 2:
        draw.line(line, fill='grey', width=3, joint='curve')
    with BytesIO() as output:
        im.save(output, format="PNG")
        png = output.getvalue()
    return png

check = [icon(0), icon(1), icon(2)]

'''
starting_path = sg.popup_get_folder('Folder to display')
if not starting_path:
    sys.exit(0)

treedata = sg.TreeData()
add_files_in_folder('', starting_path)
font = ('Helvetica', 16)
layout = [[sg.Text('File and folder browser Test')],
          [sg.Tree(data=treedata, headings=['Size', ], auto_size_columns=True,
                   num_rows=10, col0_width=40, key='-TREE-', font=font,
                   row_height=48, show_expanded=False, enable_events=True)],
          [sg.Button('Ok', font=font), sg.Button('Cancel', font=font)]]
window = sg.Window('Tree Element Test', layout, finalize=True)
tree = window['-TREE-']         # type: sg.Tree
tree.bind("<Double-1>", '+DOUBLE')
while True:
    event, values = window.read()
    if event in (sg.WIN_CLOSED, 'Cancel'):
        break
    if event.endswith('DOUBLE'):
        double_click()
    print(event, values)
window.close()
'''