import serial
import serial.tools.list_ports
import time
import signal
import threading
import sys
import ctypes
import platform
import numpy as np
from .vesc_packet import *

######################### USB #########################
def list_serial():
    ports = list(serial.tools.list_ports.comports())
    
    ports_hwid = []
    ports_name = []
    ports_desc = []
    for p in ports:
        if p.vid == 0x0483:
            ports_name.append(p.device)
            ports_desc.append(p.description)
            vid_pid = "{:04x}:{:04x}".format(p.vid, p.pid)
            ports_hwid.append(vid_pid)
    return ports_name, ports_desc, ports_hwid, len(ports_hwid)

class VESC_USB(VESC_PACKET):
    def __init__(self, serial_port_name, serial_port_row_number, window_handler):
        super().__init__()
        self.serial_name = serial_port_name
        self.window = window_handler

        self.line = [] #라인 단위로 데이터 가져올 리스트 변수
        self.exitThread_usb = False   # 쓰레드 종료용 변수
        
        self.usb_port_index = serial_port_row_number
        self.usb_connection_flag = True

        self.last_send_vesc_id = 0xFF

        self.alive_thread = None
        self.periodic_run = False
        self.periodic_freq = 100
        self.periodic_time = 0.02

        self.loop_time_ms = 0
        self.loop_freq_hz = 0

    #쓰레드 종료용 시그널 함수
    def handler_usb(self, signum, frame):
        self.exitThread_usb = True

    # USB RX Thread
    def readThread(self, process_data):
        packet_start_flag = 0
        index = 0
        length = 0

        # 쓰레드 종료될때까지 계속 돌림
        while not self.exitThread_usb:
            #데이터가 있있다면
            for c in self.serial_name.read():           
                #line 변수에 차곡차곡 추가하여 넣는다.
                if c == 2 and packet_start_flag == 0:
                    # start to recv
                    packet_start_flag = 1
                
                if packet_start_flag == 1:
                    # start byte
                    self.line.append(c)
                    packet_start_flag = 2
                elif packet_start_flag == 2:
                    # length byte
                    length = c + 3
                    self.line.append(c)
                    packet_start_flag = 3
                elif packet_start_flag == 3:
                    # remained bytes
                    self.line.append(c)
                    index += 1

                    #print("c:",c)
                    #print("index:",index)
                    #print("length:",length)

                    if c == 3 and length==index:
                        packet_start_flag = 0
                        index = 0
                        length = 0
                        self.parsing_data(self.line)
                        del self.line[:]

    def serial_send_alive(self):
        freq = self.periodic_freq
        sleep_time = 1/freq

        start_time = 0
        prev_time = 0
        self.loop_time_ms = 10
        self.loop_freq_hz = freq
        
        while True:
            prev_time = start_time
            start_time = time.time_ns()
            self.periodic_time = start_time - prev_time
            self.loop_time_ms = self.periodic_time/1000000
            self.loop_freq_hz = 1/self.loop_time_ms*1000

            if self.periodic_run == False:
                break
        
            for vesc in self.vesc_id_data:
                vesc_id = vesc[1]
                vesc_comm = vesc[2]
                self.serial_send_cmd(vesc_id, vesc_comm, "alive")

            #print('{:.3f}ms, {:.3f}Hz'.format(loop_time_ms, loop_freq_hz))

            time.sleep(sleep_time)

    def del_vesc_list(self):
        i = 0
        for i in range(len(self.vesc_id_data)-1, -1, -1):
            vesc_obj = self.vesc_id_data[i]
            if vesc_obj[0] == self.serial_name.port:
                self.vesc_id_data.remove(vesc_obj)

    def get_serial_port_name_from_class(self):
        return self.serial_name.port

    def serial_send_cmd(self, vesc_id, vesc_comm, cmd, value=0):
        if vesc_comm == 'Local':
            vesc_id = 0xFF

        if cmd == "release":
            send_data = self.set_release(vesc_id)
        elif cmd == "alive":
            send_data = self.set_alive(vesc_id)
        elif cmd == "duty":
            send_data = self.set_duty_control(vesc_id, value)
        elif cmd == "current":
            send_data = self.set_current_control(vesc_id, value)
        elif cmd == "current_brake":
            send_data = self.set_current_brake_control(vesc_id, value)
        elif cmd == "servo":
            send_data = self.set_servo_control(vesc_id, value)
        elif cmd == "terminal":
            send_data = self.send_terminal_cmd(vesc_id, value)
        
        # use get value cmd default
        send_data = send_data + self.get_value(vesc_id)

        #
        self.last_send_vesc_id = vesc_id
        self.serial_write(send_data)

    def serial_write(self, data):
        self.serial_name.write(data)         