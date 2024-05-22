from concurrent.futures import ThreadPoolExecutor
import re
import ipaddress
import time
import socket
from pprint import pprint

import textfsm

# from get_info_netbox import GetNetbox
import dotenv
from datetime import datetime
from itertools import repeat
import logging
import asyncio
from scrapli import AsyncScrapli
from scrapli.exceptions import ScrapliException
from pprint import pprint
import os
import paramiko
from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)

dotenv.load_dotenv()

logging.getLogger('paramiko').setLevel(logging.WARNING)

logging.basicConfig(
    format='%(threadName)s %(name)s %(levelname)s: %(message)s',
    level=logging.INFO,
)

base_dir = os.path.dirname(os.path.abspath(__file__))


def connect_dev(ipaddr, uname, passw, command, dev_type='cisco_xe'):
    if dev_type == 'cisco_xe':
        device = {'device_type': dev_type,
                  'host': ipaddr,
                  'username': uname,
                  'password': passw,
                  'secret': 'enablepass',
                  "read_timeout_override": 16,
                  }
    else:
        device = {'device_type': dev_type,
                  'host': ipaddr,
                  'username': uname,
                  'password': passw,
                  'secret': 'enablepass',
                  "read_timeout_override": 90,
                  }
    start_msg = '===> {} Connection: {}'
    received_msg = '<=== {} Received:   {}'
    ip = device['host']
    logging.info(start_msg.format(datetime.now().time(), ip))
    try:
        if type(command) is list:
            result_list = []
            for cmd in command:
                with ConnectHandler(**device) as ssh:
                    result_list.append(ssh.send_command(cmd))
                    logging.info(received_msg.format(datetime.now().time(), ip))
            return result_list
        else:
            with ConnectHandler(**device) as ssh:
                result = ssh.send_command(command)
                logging.info(received_msg.format(datetime.now().time(), ip))
            return result
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        logging.warning(error)
        return error


def snr_connect_dev_paging(
    ip,
    username,
    password,
    command,
    enable="enable",
    max_bytes=60000,
    short_pause=1,
    long_pause=5,
):
    cl = paramiko.SSHClient()
    cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cl.connect(
        hostname=ip,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
    )
    with cl.invoke_shell() as ssh:
        # ssh.send("enable\n")
        # ssh.send(enable + "\n")
        time.sleep(short_pause)
        ssh.recv(max_bytes)

        # result = {}
        ssh.send(f"{command}\n")
        ssh.settimeout(5)

        output = ""
        while True:
            try:
                page = ssh.recv(max_bytes).decode("utf-8")
                output += page
                time.sleep(0.5)
            except socket.timeout:
                break
            if "More" in page:
                ssh.send(" ")
        output = re.sub(" +--More--| +\x08+ +\x08+", "\n", output)
        # result[command] = outputs

    return output

'''
CONNECT TO DEVICE ACCORDING TO IPADDR AND SEND SHOW COMMAND
THEN PARSING THE SHOW COMMAND RESULT BY REGULAR EXPRESSIONS AND THE METHOD SEARCH

CONNECTION ATTRIBUTES
IPADDR - CORE MGMT IP ADDRESS
INTF - CORE INTERNET PROVIDER INTERFACES
UNAME - USERNAME
PASSW - PASSWORD
'''


def check_core_intf_isp(ipaddr, intf, uname, passw):
    errors_dict = {}
    regex = (r'^(?P<interface>\S+) is (?P<intf_status>\S+), line protocol is (?P<prot_status>\S+)'
             r'|\s+Description: (?P<description>\S+)'
             r'|\s+\S+ (?P<speed>\S+), media .*'
             r'|\s+(?P<input_errors>\d+) input errors, .*'
             r'|\s+(?P<output_errors>\d+) output errors, .*')
    command = "show int " + intf + " | i is|Description|errors"
    output = connect_dev(ipaddr, uname, passw, command, dev_type='cisco_ios')
    split_show = output.split('\n')
    for line in split_show:
        match = re.search(regex, line)
        if match:
            # compare the last group of the expression with string prot_status to catch first 3 groups of regex
            if match.lastgroup == 'prot_status':
                errors_dict = match.groupdict()
            else:
                # add last group name and the value of the group
                errors_dict[match.lastgroup] = match.group(match.lastgroup)
    # add raw value
    errors_dict["output"] = output
    return errors_dict


'''
CONNECT TO THE DEVICE WITH IPADDR AND SEND COMMAND TO GET INFO OF DEFAULT ROUTS
THEN PARSING THE RESULT BY THE REGULAR EXPRESSION
ADD THE GW ADDRESS FROM RUN CONFIG TO THE GW LIST
AFTER THAT WE COMPARE THE NETWORK OF ROUTER INTERFACE ADDRESS 
IF GW IP INCLUDED IN THIS RANGE WE USE .IP METHOD TO INCLUDE THE ADDRESS IN ICMP COMMAND
THEN PARSING THE PING COMMAND RESULT TO CREATE A DICTIONARY WITH KEYS

CONNECTION ARGUMENTS
IPADDR - ROUTER MGMT IP ADDRESS 
ISP_RTR_INT - ROUTER PUBLIC IP ADDRESS
UNAME - USERNAME
PASSW - PASSWORD
PUBLIC_IP - PUBLIC IP ADDRESS (FOR EXAMPLE COD IP ADDRESS)
'''


def check_router_gw(ipaddr, isp_rtr_int, uname, passw, public_ip="91.217.227.1"):
    ping_dict = {}
    regex = (r'ip route 0.0.0.0 0.0.0.0 (?P<gateway>\S+) \d+ name .*')
    regex_ping = (r'Success rate is (?P<icmp_percent>\d+)\s+\S+\s+[(]+(?P<icmp_packets>\S+)[)]+'
                  r'.*round-trip min/avg/max = (?P<delay>\S+)\s+\S+'
                  r'|Success rate is (?P<icmp_pcent>\d+)\s+\S+\s+[(]+(?P<icmp_pkts>\S+)[)]+')
    command = "show run | i route 0.0.0.0"
    output = connect_dev(ipaddr, uname, passw, command, dev_type='cisco_ios')
    split_show = output.split('\n')
    gw_list = [match.group('gateway') for line in split_show if (match := re.search(regex, line))]
    for ip in gw_list:
        # convert ip in ipaddress object to compare with the network range of the router intf
        ip_addr = ipaddress.ip_address(ip)
        if ip_addr in isp_rtr_int.network:
            ping_gw = "ping " + str(ip_addr)
            ping_result = connect_dev(ipaddr, uname, passw, ping_gw)
            # prepare date to parse by regular expressions regex_ping
            split_ping = ping_result.split('\n')
            for lping in split_ping:
                match_ping = re.search(regex_ping, lping)
                if match_ping:
                    ping_dict = match_ping.groupdict()
            # save raw data
            ping_dict["ping_result"] = ping_result
            ping_dict["ip_addr"] = str(ip_addr)
        if public_ip:
            trace_cod = f"traceroute {public_ip} source {isp_rtr_int.ip} timeout 1"
            trace_result = connect_dev(ipaddr, uname, passw, trace_cod)
            split_trace = trace_result.split('\n')
            # save raw data
            ping_dict["trace_result"] = split_trace
    return ping_dict


'''
CONCURRENT CONNECTION TO THE BORDER DEVICES FOR GETTING A ROUTE AND TRACE THE ISP IP ADDRESS
THEN ADD THE DATA IN DATA DICTIONARY WITH A KEY SUCH AS A BORDER HOSTNAME
AFTER THAT COMPARE THE STRINGS OF SPLIT RESULTS WITH THE REGEX EXPRESSION AND ADD MATCHED VALUES TO THE DATA DICTIONARY
'''


