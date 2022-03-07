import pysoem
import time
from .vesc_packet import *

# PySOEM
class VESC_ETHERCAT(VESC_PACKET):
    def __init__(self, adapter_name, BYTE_NUM):
        super().__init__()
        self.adapter = adapter_name

        self.master = pysoem.Master()
        self.master.in_op = False
        self.master.do_check_state = False
        self.master.open(adapter_name)

        self.BYTE_NUM = BYTE_NUM
        print("EtherCAT Master is opened using", adapter_name)

    '''
    def ethercat_chk_thread():
        # 쓰레드 종료될때까지 계속 돌림
        while not ethercat_chk_thread_stop_event.is_set():
            if vesc_ethercat_class.master.in_op and ((actual_wkc < vesc_ethercat_class.master.expected_wkc) or vesc_ethercat_class.master.do_check_state):
                vesc_ethercat_class.master.do_check_state = False
                vesc_ethercat_class.master.read_state()
                for i, slave in enumerate(vesc_ethercat_class.master.slaves):
                    if slave.state != pysoem.OP_STATE:
                        vesc_ethercat_class.master.do_check_state = True
                        ethercat_check_slave(slave, i)
                if not vesc_ethercat_class.master.do_check_state:
                    window.Element("-ETHERCAT_STS_MSG-").Update('OK : all slaves resumed OPERATIONAL.')
        time.sleep(1)

    def ethercat_check_slave(slave, pos):
            if slave.state == (pysoem.SAFEOP_STATE + pysoem.STATE_ERROR):
                print(
                    'ERROR : slave {} is in SAFE_OP + ERROR, attempting ack.'.format(pos))
                slave.state = pysoem.SAFEOP_STATE + pysoem.STATE_ACK
                slave.write_state()
            elif slave.state == pysoem.SAFEOP_STATE:
                print(
                    'WARNING : slave {} is in SAFE_OP, try change to OPERATIONAL.'.format(pos))
                slave.state = pysoem.OP_STATE
                slave.write_state()
            elif slave.state > pysoem.NONE_STATE:
                if slave.reconfig():
                    slave.is_lost = False
                    print('MESSAGE : slave {} reconfigured'.format(pos))
            elif not slave.is_lost:
                slave.state_check(pysoem.OP_STATE)
                if slave.state == pysoem.NONE_STATE:
                    slave.is_lost = True
                    print('ERROR : slave {} lost'.format(pos))
            if slave.is_lost:
                if slave.state == pysoem.NONE_STATE:
                    if slave.recover():
                        slave.is_lost = False
                        print(
                            'MESSAGE : slave {} recovered'.format(pos))
                else:
                    slave.is_lost = False
                    print('MESSAGE : slave {} found'.format(pos))
    '''

    def get_vesc_slave_info(self):
        # Get vesc slaves info
        for slave in self.master.slaves:
            # erase output buffer first
            output_tmp = bytearray([0 for i in range(self.BYTE_NUM)])
            slave.output = bytes(output_tmp)
            # load data
            send_data = self.pdo_get_id(0xFF) #self.get_fw_version(0xFF) #self.get_value(0xFF)
            for i in range(len(send_data)):
                output_tmp[i] = send_data[i]
            slave.output = bytes(output_tmp)

        #vec.packet_class.debug_print_get_value_return = True
        #vec.packet_class.debug_print_custom_return = True

        self.master.send_processdata()
        self.master.receive_processdata()

        for slave in self.master.slaves:
            self.ethercat_Slave_Read_Rxdata(slave.input)
        
        #for vesc_id in self.controller_id_list:
        #    print("vesc id:{}".format(vesc_id))

    def refresh_vesc_ethercat_list(self, joint_predefined_list, joint_list):
        self.vesc_id_data.clear()
        
        ###
        ids = self.controller_id_list
        #print(ids)
        if len(ids) != 0:
            for i in range(len(ids)):
                try:
                    if i == 0:
                        if joint_predefined_list[ids[i]] is not None: 
                            self.vesc_id_data.append([self.adapter, ids[i], "SLAVE{}".format(i+1), joint_predefined_list[ids[i]]])
                    else:
                        if joint_predefined_list[ids[i]] is not None: 
                            self.vesc_id_data.append([self.adapter, ids[i], "SLAVE{}".format(i+1), joint_predefined_list[ids[i]]])
                except:
                    if i == 0:
                        self.vesc_id_data.append([self.adapter, ids[i], "SLAVE{}".format(i+1), joint_list[i]])
                        print("Joint number of vesc id:", ids[i], "is not pre-defined")
                    else:
                        self.vesc_id_data.append([self.adapter, ids[i], "SLAVE{}".format(i+1), joint_list[i]])
                        print("Joint number of vesc id:", ids[i], "is not pre-defined")
            #print(vesc_packet_usb.vesc_id_data)

    def ethercat_send_cmd(self, cmd, value=0):
        vesc_id = 0xFF

        comm_set_cmd = COMM_PACKET_ID['COMM_CUSTOM_APP_DATA']
        host_type = OPENROBOT_HOST_TYPE['ETHERCAT']

        send_data = []
        if cmd == "duty":
            command = COMM_PACKET_ID['COMM_SET_DUTY']
            set_value = float(value)
        elif cmd == "current":
            command = COMM_PACKET_ID['COMM_SET_CURRENT']
            set_value = float(value)
        elif cmd == "current_brake":
            command = COMM_PACKET_ID['COMM_SET_CURRENT_BRAKE']
            set_value = float(value)
        elif cmd == "release":
            command = COMM_PACKET_ID['COMM_SET_CURRENT']   
            set_value = 0

        send_data = self.packet_encoding(comm_set_cmd, [host_type, command, vesc_id, set_value])
        return send_data

    def ethercat_Slave_Read_Rxdata(self, data):
        packet = []
        for i in range(len(data)):
            packet.append(data[i])
        self.parsing_data(packet)
        
    def ethercat_Master_Load_Txdata(self, target_slave_num, data):
        # erase output buffer first
        output_tmp = bytearray([0 for i in range(self.BYTE_NUM)])
        self.master.slaves[target_slave_num].output = bytes(output_tmp)
        # load data
        for i in range(len(data)):
            output_tmp[i] = data[i]    
        self.master.slaves[target_slave_num].output = bytes(output_tmp)
        