from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
from varname import nameof
from io import BytesIO
from PIL import Image, ImageDraw
import time

class REALTIME_PLOT():
    def __init__(self, sg_window, sg_treedata):
        self.window = sg_window
        self.treedata = sg_treedata

        self.tree = self.window['-TREE-']
        self.tree.bind("<Double-Button-1>", '+DOUBLE')
        self.tree.bind("<Button-1>", '+B1_CLICK')

        self.graph_data = {}

        self.start_time = time.time()
        self.time = {}
        self.data_list = []
        self.data_dict = {}
        self.data_points = 50

        self.check = [self.icon(0), self.icon(1)]

        self.canvas_elem = self.window['-CANVAS-']
        self.canvas = self.canvas_elem.TKCanvas

        self.fs = 20
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("time(s)", fontsize=self.fs)
        self.ax.set_ylabel("", fontsize=self.fs)
        self.ax.set_title('', fontsize=self.fs)
        self.ax.grid()
        self.ax.tick_params(labelsize=self.fs)
        self.fig_agg = self.draw_figure()

    # Tree
    def icon(self, check):
        box = (32, 32)
        background = (255, 255, 255, 0)
        rectangle = (3, 3, 29, 29)
        line = ((9, 17), (15, 23), (23, 9))
        im = Image.new('RGBA', box, background)
        draw = ImageDraw.Draw(im, 'RGBA')
        draw.rectangle(rectangle, outline='black', width=3)
        if check == 1:
            draw.line(line, fill='white', width=3, joint='curve')
        with BytesIO() as output:
            im.save(output, format="PNG")
            png = output.getvalue()
        return png

    def b1_click(self):
        item = self.tree.Widget.selection()[0]
        key = self.tree.IdToKey[item]
        parent = self.treedata.tree_dict[key].parent
        #print(parent)
        if parent == '':
            self.root_clicked = True
        else:    
            self.root_clicked = False

    def icon_switch(self, key):
        index = self.treedata.tree_dict[key].values[-1]
        index = (index + 1) % 2
        self.treedata.tree_dict[key].values[-1] = index
        self.tree.update(key=key, icon=self.check[index])

        p_key = self.treedata.tree_dict[key].parent
        legend = self.treedata.tree_dict[key].key
        if p_key != '':
            if index == 1:
                self.graph_data[legend] = None
            else:
                try:
                    del self.graph_data[legend]
                    del self.data_dict[legend]
                    del self.time[legend]
                except KeyError:
                    print("KeyError:{}".format(legend))

    def double_click(self):
        item = self.tree.Widget.selection()[0]
        key = self.tree.IdToKey[item]
        self.icon_switch(key)

        # Group Clicked
        if self.root_clicked == True:
            # Child Clicked
            for child in self.treedata.tree_dict[key].children:
                key = child.key
                self.icon_switch(key)
            
    def add_tree_group(self, group_name):
        p_key = '{}'.format(group_name)
        self.treedata.Insert("", p_key, group_name, values=[0], icon=self.check[0])
        self.tree.update(values=self.treedata)
        #print(p_key)

    def add_tree_item(self, group_name, item_name):
        p_key = '{}'.format(group_name)
        c_key = '({}) {}'.format(group_name, item_name)
        self.treedata.Insert(p_key, c_key, item_name, values=[0], icon=self.check[0])
        self.tree.update(values=self.treedata)
        #print(c_key)

    #########################################################
    def update_plot(self, rtdata, number_to_draw):
        data_points = int(number_to_draw)
        keys = []
        
        # Convert VESC Value to searchable dictionary 
        converted_value = {}
        for value_dict in rtdata['vesc_values_list']:
            vesc_id = value_dict['controller_id']
            for key in value_dict:
                converted_value['(VESC_ID:{}) {}'.format(vesc_id, key)] = value_dict[key]
        #print(converted_value)

        # input rtdata to graph_data
        for key in self.graph_data.keys():
            try:
                self.graph_data[key] = rtdata[key]
            except KeyError:
                self.graph_data[key] = converted_value[key]
                
        # prepare data as numbers to draw 
        keys = self.graph_data.keys()
        for key in keys:
            try:
                self.time[key].append(time.time() - self.start_time)
                while len(self.time[key]) > data_points:
                    self.time[key].pop(0)
                self.data_dict[key].append(self.graph_data[key])
                while len(self.data_dict[key]) > data_points:
                    self.data_dict[key].pop(0)
            except KeyError:
                self.time[key] = [time.time() - self.start_time]
                self.data_dict[key] = [self.graph_data[key]]

        if len(keys) != 0:
            ###### Graph ######
            font_size = 20
            self.ax.cla()
            self.ax.set_xlabel("time(sec)", fontsize=font_size)
            #self.ax.set_ylim([0, lim_max])
            self.ax.grid()
            for k in keys:
                self.ax.plot(self.time[k], self.data_dict[k], label=k)
            if len(keys) != 0:
                self.ax.legend(fontsize=font_size, loc='upper right')
                self.ax.tick_params(labelsize=font_size)
            self.fig_agg.draw()

    def draw_figure(self, loc=(0, 0)):
        figure_canvas_agg = FigureCanvasTkAgg(self.fig, self.canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg