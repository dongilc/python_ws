import PySimpleGUI as sg
import ctypes
import platform
import serial
import pysoem
import time
from openrobot_vesc_lib import vesc_pyserial as vs
from openrobot_vesc_lib import vesc_ethercat as ve
from openrobot_vesc_lib.general_defines import *
from openrobot_vesc_lib import rt_plot as rp
import threading
from threading import Timer
import multiprocessing
from multiprocessing import Process, Manager, current_process, freeze_support

# need sudo, therefore run as like "sudo -E env "PATH=$PATH" python VESCular_Basic_Test_Gui.py"
loop_time = 0
pdo_loop_time_ms = 0
pdo_loop_freq_khz = 0
point = 0
progress_time = []
frequency_list = []
graph_update_flag = False
vesc_values_names = ['temp_fet[C]', 'temp_motor[C]', 'motor_current[A]', 'input_current[A]', 'id_current[A]', 'iq_current[A]', 'duty', 'erpm', 
                     'volt_input[V]', 'amp_hours[Ah]', 'amp_hours_charged[Ah]', 'watt_hours[Wh]', 'watt_hours_charged[Wh]', 'tacho', 'tacho_abs', 
                     'fault', 'pid_pos_now[deg]', 'controller_id', 'temp_mos1[C]', 'temp_mos2[C]', 'temp_mos3[C]', 'vd_volt[V]', 'vq_volt[V]']

BYTE_NUM = 128
actual_wkc = None   # Working Counter
proc_ethercat_pdo = None
process_data = {}

#
serial_loop_time_ms = 0
serial_loop_freq_hz = 0

######################### Class Init #########################
# default serial
vesc_serial_name = ''
vesc_serial_class = None
ser_ind = 0
baud = ('115200', '460800', '921600')
tout = 0.5

# default ethercat
vesc_ethercat_class = None

# default about joint
joint_list = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6']
joint_original_tuple = tuple(joint_list)
vesc_joint_match = {} #{1:'J1', 2:'J2', 3:'J3', 4:'J4', 5:'J5', 6:'J6'} # dictionary type, ID:'Joint Number'
refresh_list_flag = False
vesc_serial_class_list = []

# gui theme select
sg.theme('DarkAmber')   # Add a touch of color

######################### Common Functions #########################
# For 4K monitor(HiDPI)
def make_dpi_aware():
    if platform.system() == "Windows":
        if int(platform.release()) == "7":
            ctypes.windll.user32.SetProcessDPIAware()
        elif int(platform.release()) >= 8:
            ctypes.windll.shcore.SetProcessDpiAwareness(True)

def dict_get_key_from_value(dict, val):
    for key, value in dict.items():
        try:
            if val == value:
                return key
        except KeyError:
            print("There is no key of value:{}".format(val))

# 시리얼 포트 스캔
def scan_serial_ports():
    p_name, p_desc, p_hwid, p_num = vs.list_serial()
    #print(p_name)
    #print(p_desc)
    #print(p_hwid)
    if p_num == 0: p_data = [["No Device"],[""]]
    else:
        p_data = [] 
        for i in range(p_num):
            p_data = p_data + [[i, p_name[i], p_hwid[i]]]
    return p_data

def refresh_vesc_serial_class_list():
    vesc_serial_class.vesc_id_data.clear()
    for ser_class in vesc_serial_class_list:
        if ser_class is not None:
            ids = ser_class.controller_id_list
            
            if len(ids) != 0:
                for i in range(len(ids)):
                    try:
                        if i == 0:
                            if vesc_joint_match[ids[i]] is not None: 
                                vesc_serial_class.vesc_id_data.append([vesc_serial_class.serial_name.port, ids[i], "Local", vesc_joint_match[ids[i]]])
                        else:
                            if vesc_joint_match[ids[i]] is not None: 
                                vesc_serial_class.vesc_id_data.append([vesc_serial_class.serial_name.port, ids[i], "CAN", vesc_joint_match[ids[i]]])
                    except:
                        if i == 0:
                            vesc_serial_class.vesc_id_data.append([vesc_serial_class.serial_name.port, ids[i], "Local", joint_list[i]])
                            vesc_joint_match[ids[i]] = joint_list[i]
                            print("Joint number of vesc id:", ids[i], "is not pre-defined")
                        else:
                            vesc_serial_class.vesc_id_data.append([vesc_serial_class.serial_name.port, ids[i], "CAN", joint_list[i]])
                            vesc_joint_match[ids[i]] = joint_list[i]
                            print("Joint number of vesc id:", ids[i], "is not pre-defined")
                #print(vesc_serial_class.vesc_id_data)
        else:
            print("No devices, SCAN VESC first")
    window.Element('-VESC_TABLE_SERIAL-').Update(values=vesc_serial_class.vesc_id_data)
    refresh_list_flag = False

def serial_alive_thread_stop(window):
    global vesc_serial_class
    try:
        vesc_serial_class.periodic_run = False
        window.Element('-BTN_SERIAL_PERIODIC-').Update(text="Periodic On")
        window.Element('-TERMINAL_SEND-').Update(disabled=False)
        print('Serial Periodic Process Stop')
    except Exception as e: None

# EtherCAT using PySOEM
def ethercat_pdo_multiprocess_func(vec,):
    time_start = 0
    time_prev = 0
    loop_time = 0
    pdo_loop_time_ms = 0
    pdo_loop_freq_khz = 0
    ethercat_wkc = ''

    num_cores = multiprocessing.cpu_count()
    print("number of cores of PC:", num_cores)
    c_proc = current_process()
    print("Running on Process", c_proc.name, "PID", c_proc.pid)

    ## 쓰레드 종료될때까지 계속 돌림
    while True:
        ######## Process Loop time control ########
        time_prev = time_start
        time_start = time.time_ns()
        loop_time = time_start - time_prev
        pdo_loop_time_ms = loop_time/1000000.
        if pdo_loop_time_ms == 0:
            pdo_loop_freq_khz = 1
        else:
            pdo_loop_freq_khz = 1/pdo_loop_time_ms

        ######## Prepare process Data ########
        # downloading process data      
        target_slave_index = process_data['target_slave']
        data = process_data['send_data']
        vec.debug_print_get_value_return = process_data['debug_print'][0]
        vec.debug_print_custom_return = process_data['debug_print'][1]
        # uploading process data
        process_data['ethercat_wkc'] = ethercat_wkc
        process_data['loop_pdo_ms'] = pdo_loop_time_ms
        process_data['loop_pdo_khz'] = pdo_loop_freq_khz
        process_data['vesc_values'] = vec.value_list

        ######## Prepare TX data ########
        # erase output buffer first
        if target_slave_index is not None:
            output_tmp = bytearray([0 for i in range(vec.BYTE_NUM)])
            vec.master.slaves[target_slave_index].output = bytes(output_tmp)
        # load data
        if len(data) != 0:
            for i in range(len(data)):
                output_tmp[i] = data[i]    
            vec.master.slaves[target_slave_index].output = bytes(output_tmp)

        # EtherCAT PDO
        vec.master.send_processdata()
        actual_wkc = vec.master.receive_processdata()
        if not actual_wkc == vec.master.expected_wkc:
            ethercat_wkc = 'Incorrect WKC'
        else:
            ethercat_wkc = 'Normal Operation'

        ######## Process RX data ########
        for slave in vec.master.slaves:
            vec.ethercat_Slave_Read_Rxdata(slave.input)

        #time.sleep(0.1)

def ethercat_pdo_multiprocess_stop(window):
    global proc_ethercat_pdo
    try:
        proc_ethercat_pdo.terminate()
        proc_ethercat_pdo = None
        print("EtherCAT PDO Process Stop")
        window.Element("-ETHERCAT_STS_MSG-").Update('EtherCAT PDO Stopped')
    except Exception as e: None

def ethercat_master_close(vec):
    vec.master.state = pysoem.INIT_STATE
    # request INIT state for all slaves
    vec.master.write_state()
    vec.master.close()
    vec.master = None

############################################## Main ##############################################
if __name__ == "__main__":
    if platform.system() == "Windows":
        freeze_support()

    manager = Manager()
    process_data = manager.dict()
    process_data['target_slave'] = None
    process_data['send_data'] = []
    process_data['debug_print'] = [False, False]
    process_data['ethercat_wkc'] = ''
    process_data['loop_pdo_ms'] = 0
    process_data['loop_pdo_khz'] = 0
    process_data['vesc_values'] = []
    
    ######################### GUI #########################
    # usb port table data 
    ports_title = ["No.", "Port Name", "VID:PID"]
    ports_data = scan_serial_ports()
    # vesc id table data
    vesc_id_headings = ["Port", "VESC ID", "COMM", "Joint"]
    # Ethernet Adapter 
    adapter_id_data = []
    adapter_id_headings = ["No.", "Name", "Desc"]

    # print all debugging msgs to Multiline
    #print = sg.cprint
    #MLINE_KEY1 = '-ML1-'+sg.WRITE_ONLY_KEY

    vesc_layout = [ [sg.HorizontalSeparator()],
                    #[sg.Text('VESC USB Connection', font=("Tahoma", 14))],
                    [sg.Table(values=ports_data, headings=ports_title, max_col_width=100,
                                    col_widths=[10,20,20],
                                    background_color='black',
                                    auto_size_columns=False,
                                    justification='center',
                                    num_rows=3,
                                    alternating_row_color='black',
                                    enable_events=True,
                                    key='-USB_TABLE-',
                                    row_height=50)],
                    [sg.Text('Baudrate'), sg.Combo(values=baud, default_value='921600', readonly=True, k='-BAUD-'),
                    sg.Button('SCAN'), sg.Button('CONNECT'), sg.Button('DISCONNECT')],
                    [sg.HorizontalSeparator()],
                    [sg.Text('Connected VESC IDs')],
                    [sg.Table(values=[], headings=vesc_id_headings, max_col_width=100,
                                    col_widths=[20,10,10,10],
                                    background_color='black',
                                    auto_size_columns=False,
                                    display_row_numbers=False,
                                    justification='center',
                                    num_rows=6,
                                    alternating_row_color='black',
                                    enable_events=True,
                                    key='-VESC_TABLE_SERIAL-',
                                    row_height=50)],
                    [sg.Button('SCAN VESC'), sg.Button('Refresh List'), sg.Button('Periodic On', key='-BTN_SERIAL_PERIODIC-')],
                    [sg.Text("| Loop-Time:"), sg.Text("", key='-SERIAL_LOOP_MS-'), 
                     sg.Text("| Freq.:"), sg.Text("", key='-SERIAL_LOOP_HZ-')],
                    [sg.Text("| Target Freq.:"), sg.InputText("100", size=(4,1), key='-SERIAL_PERIODIC_FREQ-'), sg.Text("HZ")],
                    [sg.HorizontalSeparator()],
                    [sg.Text("Value:"), sg.InputText("0", size=(4,1), key='-SERIAL_CMD_VALUE1-'), sg.Text("[-1~+1]"),
                        sg.Button('Set Duty', size=(11,1), key='-SERIAL_CMD_DUTY-'), sg.Button('Release', size=(13,1), key='-SERIAL_CMD_RELEASE-')],
                    [sg.Text("Value:"), sg.InputText("0", size=(4,1), key='-SERIAL_CMD_VALUE2-'), sg.Text("  [A]  "),
                        sg.Button('Set Current', size=(11,1), key='-SERIAL_CMD_CURRENT-'), sg.Button('Current Brake', size=(13,1), key='-SERIAL_CMD_CURRENT_BRAKE-')],
                    [#sg.Button('Clear'),
                    sg.Button('DEBUG PRINT ON', key='-SERIAL_DEBUG_PRINT_ON-'), 
                    sg.Button('DEBUG PRINT OFF', key='-SERIAL_DEBUG_PRINT_OFF-')],
                    [sg.HorizontalSeparator()],
                    [sg.Text("Terminal Command to"), 
                    sg.Combo(values=joint_list, default_value=joint_list[0], readonly=True, k='-TARGET_JOINT-'), 
                    sg.Input(size=(18,1), focus=True, key='-TERMINAL_INPUT-'), sg.Button('SEND', key='-TERMINAL_SEND-', bind_return_key=True)]
    ]

    ethercat_layout = [ [sg.HorizontalSeparator()],
                        #[sg.Text('EtherCAT using PySOEM', font=("Tahoma", 14))],
                        [sg.Table(values=adapter_id_data, headings=adapter_id_headings, max_col_width=100,
                                    col_widths=[10,20,20],
                                    background_color='black',
                                    auto_size_columns=False,
                                    display_row_numbers=False,
                                    justification='center',
                                    num_rows=4,
                                    alternating_row_color='black',
                                    key='-ADAPTER_TABLE-',
                                    row_height=50)],
                        [sg.Button('SCAN Adapter'), sg.Button('Master OPEN'), sg.Button('Master CLOSE')],
                        [sg.HorizontalSeparator()],
                        [sg.Text('Connected VESC IDs')],
                        [sg.Table(values=[], headings=["Adapter", "VESC ID", "COMM", "Joint"], max_col_width=100,
                                    col_widths=[20,10,10,10],
                                    background_color='black',
                                    auto_size_columns=False,
                                    display_row_numbers=False,
                                    justification='center',
                                    num_rows=6,
                                    alternating_row_color='black',
                                    key='-VESC_TABLE_ETHERCAT-',
                                    row_height=50)],
                        [sg.HorizontalSeparator()],
                        [sg.Button('Refresh Slaves'), sg.Button('Run PDO'), sg.Button('Stop PDO')],
                        [sg.Text("| Loop-Time:"), sg.Text("", key='-ETHERCAT_LOOP_MS-'), 
                        sg.Text("| Freq.:"), sg.Text("", key='-ETHERCAT_LOOP_HZ-')], 
                        [sg.Text("| Status Msg:"), sg.Text("", key='-ETHERCAT_STS_MSG-')],
                        [sg.HorizontalSeparator()],
                        [sg.Text("Value:"), sg.InputText("0", size=(4,1), key='-ETHERCAT_CMD_VALUE1-'), sg.Text("[-1~+1]"),
                        sg.Button('Set Duty', size=(11,1), key='-ETHERCAT_CMD_DUTY-'), sg.Button('Release', size=(13,1), key='-ETHERCAT_CMD_RELEASE-')],
                        [sg.Text("Value:"), sg.InputText("0", size=(4,1), key='-ETHERCAT_CMD_VALUE2-'), sg.Text("  [A]  "),
                        sg.Button('Set Current', size=(11,1), key='-ETHERCAT_CMD_CURRENT-'), sg.Button('Current Brake', size=(13,1), key='-ETHERCAT_CMD_CURRENT_BRAKE-')],
                        [#sg.Button('Get Value', size=(12,1)),
                        sg.Button('DEBUG PRINT ON', key='-ETHERCAT_DEBUG_PRINT_ON-'), 
                        sg.Button('DEBUG PRINT OFF', key='-ETHERCAT_DEBUG_PRINT_OFF-')],
    ]

    graph_legend_layout = [[sg.Checkbox('PDO Loop Freq.')], 
    ]

    treedata = sg.TreeData()
    graph_layout = [[sg.Text('Real-time Plot', font=("Tahoma", 12)), 
                     sg.Button('Graph ON'), sg.Button('Graph OFF'),
                     sg.Text('| Number of Data to Draw:'), sg.Slider(range=(10, 100), default_value=50, orientation='h', key='-SLIDER-DATAPOINTS-')],
                    [sg.Canvas(expand_x=True, expand_y=True, key='-CANVAS-'), 
                     sg.Tree(data=treedata, headings = [], font=("Tahoma", 8),
                             num_rows=20, col0_width=20, key='-TREE-', 
                             row_height=120, show_expanded=True, enable_events=True)],
    ]

    tab_layout = [[sg.TabGroup([[sg.Tab('VESC Serial', vesc_layout), sg.Tab('VESC EtherCAT',ethercat_layout)]], font=("Tahoma", 14))]]

    layout_main = [[sg.Column(tab_layout), sg.VSeperator(), sg.Column(graph_layout, expand_x=True, expand_y=True, vertical_alignment="top")]
    ]

    # 4k hidpi solution
    make_dpi_aware()
    #print(platform.system())
    #print(platform.architecture()[1])
    # Create the Window
    if platform.system() == "Linux" and platform.architecture()[1] == "ELF":
        window = sg.Window('VESCular Basic Test Gui', layout_main, location=(300,50), size=(3500,1400), scaling=5.0, finalize=True) #, keep_on_top=True
    else:
        window = sg.Window('VESCular Basic Test Gui', layout_main, location=(300,50), size=(3500,1400), finalize=True)
    
    ########################### Graph Plot init Setting #############################
    rp_class = rp.REALTIME_PLOT(window, treedata)

    ######################### GUI Event Loop #########################
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read(timeout=5)

        if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
            for class_instance in vesc_serial_class_list:
                class_instance.exitThread_usb = True
                class_instance.usb_connection_flag = False
                # close serial
                if class_instance.serial_name is not None:
                    if class_instance.serial_name.is_open:
                        class_instance.serial_name.close()
            
            # Terminate Serical Process
            serial_alive_thread_stop(window)

            # Terminate Ethercat Process
            ethercat_pdo_multiprocess_stop(window)
            try:
                vesc_ethercat_class.master.state = pysoem.INIT_STATE
                # request INIT state for all slaves
                vesc_ethercat_class.master.write_state()
                vesc_ethercat_class.master.close()
            except Exception as e: None

            break

        if event.endswith('B1_CLICK'):
            rp_class.b1_click()

        if event.endswith('DOUBLE'):
            rp_class.double_click()

        if event == "-USB_TABLE-":
            row = values['-USB_TABLE-']
            if len(row) != 0:
                ser_ind = row[0]
                vesc_serial_name = ports_data[ser_ind][1]
                print("USB Port Selected - No:{0}, port:{1}".format(ser_ind, vesc_serial_name))

        if event == "SCAN":
            print("Scan valid usb ports...")
            ports_data = scan_serial_ports()
            window.Element('-USB_TABLE-').Update(values=ports_data)
    
        if event == "-VESC_TABLE_SERIAL-":
            row = values['-VESC_TABLE_SERIAL-']
            if len(row) != 0:
                index = row[0]
                print("Joint {} is selected on serial device.".format(vesc_serial_class.vesc_id_data[index][3]))

        if event == "Refresh List":
            refresh_vesc_serial_class_list()

        if event == "-BTN_SERIAL_PERIODIC-":
            if vesc_serial_name == 'No Device':
                print("Select valid devices")
            elif vesc_serial_name != '':
                if vesc_serial_class is not None:
                    if vesc_serial_class.periodic_run == False:
                        vesc_serial_class.periodic_run = True
                        vesc_serial_class.periodic_freq = float(values['-SERIAL_PERIODIC_FREQ-'])       
                        window.Element('-BTN_SERIAL_PERIODIC-').Update(text="Periodic Off")
                        window.Element('-TERMINAL_SEND-').Update(disabled=True)
                        #print("Serial device periodic control is On")

                        vs.signal.signal(vs.signal.SIGINT, vesc_serial_class.periodic_run)
                        vesc_serial_class.alive_thread = threading.Thread(target=vesc_serial_class.serial_send_alive)
                        vesc_serial_class.alive_thread.start()

                        rp_class.add_tree_group('Serial Loop')
                        rp_class.add_tree_item('Serial Loop', 'time')
                        rp_class.add_tree_item('Serial Loop', 'freq.')
                        #proc_serial_alive = Process(target=serial_alive_multiprocess_func, args=(vesc_serial_class,))
                        #proc_serial_alive.start()
                        #print("Serial Periodic Process Start")
                    else:
                        serial_alive_thread_stop(window)
                        
                else:
                    print("VESC Not Connected")
            else:
                print("Please select USB Port first")

        if event == "CONNECT":
            baudrate_sel = values['-BAUD-']
            if vesc_serial_name == 'No Device':
                print("Select valid devices")
            elif vesc_serial_name != '':
                if vesc_serial_class is None:
                    while True:
                        try:
                            # create serial connection class
                            vesc_serial_class = vs.VESC_USB(serial.Serial(vesc_serial_name, baudrate_sel, timeout=tout), ser_ind, window)
                            vesc_serial_class_list.append(vesc_serial_class)
                        except serial.SerialException:
                            continue
                        else:
                            print("VESC USB Connected at {}, {}bps".format(vesc_serial_class.serial_name.port, baudrate_sel))
                            break

                    if vesc_serial_class.usb_connection_flag:
                        #종료 시그널 등록
                        vs.signal.signal(vs.signal.SIGINT, vesc_serial_class.handler_usb)

                        #시리얼 읽을 쓰레드 생성
                        thread_usb_rx = vs.threading.Thread(target=vesc_serial_class.readThread, args=(process_data,))
                        #시작!
                        thread_usb_rx.start()
                        print("VESC USB RX Thread Started", vesc_serial_class.serial_name.port)

                        # Specify Next event, automatically scan vesc IDs
                        event = "SCAN VESC"
                else:
                    print("Select USB Port is already Opened")
            else:
                print("Please select USB Port first")
            
        if event == "DISCONNECT":
            if vesc_serial_name == 'No Device':
                print("Select valid devices")
            elif vesc_serial_name != '':
                #print(len(vesc_serial_class.vesc_id_data))

                if vesc_serial_class is not None:
                    #print(vesc_serial_class.vesc_id_data)
                    # delete connected vesc list 
                    vesc_serial_class.del_vesc_list()
                    vesc_serial_class.reset_controller_id_list()
                    #print(vesc_serial_class.vesc_id_data)
                    window.Element('-VESC_TABLE_SERIAL-').Update(values=vesc_serial_class.vesc_id_data)

                    # serial class disconnection
                    vesc_serial_class.exitThread_usb = True
                    vesc_serial_class.periodic_run = False
                    window.Element('-BTN_SERIAL_PERIODIC-').Update(text="Periodic On")
                    ethercat_pdo_multiprocess_stop()

                    vesc_serial_class.serial_name.close()
                    vesc_serial_class = None
                    print("VESC USB Disconnected")
                else:
                    print("VESC Not Connected")
            else:
                print("Please select USB Port first")
    
        if event == "SCAN VESC":
            if vesc_serial_class is not None:
                if vesc_serial_class.usb_connection_flag:
                    vesc_serial_class.reset_controller_id_list()
                    send_data = vesc_serial_class.packet_encoding(COMM_PACKET_ID['COMM_GET_VALUES'])
                    #print(send_data)
                    vesc_serial_class.serial_write(send_data)
                    time.sleep(0.1)
                    send_data = vesc_serial_class.packet_encoding(COMM_PACKET_ID['COMM_PING_CAN'])
                    #print(send_data)
                    vesc_serial_class.serial_write(send_data)
                    
                    # 5초후에 REPRESH LIST event 실행하기
                    if refresh_list_flag == False:
                        Timer(5, refresh_vesc_serial_class_list).start()           
                else:
                    print("VESC Not Connected")
            else:
                print("VESC Not Connected")

        if event == "Clear":
            window['-OUTPUT-'].update(value='')

        if event == "-SERIAL_CMD_DUTY-" or event == "-SERIAL_CMD_RELEASE-":
            if vesc_serial_class is not None:
                row = values['-VESC_TABLE_SERIAL-']
                if len(row) != 0:
                    index = row[0]
                    vesc_id = vesc_serial_class.vesc_id_data[index][1]
                    vesc_comm = vesc_serial_class.vesc_id_data[index][2]
                    if event == "-SERIAL_CMD_DUTY-":
                        vesc_serial_class.serial_send_cmd(vesc_id, vesc_comm, "duty", values['-SERIAL_CMD_VALUE1-'])
                    elif event == "-SERIAL_CMD_RELEASE-":
                        vesc_serial_class.serial_send_cmd(vesc_id, vesc_comm, "release")
                else:
                    print("Joint is not selected.") 
            else:
                print("Serial is not open yet.")

        if event == "-SERIAL_CMD_CURRENT-" or event == "-SERIAL_CMD_CURRENT_BRAKE-":
            if vesc_serial_class is not None:
                row = values['-VESC_TABLE_SERIAL-']
                if len(row) != 0:
                    index = row[0]
                    vesc_id = vesc_serial_class.vesc_id_data[index][1]
                    vesc_comm = vesc_serial_class.vesc_id_data[index][2]
                    if event == "-SERIAL_CMD_CURRENT-":
                        vesc_serial_class.serial_send_cmd(vesc_id, vesc_comm, "current", values['-SERIAL_CMD_VALUE2-'])
                    elif event == "-SERIAL_CMD_CURRENT_BRAKE-":
                        vesc_serial_class.serial_send_cmd(vesc_id, vesc_comm, "current_brake", values['-SERIAL_CMD_VALUE2-'])
                else:
                    print("Joint is not selected.") 
            else:
                print("Serial is not open yet.")

        if event == "-TERMINAL_SEND-":
            if vesc_serial_class is not None:
                #print(vesc_joint_match)
                vesc_id = dict_get_key_from_value(vesc_joint_match, values['-TARGET_JOINT-'])
                vesc_comm = 'Local'
                for vesc in vesc_serial_class.vesc_id_data:
                    #print(vesc)
                    if vesc[1] == vesc_id:
                        vesc_comm = vesc[2]
                #print(vesc_id, vesc_comm)
                vesc_serial_class.serial_send_cmd(vesc_id, vesc_comm, 'terminal', values['-TERMINAL_INPUT-'])
            else:
                print("Serial is not open yet.")
    
        if event == "-SERIAL_DEBUG_PRINT_ON-":
            if vesc_serial_class is not None:
                vesc_serial_class.debug_print_get_value_return = True
                vesc_serial_class.debug_print_custom_return = True
                print("DEBUG PRINT ON")
            else:
                print("Serial is not open yet.")

        if event == "-SERIAL_DEBUG_PRINT_OFF-":
            if vesc_serial_class is not None:
                vesc_serial_class.debug_print_get_value_return = False
                vesc_serial_class.debug_print_custom_return = False
                print("DEBUG PRINT OFF")
            else:
                print("Serial is not open yet.")

        # EtherCAT
        if event == "SCAN Adapter":
            print("Scan Ethernet Adapters...")
            adapter_id_data = []
            scaned_adapters = pysoem.find_adapters()
            for i, adapter in enumerate(scaned_adapters):
                adapter_id_data.append([i, adapter.name, adapter.desc])
            window.Element('-ADAPTER_TABLE-').Update(values=adapter_id_data)

        if event == "-ADAPTER_TABLE-":
            row = values['-ADAPTER_TABLE-']
            if len(row) != 0:
                ser_ind = row[0]
                selected_adapter_name = adapter_id_data[ser_ind][1]
                selected_adapter_desc = adapter_id_data[ser_ind][2]
                print("Ethernet Adapter Selected - Name:{}, Desc:{}".format(selected_adapter_name, selected_adapter_desc))

        if event == "Master OPEN":
            row = values['-ADAPTER_TABLE-']
            if len(row) != 0:
                adapter_name = adapter_id_data[row[0]][1]     

                # Create vesc packet class
                vesc_ethercat_class = ve.VESC_ETHERCAT(adapter_name, BYTE_NUM)

                slaves = []
                for i in range(vesc_ethercat_class.master.config_init()):
                    slaves.append(vesc_ethercat_class.master.slaves[i])
                    print('name:{}, Vender ID:{}, Product Code:{}'.format(slaves[i].name, hex(slaves[i].man), hex(slaves[i].id)))

                # PREOP_STATE to SAFEOP_STATE request - each slave's config_func is called
                vesc_ethercat_class.master.config_map()

                # wait 50 ms for all slaves to reach SAFE_OP state
                if vesc_ethercat_class.master.state_check(pysoem.SAFEOP_STATE, 50000) != pysoem.SAFEOP_STATE:
                    vesc_ethercat_class.master.read_state()
                    for slave in vesc_ethercat_class.master.slaves:
                        if not slave.state == pysoem.SAFEOP_STATE:
                            print('{} did not reach SAFEOP state'.format(slave.name))
                            print('al status code {} ({})'.format(hex(slave.al_status),
                                                                pysoem.al_status_code_to_string(slave.al_status)))
                    raise Exception('not all slaves reached SAFEOP state')

                # set master as Operational State
                vesc_ethercat_class.master.state = pysoem.OP_STATE
                vesc_ethercat_class.master.write_state()

                # Check Operational state
                vesc_ethercat_class.master.state_check(pysoem.OP_STATE, 50000)
                if vesc_ethercat_class.master.state != pysoem.OP_STATE:
                    vesc_ethercat_class.master.read_state()
                    for slave in vesc_ethercat_class.master.slaves:
                        if not slave.state == pysoem.OP_STATE:
                            print('{} did not reach OP state'.format(slave.name))
                            print('al status code {} ({})'.format(hex(slave.al_status),
                                                                pysoem.al_status_code_to_string(slave.al_status)))
                    raise Exception('not all slaves reached OP state')

                # 0.1초후 함수 실행
                time.sleep(0.1)
                vesc_ethercat_class.get_vesc_slave_info()
                time.sleep(0.1)
                vesc_ethercat_class.refresh_vesc_ethercat_list(vesc_joint_match, joint_list)
                window.Element('-VESC_TABLE_ETHERCAT-').Update(values=vesc_ethercat_class.vesc_id_data)
            else:
                print("Ethernet Adapter is not selected")

        if event == "Master CLOSE":
            if vesc_ethercat_class is not None:
                if vesc_ethercat_class.master is not None:
                    if proc_ethercat_pdo is not None:
                        if proc_ethercat_pdo.is_alive():
                            ethercat_pdo_multiprocess_stop(window)
                            ethercat_master_close(vesc_ethercat_class)                        
                    print("EtherCAT Master is closed")
                else:
                    print("EtherCAT Master is not opened")
            else:
                print("EtherCAT Master is not opened")

        if event == "Refresh Slaves":
            if vesc_ethercat_class is not None:
                if vesc_ethercat_class.master is not None:
                    vesc_ethercat_class.get_vesc_slave_info()
                    time.sleep(0.1)
                    vesc_ethercat_class.refresh_vesc_ethercat_list(vesc_joint_match, joint_list)
                    window.Element('-VESC_TABLE_ETHERCAT-').Update(values=vesc_ethercat_class.vesc_id_data)
                else:
                    window.Element("-ETHERCAT_STS_MSG-").Update('Please EtherCAT Connect First')
                    print("EtherCAT Master is not opened")
            else:
                print("EtherCAT Master is not opened")

        if event == "Run PDO":
            if vesc_ethercat_class is not None:
                if vesc_ethercat_class.master is not None:
                    if proc_ethercat_pdo is not None:
                        print("EtherCAT PDO Thread Already Started")
                    else:
                        proc_ethercat_pdo = Process(target=ethercat_pdo_multiprocess_func, args=(vesc_ethercat_class,))
                        proc_ethercat_pdo.start()
                        print("EtherCAT PDO Process Start")
                        window.Element("-ETHERCAT_STS_MSG-").Update('EtherCAT PDO Started')

                        rp_class.add_tree_group('PDO Loop')
                        rp_class.add_tree_item('PDO Loop', 'time')
                        rp_class.add_tree_item('PDO Loop', 'freq.')
                else:
                    window.Element("-ETHERCAT_STS_MSG-").Update('Please EtherCAT Connect First')
                    print("EtherCAT Master is not opened")
            else:
                print("EtherCAT Master is not opened")

        if event == "Stop PDO":
            if vesc_ethercat_class is not None:
                if vesc_ethercat_class.master is not None:
                    if proc_ethercat_pdo is not None:
                        ethercat_pdo_multiprocess_stop(window)
                    else:
                        print("EtherCAT PDO is not running.")
                else:
                    window.Element("-ETHERCAT_STS_MSG-").Update('Please EtherCAT Connect First')
                    print("EtherCAT Master is not opened")
            else:
                print("EtherCAT Master is not opened")

        if event == "-ETHERCAT_CMD_DUTY-" or event == "-ETHERCAT_CMD_RELEASE-":
            if proc_ethercat_pdo is not None:
                if proc_ethercat_pdo.is_alive():
                    row = values['-VESC_TABLE_ETHERCAT-']
                    if len(row) != 0:
                        slave_index = row[0]

                        if event == "-ETHERCAT_CMD_DUTY-":
                            send_data = vesc_ethercat_class.ethercat_send_cmd("duty", slave_index, values['-ETHERCAT_CMD_VALUE1-'])
                            #print("set duty {} at slave{}".format(values['-ETHERCAT_CMD_VALUE1-'], slave_index+1))
                        elif event == "-ETHERCAT_CMD_RELEASE-":
                            send_data = vesc_ethercat_class.ethercat_send_cmd("release", slave_index)
                            #print("set release at slave{}".format(slave_index+1))
                        process_data['target_slave'] = slave_index
                        process_data['send_data'] = send_data
                    else:
                        print("EtherCAT Slave is not selected")
                else:
                    print("EtherCAT PDO is not alive")
            else:
                print("EtherCAT PDO is not runing")

        if event == "-ETHERCAT_CMD_CURRENT-" or event == "-ETHERCAT_CMD_CURRENT_BRAKE-":
            if proc_ethercat_pdo is not None:
                if proc_ethercat_pdo.is_alive():
                    row = values['-VESC_TABLE_ETHERCAT-']
                    if len(row) != 0:
                        slave_index = row[0]

                        if event == "-ETHERCAT_CMD_CURRENT-":
                            send_data = vesc_ethercat_class.ethercat_send_cmd("current", slave_index, values['-ETHERCAT_CMD_VALUE2-'])
                            #print("set current {} at slave{}".format(values['-ETHERCAT_CMD_VALUE2-'], slave_index+1))
                        elif event == "-ETHERCAT_CMD_CURRENT_BRAKE-":
                            send_data = vesc_ethercat_class.ethercat_send_cmd("current_brake", slave_index, values['-ETHERCAT_CMD_VALUE2-'])
                            #print("set current brake {} at slave{}".format(values['-ETHERCAT_CMD_VALUE2-'], slave_index+1))
                        process_data['target_slave'] = slave_index
                        process_data['send_data'] = send_data
                    else:
                        print("EtherCAT Slave is not selected")
                else:
                    print("EtherCAT PDO is not alive")
            else:
                print("EtherCAT PDO is not runing")

        if event == "Get Value":
            if proc_ethercat_pdo is not None:
                if proc_ethercat_pdo.is_alive():
                    vesc_ethercat_class.ethercat_send_cmd(event, None)
                else:
                    print("EtherCAT PDO is not runing") 
            else:
                print("EtherCAT PDO is not runing")

        if event == "-ETHERCAT_DEBUG_PRINT_ON-":
            if vesc_ethercat_class is not None:
                if vesc_ethercat_class.master is not None:
                    vesc_ethercat_class.debug_print_get_value_return = True
                    vesc_ethercat_class.debug_print_custom_return = True
                    process_data['debug_print'] = [True, True]
                    print("DEBUG PRINT ON")
                else:
                    print("EtherCAT PDO is not runing")
            else:
                print("EtherCAT master is not opened")

        if event == "-ETHERCAT_DEBUG_PRINT_OFF-":
            if vesc_ethercat_class is not None:
                if vesc_ethercat_class.master is not None:
                    vesc_ethercat_class.debug_print_get_value_return = False
                    vesc_ethercat_class.debug_print_custom_return = False
                    process_data['debug_print'] = [False, False]
                    print("DEBUG PRINT OFF")
                else:
                    print("EtherCAT PDO is not runing")  
            else:
                print("EtherCAT master is not opened")

        if event == "Graph ON":
            if proc_ethercat_pdo is not None:
                if proc_ethercat_pdo.is_alive():
                    graph_update_flag = True
                    print("Graph on", vesc_ethercat_class.controller_id_list)
                    for vesc_id in vesc_ethercat_class.controller_id_list:
                        group_name = 'VESC_ID:{}'.format(vesc_id)
                        try:
                            print("Already registed group",rp_class.treedata.tree_dict[group_name].key)
                        except:
                            rp_class.add_tree_group(group_name)
                            print("Newly regist group",group_name)
                            for i, name in enumerate(vesc_values_names):
                                rp_class.add_tree_item(group_name, name)
                else:
                    print("EtherCAT PDO is not runing")
            
            if vesc_serial_class is not None:
                if vesc_serial_class.periodic_run:
                    graph_update_flag = True
                    print("Graph on", vesc_serial_class.controller_id_list)
                    for vesc_id in vesc_serial_class.controller_id_list:
                        group_name = 'VESC_ID:{}'.format(vesc_id)
                        try:
                            print("Already registed group",rp_class.treedata.tree_dict[group_name].key)
                        except:
                            rp_class.add_tree_group(group_name)
                            print("Newly regist group",group_name)
                            for i, name in enumerate(vesc_values_names):
                                rp_class.add_tree_item(group_name, name)
                else:
                    print("Serial Periodic is not running")
        
        if event == "Graph OFF":
            graph_update_flag = False

        ###### Periodic Update ######
        ethercat_wkc = process_data['ethercat_wkc']
        pdo_loop_time_ms = process_data['loop_pdo_ms']
        pdo_loop_freq_khz = process_data['loop_pdo_khz']
        vesc_values_list = process_data['vesc_values']

        #
        window['-ETHERCAT_STS_MSG-'].update(ethercat_wkc)
        window['-ETHERCAT_LOOP_MS-'].update('{:.3f}ms'.format(pdo_loop_time_ms)) 
        window['-ETHERCAT_LOOP_HZ-'].update('{:.3f}kHz'.format(pdo_loop_freq_khz))
        try:
            window['-SERIAL_LOOP_MS-'].update('{:.3f}ms'.format(vesc_serial_class.loop_time_ms)) 
            window['-SERIAL_LOOP_HZ-'].update('{:.3f}Hz'.format(vesc_serial_class.loop_freq_hz))
        except: None
        
        # graph update
        if graph_update_flag:
            if proc_ethercat_pdo is not None:
                if proc_ethercat_pdo.is_alive():
                    graph_data = {'(PDO Loop) time':pdo_loop_time_ms, '(PDO Loop) freq.':pdo_loop_freq_khz}
                    graph_data['vesc_values_list'] = vesc_values_list
                    rp_class.update_plot(graph_data, values['-SLIDER-DATAPOINTS-'])

            try:
                if vesc_serial_class.periodic_run:
                    graph_data = {'(Serial Loop) time':vesc_serial_class.loop_time_ms, '(Serial Loop) freq.':vesc_serial_class.loop_freq_hz}
                    graph_data['vesc_values_list'] = vesc_serial_class.value_list
                    rp_class.update_plot(graph_data, values['-SLIDER-DATAPOINTS-'])
            except: None

    window.close()