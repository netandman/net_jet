from concurrent.futures import ThreadPoolExecutor
import re
import ipaddress
from pprint import pprint
#from get_info_netbox import GetNetbox
from datetime import datetime
from itertools import repeat
import logging

import yaml
from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)

logging.getLogger('paramiko').setLevel(logging.WARNING)

logging.basicConfig(
    format='%(threadName)s %(name)s %(levelname)s: %(message)s',
    level=logging.INFO,
)

def connect_dev(ipaddr, uname, passw, command, dev_type='cisco_xe'):
    if dev_type == 'cisco_xe':
        device = {'device_type': dev_type,
                  'host': ipaddr,
                  'username': uname,
                  'password': passw,
                  'secret': 'enablepass',
                  "read_timeout_override": 12,
                  }
    else:
        device = {'device_type': dev_type,
                  'host': ipaddr,
                  'username': uname,
                  'password': passw,
                  'secret': 'enablepass',
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
COD_IP - DATA CENTER PUBLIC IP ADDRESS
'''


def check_router_gw(ipaddr, isp_rtr_int, uname, passw, cod_ip="91.217.227.1"):
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
        if cod_ip:
            trace_cod = f"traceroute {cod_ip} source {isp_rtr_int.ip} timeout 1"
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


if __name__ == "__main__":
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = GetNetbox(**credentials['netbox'])
    username, passw = credentials['cisco'].values()
    labs.lab_info("Лаборатория Новосибирск")
    #labs.core_ip()
    #labs.core_isp_intf()
    #print(check_core_intf_isp(str(labs.core_mgmt_ip), str(labs.main_isp_intf), username, passw))
    #labs.router_ip()
    #labs.router_isp_intf()
    #print(check_router_gw(str(labs.router_mgmt_ip), labs.rtr_main_isp_ip, username, passw))
    labs.router_ip()
    labs.router_isp_intf()
    labs.borders_ip()
    pprint(check_rtr_from_borders(labs.borders_dict, labs.rtr_main_isp_ip, username, passw))