def check_rtr_from_borders(borders_dict, isp_rtr_int, uname, passw):
    borders_list = []
    regex = (r'Routing entry for (?P<route>\S+).*'
             r'|Last update from \S+ (?P<date_update>\S+) ago')
    # connection to the devices
    with ThreadPoolExecutor(max_workers=4) as executor:
        data = {}
        # get the value of the borders_dict to make commands
        for key, val in borders_dict.items():
            commands = [f"trace {isp_rtr_int.ip} source {val['as_intf']} timeout 1",
                        f"show ip route {isp_rtr_int.ip}"]
            # make borders list with borders ip addresses for thread pool executor
            borders_list.append(val['mgmt_ip'])
        result = executor.map(connect_dev, borders_list, repeat(uname), repeat(passw), repeat(commands))
    # split values to mach the result with device
    for device, output in zip(borders_list, result):
        for brd, vl in borders_dict.items():
            if vl['mgmt_ip'] == device:
                # generate the devices dictionary, split method to make list of string and help parsing
                data[brd] = {'mgmt_ip': device,
                             **{'trace': out_line.split('\n') for out_line in output if "Tracing" in out_line},
                             **{'route': out_line.split('\n') for out_line in output if "Routing" in out_line}}
    for key, val in data.items():
        for line in val['route']:
            match = re.search(regex, line)
            if match:
                data[key][match.lastgroup] = match.group(match.lastgroup)
    return data


'''
FUNCTION TO PARSE THE RESULT OF SHOW INTERFACE COMMAND
ACCORDING TO THE RESULT OF THE COMMAND CREATE A DICIONARY
COMPARE THE AGING TIME WITH OPTION PERIOD THAT HAS DEFAULT VALUE 7 WEEKS
EXAMPLE:
{'C2960_xxx_02': {'FastEthernet0': {'status': 'down', 'last_input': 'never', 'last_output': 'never,'}}
{'S2985_xxx_21': {'Ethernet1/0/1': {'status': 'down', 'status_change': '5w-2d-2h-10m-11s'}}
'''


def parsing_intf(switches_dict, uname, passw, command="show interface", period=7):
    commands = command  # if command will be list the function handles it correctly
    result_dict = {}
    dev_type = 'cisco_ios'
    cisco_match = ["C2960", "C3750", "C9200"]
    regex_cisco = (r'(?P<intf>\S+) is (?P<status>\S+), line protocol is down.+?Last input (?P<last_input>\S+), output (?P<last_output>\S+)')
    regex_snr = (r'(?P<intf>Ethernet\S+) is (?P<status>\S+), line protocol is down.+?Time since last status change:(?P<status_change>\S+)')
    regex_age = (r'(?P<weeks>\d+)w(?P<days>\d+)d')
    '''
    - get ip addresses of the switches_dict to make commands
    - make switches list with ip addresses for thread pool executor
    - because of the key is a netbox object we should to change type of the key
    - we also should to distribute cisco and snr switches to different lists
    for using different switch connection functions
    '''
    cisco_sw_mgmt_ip = [val['mgmt_ip'] for key, val in switches_dict.items() if str(key) in cisco_match]
    snr_sw_mgmt_ip = [val['mgmt_ip'] for key, val in switches_dict.items() if str(key) not in cisco_match]
    with ThreadPoolExecutor(max_workers=4) as executor:
        result_cisco = list(executor.map(connect_dev, cisco_sw_mgmt_ip, repeat(uname), repeat(passw), repeat(commands),
                                         repeat(dev_type)))
        result_snr = list(executor.map(snr_connect_dev_paging, snr_sw_mgmt_ip, repeat(uname), repeat(passw), repeat(commands)))

        result = result_cisco + result_snr

        # cisco_sw_mgmt_ip.extend(snr_sw_mgmt_ip)
    for device, output in zip(cisco_sw_mgmt_ip + snr_sw_mgmt_ip, result):
        for sw, vl in switches_dict.items():
            if vl['mgmt_ip'] == device:
                # change format sw from pynetbox.models.dcim.Devices to string
                sw = str(sw)
                # generate the devices dictionary, split method to make list of string and help parsing
                if any(x in sw for x in cisco_match):
                    result_dict[sw] = {}
                    match = re.finditer(regex_cisco, output, re.DOTALL)
                    for m in match:
                        if "never" in m.group('last_input') or "never" in m.group('last_output'):
                            result_dict[sw][m.group('intf')] = {'status': m.group('status'),
                                                                'last_input': m.group('last_input'),
                                                                'last_output': m.group('last_output')}
                        elif "w" in m.group('last_input') or "w" in m.group('last_output'):
                            match_input = re.search(regex_age, m.group('last_input'))
                            match_output = re.search(regex_age, m.group('last_output'))
                            if match_input and match_output:
                                if int(match_input.group('weeks')) and int(match_output.group('weeks')) >= period:
                                    result_dict[sw][m.group('intf')] = {'status': m.group('status'),
                                                                        'last_input': m.group('last_input'),
                                                                        'last_output': m.group('last_output')}
                        else:
                            result_dict[sw][m.group('intf')] = {'status': m.group('status'),
                                                                'last_input': 'None',
                                                                'last_output': 'None'}

                else:
                    # print("SNR pattern!")
                    result_dict[sw] = {}
                    match = re.finditer(regex_snr, output, re.DOTALL)
                    for m in match:
                        age_list = m.group('status_change').split('-')
                        age = int(age_list[0].rstrip('w'))
                        if age >= period:
                            result_dict[sw][m.group('intf')] = {'status': m.group('status'),
                                                                'status_change': m.group('status_change')}
    return result_dict


