from .general_defines import *
from . import vesc_crc
import ctypes

class VESC_VALUES:
    def __init__(self):
        self.temp_fet = 0
        self.temp_motor = 0
        self.motor_current = 0
        self.input_current = 0
        self.id_current = 0
        self.iq_current = 0
        self.duty = 0
        self.erpm = 0
        self.volt_input = 0
        self.amp_hours = 0
        self.amp_hours_charged = 0
        self.watt_hours = 0
        self.watt_hours_charged = 0
        self.tacho = 0
        self.tacho_abs = 0
        self.fault = 0
        self.pid_pos_now = 0
        self.controller_id = 0
        self.temp_mos1 = 0
        self.temp_mos2 = 0
        self.temp_mos3 = 0
        self.vd_volt = 0
        self.vq_volt = 0

class VESC_PACKET():
    def __init__(self):
        self.value_list = None

        self.debug_print_get_value_return = False
        self.debug_print_custom_return = False

        self.vesc_id_data = []
        self.controller_id_list = []

    def reset_controller_id_list(self):
        del self.controller_id_list[:]

    def packet_encoding(self, comm, comm_value = None):
        start_frame = [2]

        if comm == COMM_PACKET_ID['COMM_CUSTOM_APP_DATA']:
            host = comm_value[0]
            command = comm_value[1]
            vesc_target_id = comm_value[2]
            comm_value = comm_value[3]
            command_frame = [comm, host, 1, vesc_target_id, command]
        elif comm == COMM_PACKET_ID['COMM_FORWARD_CAN']:
            vesc_target_id = comm_value[0]
            command = comm_value[1]
            comm_value = comm_value[2]
            command_frame = [comm, vesc_target_id, command]
        else:
            command = comm
            command_frame = [command]

        data_list = []
        value = None
        if command == COMM_PACKET_ID['COMM_SET_DUTY']:
            value = int(comm_value * 100000.0)
        elif command == COMM_PACKET_ID['COMM_SET_CURRENT']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID['COMM_SET_CURRENT_BRAKE']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID['COMM_SET_RPM']:
            value = int(comm_value)
        elif command == COMM_PACKET_ID['COMM_SET_POS']:
            value = int(comm_value * 1000000.0)
        elif command == COMM_PACKET_ID_OPENROBOT['COMM_SET_DPS']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID_OPENROBOT['COMM_SET_DPS_VMAX']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID_OPENROBOT['COMM_SET_DPS_AMAX']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID_OPENROBOT['COMM_SET_SERVO']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID_OPENROBOT['COMM_SET_TRAJ']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID['COMM_SET_SERVO_POS']:
            value = int(comm_value * 1000.0)
        elif command == COMM_PACKET_ID['COMM_TERMINAL_CMD']:
            comm_value_bytes = comm_value.encode('utf-8')
            for i in range(len(comm_value_bytes)):
                data_list.append(comm_value_bytes[i])
        else:
            value = None

        if value is not None:
            d1 = (value >> 24) & 0xFF
            d2 = (value >> 16) & 0xFF
            d3 = (value >> 8) & 0xFF
            d4 = value & 0xFF
            data_list = [d1, d2, d3, d4]
        
        data_frame = command_frame + data_list
        data_len = [len(data_frame)]

        # To see sending data frame
        #print("data_frame:",data_frame)
        #print("data_len:",data_len)

        arr = (ctypes.c_ubyte * len(data_frame))(*data_frame)
        #crc = crc_vesc.crc16(arr,len(data_frame))
        crc = vesc_crc.crc16(arr,len(data_frame))
        crch = (crc >> 8) & 0xFF
        crcl = crc & 0xFF
        crc_frame = [crch, crcl]
        end_frame = [3]
        data_send = start_frame + data_len + data_frame + crc_frame + end_frame
        return data_send

    def crc_check(self, data_frame, crc_input):
        arr = (ctypes.c_ubyte * len(data_frame))(*data_frame)
        #crc = crc_vesc.crc16(arr,len(data_frame))
        crc = vesc_crc.crc16(arr,len(data_frame))
        crch = (crc >> 8) & 0xFF
        crcl = crc & 0xFF

        #print("{0} {1}",crc_input[0], crch)
        #print("{0} {1}",crc_input[1], crcl)

        if crc_input[0] == crch and crc_input[1] ==crcl:
            #print("crc check - Pass")
            return True
        else:
            print("crc check - Fail")
            print("received crch:{}, crcl:{}, calculated crch:{}, crch{}".format(crc_input[0], crc_input[1],crch,crcl))
            return False

    def get_bytes(self, data, div=1):
        raw_value = int(0)
        length = len(data)
        for i in range(length-1, -1, -1):
            raw_value = raw_value | data[-(i+1)] << 8*i
        #print(hex(raw_value))

        # Negative hex value process
        if length == 4:
            value = status_negative_value_process_4_byte(raw_value)
        elif length == 3:
            value = status_negative_value_process_3_byte(raw_value)
        elif length == 2:
            value = status_negative_value_process_2_byte(raw_value)
        else:
            value = raw_value

        # int value divided by div
        if div == 1:
            result = int(value)
        else:
            result = int(value)/div
        return result

    def set_duty_control(self, vesc_id, value):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_SET_DUTY']
        comm_value = float(value)
        if comm_value <= 1 and comm_value >= -1:
            if vesc_id == 0xFF:
                send_data = self.packet_encoding(comm_set_cmd, comm_value)
            else:
                send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, comm_value])
        else:
            print("Error! command value is out of range [-1,1]")
            send_data = False
        return send_data

    def set_current_control(self, vesc_id, value):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_SET_CURRENT']
        comm_value = float(value)
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, comm_value)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, comm_value])
        return send_data

    def set_current_brake_control(self, vesc_id, value):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_SET_CURRENT_BRAKE']
        comm_value = float(value)
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, comm_value)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, comm_value])
        return send_data

    def set_servo_control(self, vesc_id, value):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_SET_SERVO']
        comm_value = float(value)
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, comm_value)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, comm_value])
        return send_data

    def set_rcservo_pos_control(self, vesc_id, value):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_SET_SERVO_POS']
        comm_value = float(value)
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, comm_value)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, comm_value])
        return send_data

    def set_release(self, vesc_id):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_SET_CURRENT']
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, 0)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, 0])
        return send_data

    def set_alive(self, vesc_id):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_ALIVE']
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, 0)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, 0])
        return send_data  
         
    def get_value(self, vesc_id):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_GET_VALUES']
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, 0)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, 0])
        return send_data

    def get_fw_version(self, vesc_id):
        # prepare data
        comm_set_cmd = COMM_PACKET_ID['COMM_FW_VERSION']
        if vesc_id == 0xFF:
            send_data = self.packet_encoding(comm_set_cmd, 0)
        else:
            send_data = self.packet_encoding(COMM_PACKET_ID['COMM_FORWARD_CAN'], [vesc_id, comm_set_cmd, 0])
        return send_data

    def send_terminal_cmd(self, vesc_id, value):
        # terminal command using CAN_FORWARD
        if vesc_id == 0xFF:
            comm_set_cmd = COMM_PACKET_ID['COMM_TERMINAL_CMD']
            send_data = self.packet_encoding(comm_set_cmd, value)
        else:
            comm_set_cmd = COMM_PACKET_ID['COMM_FORWARD_CAN']
            send_data = self.packet_encoding(comm_set_cmd, [vesc_id, COMM_PACKET_ID['COMM_TERMINAL_CMD'], value])
        return send_data

    def regist_controller_id(self, index, value):
        if index is None:
            self.controller_id_list.append(value['controller_id']) # add new vesc id
            if self.value_list is None:
                self.value_list = [value] # first time
            else:
                self.value_list.append(value) # add value
        else:
            try:    
                self.value_list[index] = value # overwrite value
            except:
                self.value_list.append(value) # add value

    #####
    def pdo_get_id(self, vesc_id):
        comm_set_cmd = COMM_PACKET_ID['COMM_CUSTOM_APP_DATA']
        host_type = OPENROBOT_HOST_TYPE['ETHERCAT']
        command = COMM_PACKET_ID_OPENROBOT['COMM_SET_RELEASE']
        vesc_target_id = vesc_id
        comm_value = 0
        send_data = self.packet_encoding(comm_set_cmd, [host_type, command, vesc_target_id, comm_value])
        return send_data

    #데이터 처리할 함수
    def parsing_data(self, data):
        #print("length:{}, raw data:{}".format(data[1], data))
        #print("raw data hex:",list2hex(data))
        
        # data frame divide
        ind = 0
        start_byte = data[ind]; ind += 1
        len = data[ind]; ind += 1
        data_frame = data[ind:ind+len]; ind += len
        crc_frame = data[ind:ind+2]; ind += 2
        end_byte = data[ind]
    
        #print(start_byte)
        #print(len)
        #print(data_frame)
        #print(crc_frame)
        #print(end_byte)

        # crc_check
        crc_result = self.crc_check(data_frame, crc_frame)
        
        # data parsing
        if start_byte == 2 and end_byte == 3 and crc_result:
            ind_f = 0
            ind_r = len
            command = data_frame[ind_f]; ind_f += 1

            if command == COMM_PACKET_ID['COMM_FW_VERSION']:
                fw_major = data_frame[ind_f]; ind_f += 1
                fw_minor = data_frame[ind_f]; ind_f += 1
                print('VESC Firmware Ver:{0}.{1}'.format(fw_major,fw_minor))

                ind_r -= 1
                hw_type_vesc = data_frame[ind_r]; ind_r -= 1
                fw_test_ver = data_frame[ind_r]; ind_r -= 1
                pairing_done = data_frame[ind_r]; ind_r -= 1
                uuid = data_frame[ind_r-12:ind_r]; ind_r -= 12
                hw_name = data_frame[ind_f:ind_r]

                print("HW_NAME:",list2chr(hw_name))
                print("UUID:",list2hex_nospace(uuid))
                print("pairing_done:",pairing_done)
                print("fw_test_ver:",fw_test_ver)
                print("hw_type_vesc:",hw_type_vesc)
        
            elif command == COMM_PACKET_ID['COMM_PING_CAN']:
                can_connected_id = []
                for i in range(len-1):
                    can_connected_id.append(data_frame[ind_f]); ind_f += 1
                #print("CAN connected ID:",can_connected_id)

                can_id_add_flag = True;
                for id in self.controller_id_list:
                    try:
                        if id == can_connected_id[0]:
                            can_id_add_flag = False
                    except: None
                if can_id_add_flag:
                    self.controller_id_list = self.controller_id_list + can_connected_id
                
                #print("controller_id_list:", self.controller_id_list)

                # initialize value list also 
                #for i in enumerate(self.controller_id_list):
                #    self.value_list.append(VESC_VALUES())

            elif command == COMM_PACKET_ID['COMM_GET_VALUES']:
                values_temp = {}
                values_temp['temp_fet[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['temp_motor[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['motor_current[A]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 100); ind_f += 4
                values_temp['input_current[A]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 100); ind_f += 4
                values_temp['id_current[A]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 100); ind_f += 4
                values_temp['iq_current[A]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 100); ind_f += 4
                values_temp['duty'] = self.get_bytes(data_frame[ind_f:ind_f+2], 1000); ind_f += 2
                values_temp['erpm'] = self.get_bytes(data_frame[ind_f:ind_f+4], 1); ind_f += 4
                values_temp['volt_input[V]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['amp_hours[Ah]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 10000); ind_f += 4
                values_temp['amp_hours_charged[Ah]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 10000); ind_f += 4
                values_temp['watt_hours[Wh]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 10000); ind_f += 4
                values_temp['watt_hours_charged[Wh]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 10000); ind_f += 4
                values_temp['tacho'] = self.get_bytes(data_frame[ind_f:ind_f+4], 1); ind_f += 4
                values_temp['tacho_abs'] = self.get_bytes(data_frame[ind_f:ind_f+4], 1); ind_f += 4
                values_temp['fault'] = self.get_bytes(data_frame[ind_f:ind_f+1]); ind_f += 1
                values_temp['pid_pos_now[deg]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 1000000); ind_f += 4
                values_temp['controller_id'] = self.get_bytes(data_frame[ind_f:ind_f+1]); ind_f += 1
                values_temp['temp_mos1[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['temp_mos2[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['temp_mos3[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['vd_volt[V]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 1000); ind_f += 4
                values_temp['vq_volt[V]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 1000); ind_f += 4     

                index = search_list_value_index(values_temp['controller_id'], self.controller_id_list)
                #print("Controller Id:",values_temp['controller_id'])
                #print("index:{}".format(index))

                self.regist_controller_id(index, values_temp)
                
                #print(self.value_list)

                if self.debug_print_get_value_return:
                    print("Controller Id:",values_temp['controller_id'])
                    print("temp_fet:",values_temp['temp_fet[C]'],"C")
                    print("temp_motor:",values_temp['temp_motor[C]'],"C")
                    print("motor_current:",values_temp['motor_current[A]'],"A")
                    print("input_current:",values_temp['input_current[A]'],"A")
                    print("id_current:",values_temp['id_current[A]'],"A")
                    print("iq_current:",values_temp['iq_current[A]'],"A")
                    print("duty:",values_temp['duty'])
                    print("erpm:",values_temp['erpm'])
                    print("volt_input:",values_temp['volt_input[V]'],"V")
                    print("amp_hours:",values_temp['amp_hours[Ah]'],"Ah")
                    print("amp_hours_charged:",values_temp['amp_hours_charged[Ah]'],"Ah")
                    print("watt_hours:",values_temp['watt_hours[Wh]'],"Wh")
                    print("watt_hours_charged:",values_temp['watt_hours_charged[Wh]'],"Wh")
                    print("tacho:",values_temp['tacho'])
                    print("tacho_abs:",values_temp['tacho_abs'])
                    print("fault:",values_temp['fault'])
                    print("pid_pos_now:",values_temp['pid_pos_now[deg]'],"deg")
                    print("controller_id:",values_temp['controller_id'])
                    print("temp_mos1:",values_temp['temp_mos1[C]'],"C")
                    print("temp_mos2:",values_temp['temp_mos2[C]'],"C")
                    print("temp_mos3:",values_temp['temp_mos3[C]'],"C")
                    print("vd_volt:",values_temp['vd_volt[V]'],"V")
                    print("vq_volt:",values_temp['vq_volt[V]'],"V")     
                    print("---------------------------------------------------") 

            elif command == COMM_PACKET_ID['COMM_CUSTOM_APP_DATA']:
                #print("custom")
                #print("raw data hex:",list2hex(data_frame))

                values_temp = {}
                values_temp['controller_id'] = self.get_bytes(data_frame[ind_f:ind_f+1]); ind_f += 1
                values_temp['pos[rad]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 100); ind_f += 4
                values_temp['vel[rps]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 10000); ind_f += 4
                values_temp['curr[A]'] = self.get_bytes(data_frame[ind_f:ind_f+4], 10000); ind_f += 4
                values_temp['voltage[V]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['temp_motor[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2
                values_temp['temp_mosfet[C]'] = self.get_bytes(data_frame[ind_f:ind_f+2], 10); ind_f += 2

                index = search_list_value_index(values_temp['controller_id'], self.controller_id_list)
                self.regist_controller_id(index, values_temp)

                '''
                if self.debug_print_custom_return:
                    # Local vesc
                    print("==============================================")
                    print("CAN Connected Device Number:",can_devs_num)
                    print("-------------------------------------------")
                    print("Local Controller Id:",controller_id)
                    #print("temp_fet:",temp_fet,"'C")
                    print("temp_motor:",temp_motor,"'C")
                    print("motor_current:",motor_current,"A")
                    #print("input_current:",input_current,"A")
                    #print("duty:",duty)
                    #print("volt_input:",volt_input,"V")
                    #print("watt_hours:",watt_hours,"Wh")
                    #print("watt_hours_charged:",watt_hours_charged,"Wh")
                    print("accum_pos_now:",accum_pos_now,"deg")
                    print("speed:",rps,"rps")
                '''

            elif command == COMM_PACKET_ID['COMM_PRINT']:
                print(bytes(data_frame).decode())