'''
PREPARE A DICTIONARY FOR SCRAPLI CONNECTION TO DEVICES
'''


def gener_dev_dict(devices, uname, passw):
    dev_dict = {"cisco": {}, "snr": {}}
    cisco_match = ["C3560", "C2960", "C3750", "C9200", "C3850", "C9300"]
    dev_template = {
    "auth_username": uname,
    "auth_password": passw,
    # "auth_secondary": passw, # to send enable cmd
    "default_desired_privilege_level": "exec",  # Set the desired privilege level to 'exec'
    "auth_strict_key": False,
    "platform": "cisco_iosxe",
    "timeout_socket": 20,  # timeout for establishing socket/initial connection in seconds
    "timeout_transport": 40,  # timeout for ssh|telnet transport in seconds
    "transport": "asyncssh",
    # some net devices don't connect by ssh default algs and requier specific key and encrypt algs
    "transport_options": {"asyncssh": {"kex_algs": ["diffie-hellman-group-exchange-sha1", "diffie-hellman-group14-sha1",
                                                    "diffie-hellman-group1-sha1"],
                                       "encryption_algs": ["aes128-ctr", "aes192-ctr",
                                                           "aes256-ctr", "aes256-cbc", "aes192-cbc", "aes128-cbc",
                                                           "3des-cbc"]}}
    }
    '''
    because there are 2 device types and different output results 
    it requires 2 different dictionary for cisco and snr
    '''
    for dev, key in devices.items():
        if any(item in str(dev) for item in cisco_match):
            dev_dict['cisco'][str(dev)] = {'host': key['mgmt_ip']}
            dev_dict['cisco'][str(dev)].update(dev_template)
        else:
            dev_dict['snr'][str(dev)] = {'host': key['mgmt_ip']}
            dev_dict['snr'][str(dev)].update(dev_template)

    return dev_dict


'''
THE FUNCTION TO SEND SHOW COMMANDS TO DEVICES
'''


async def send_show(device_dict, hostname, show_commands, txtfsm=True):
    cmd_dict = {}
    cmd_dict_parse = {}
    cisco_match = ["C3560", "C2960", "C3750", "C9200", "C3850", "C9300"]
    if type(show_commands) == str:
        show_commands = [show_commands]
    try:
        async with AsyncScrapli(**device_dict) as ssh:
            for cmd in show_commands:
                reply = await ssh.send_command(cmd)
                cmd_dict[hostname] = reply.result
                '''
                because scrapli textfsm doesn't parse the output of snr device 
                it requires to separate raw data and parse data
                '''
                if txtfsm is True and any(item in hostname for item in cisco_match):
                    cmd_dict_parse[hostname] = reply.textfsm_parse_output()
        if cmd_dict_parse:
            return cmd_dict_parse
        else:
            return cmd_dict
    except ScrapliException as error:
        print(error, device_dict["host"])


'''
TFSM_PARSE_TEMPLATE IS USING FOR PARSING RAW DATA FROM DEVICES BY SPECIAL FSM TEMPLATE FILE
IT RETURNS THE LIST OF DICTIONARIES THAT HAS STRUCTURE LIKE THIS:

[{DEVICE_HOSTNAME: [KEY: VALUE]}]   
'''


def tfsm_parse_template(file_path, dict_list):
    parsed_result_list = []
    device_result_list = []
    with open((os.path.join(base_dir, file_path)),
              encoding="utf-8") as template:
        fsm = textfsm.TextFSM(template)
        fsm_list = [{dev: fsm.ParseText(raw) for dev_dict in dict_list for dev, raw in dev_dict.items()}]
    '''
    the result above should be change from list values to dictionaries
    this is because we get fsm header as a key and its value
    '''
    for devices in fsm_list:
        for key, value in devices.items():
            for item in value:
                parsed_item = {fsm.header[i]: val for i, val in enumerate(item)}
                parsed_result_list.append(parsed_item)
            device_result_list.append({key: parsed_result_list})
    return device_result_list


'''
THE FUNCTION SEND SHOW INTERFACE STATUS TO CISCO DEVICES AND SHOW INTERFACE ETHERNET STATUS TO SNR DEVICES
BY SEND_SHOW FUNCTION AND RETURNS THE LIST OF DICTIONARIES
EXAMPLE:
[{'C2960_XXX_01': [{'duplex': 'a-full',
                            'fc_mode': '',
                            'name': '',
                            'port': 'Fa0/1',
                            'speed': 'a-100',
                            'status': 'connected',
                            'type': '10/100BaseTX',
                            'vlan_id': '111'},...]
 {'S2985_XXX_25': [{'duplex': 'a-FULL',
                             'name': '',
                             'port': '1/0/1',
                             'speed': 'a-1G',
                             'status': 'UP/UP',
                             'type': 'G-TX',
                             'vlan': '222'},...]]
'''


async def send_sh_int_status(devices, commands='show interface status',
                             snr_cmds='show int ethernet status'):
    result_list = []
    if devices["cisco"]:
        coroutines = [send_show(val, device, commands) for device, val in devices["cisco"].items()]
        result_list = await asyncio.gather(*coroutines)
    '''
    for snr devices implement the special template to get list of interface values
    '''
    if devices["snr"]:
        coroutines = [send_show(val, device, snr_cmds, txtfsm=False) for device, val in devices["snr"].items()]
        result_snr = await asyncio.gather(*coroutines)
        result_list = tfsm_parse_template("textfsm_templates/snr_parse_sh_int_eth_stat.template",
                                              result_snr)
        # result_list.append(snr_result_list)
    return result_list


'''
THE FUNCTION GET_MAC_ARP RETURNS THE RESULT BELOW:
{'core': [{'age': '73',
           'ip_addr': '172.16.230.139',
           'mac_addr': 'e454.e8bc.9e08',
           'vlan_id': '144'}]}
'''


async def get_mac_arp(core_dict, device_dict, interface):
    # cisco_match = ["C3560", "C2960", "C3750", "C9200", "C3850", "C9300"]
    snr_template_path = "textfsm_templates/snr_parse_sh_mac_add_intf_ether.template"
    cisco_template_path = "textfsm_templates/cisco_parse_sh_ip_arp.template"
    if device_dict['cisco']:
        device_name = ''
    # if any(item in device_name for item in cisco_match):
        for device, val in device_dict['cisco'].items():
            device_name = str(device)
        cmd_sh_mac = f'show mac address-table interface {interface}'
        show_mac_addr = await send_show(device_dict['cisco'][device_name], device_name, cmd_sh_mac, txtfsm=True)
        mac_addr = show_mac_addr[device_name][0]['destination_address']
    else:
        device_name = ''
        cmd_sh_mac = f'show mac-address-table interface eth{interface}'
        '''
        send_show function will return 
        {'S2985_xxx_08': 'Vlan Mac Address                 Type    Creator   Ports
        ---- --------------------------- ------- -------------------------------------
        444  1c-2c-3b-4c-5e-64           DYNAMIC Hardware Ethernet1/0/1'}
        '''
        for device, val in device_dict['snr'].items():
            device_name = str(device)
        show_mac_addr = await send_show(device_dict['snr'][device_name], device_name, cmd_sh_mac, txtfsm=False)
        '''
        add function tfsm_parse_template attributes such as path template file and 
        the result of send_show command such as list because the function tfsm handles 
        this attrib and adapted for dictionary list of devices
        
        return the result below:
        {'S2985_xxx_0x': [{'destination_address': '1c-2c-3b-4d-5e-6f',
                           'destination_port': ['Ethernet1/0/1'],
                           'type': 'DYNAMIC',
                           'vlan_id': '444'}]}
        '''
        snr_dict_list = tfsm_parse_template(snr_template_path, [show_mac_addr])
        mac_addr = snr_dict_list[0].get(device_name, [{}])[0].get('destination_address')
    cmd_sh_arp = f'show ip arp {mac_addr}'
    show_ip_arp_addr = await send_show((list(core_dict.values()))[0], 'core', cmd_sh_arp, txtfsm=False)
    '''
    implementing the textfsm templates to get the result below
    {'core': {'age': '68',
          'ip_addr': '1.2.3.4',
          'mac_addr': '1a2b.3c4d.5e6f',
          'vlan_id': '444'}}
    '''
    cisco_dict_list = tfsm_parse_template(cisco_template_path, [show_ip_arp_addr])
    return cisco_dict_list[0]


async def get_inactive_intf(devices, commands='show interface', period=7):
    result = {}
    # result_list = []
    regex_age = (r'(?P<weeks>\d+)w(?P<days>\d+)d')
    snr_template_path = "textfsm_templates/snr_parse_sh_intf.template"
    if devices["cisco"]:
        coroutines = [send_show(val, device, commands) for device, val in devices["cisco"].items()]
        result_list = await asyncio.gather(*coroutines)
        for sw_dict in result_list:
            for key, val_list in sw_dict.items():
                result[key] = {}
                for values in val_list:
                    if "w" in values['last_input'] or "w" in values['last_output']:
                        match_input = re.search(regex_age, values['last_input'])
                        match_output = re.search(regex_age, values['last_output'])
                        if match_input and match_output:
                            if int(match_input.group('weeks')) and int(match_output.group('weeks')) >= period:
                                result[key][values['interface']] = {'status': values['link_status'],
                                                                    'last_input': values['last_input'],
                                                                    'last_output': values['last_output']}
                    elif "never" in values['last_input'] and "never" in values['last_output']:
                        result[key][values['interface']] = {'status': values['link_status'],
                                                            'last_input': values['last_input'],
                                                            'last_output': values['last_output']}
    if devices["snr"]:
        coroutines = [send_show(val, device, commands, txtfsm=False) for device, val in devices["snr"].items()]
        result_snr = await asyncio.gather(*coroutines)
        '''
        for snr devices implement the special template to get list of interface values
        '''
        result_list = tfsm_parse_template(snr_template_path, result_snr)
        for sw_dict in result_list:
            for key, val_list in sw_dict.items():
                result[key] = {}
                for values in val_list:
                    age_list = values['status_change'].split('-')
                    age = int(age_list[0].rstrip('w'))
                    if age >= period:
                        result[key][values['port']] = {'status': values['status'],
                                                       'status_change': values['status_change']}
    return result
