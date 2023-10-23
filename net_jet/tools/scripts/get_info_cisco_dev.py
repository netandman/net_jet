import re
import ipaddress
from pprint import pprint
#from get_info_netbox import GetNetbox
import yaml
from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)


def connect_dev(ipaddr, uname, passw):
    device = {'device_type': 'cisco_ios',
              'host': ipaddr,
              'username': uname,
              'password': passw,
              'secret': 'enablepass',
              }
    try:
        ssh = ConnectHandler(**device)
        return ssh
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
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
    ssh = connect_dev(ipaddr, uname, passw)
    command = "show int " + intf + " | i is|Description|errors"
    output = ssh.send_command(command)
    split_show = output.split('\n')
    regex = (r'^(?P<interface>\S+) is (?P<intf_status>\S+), line protocol is (?P<prot_status>\S+)'
             r'|\s+Description: (?P<description>\S+)'
             r'|\s+\S+ (?P<speed>\S+), media .*'
             r'|\s+(?P<input_errors>\d+) input errors, .*'
             r'|\s+(?P<output_errors>\d+) output errors, .*')
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


def check_router_gw(ipaddr, isp_rtr_int, uname, passw, cod_ip="1.1.1.1"):
    gw_list = []
    ping_dict = {}
    split_trace = ''
    ssh = connect_dev(ipaddr, uname, passw)
    command = "show run | i route 0.0.0.0"
    output = ssh.send_command(command)
    split_show = output.split('\n')
    regex = (r'ip route 0.0.0.0 0.0.0.0 (?P<gateway>\S+) \d+ name .*')
    regex_ping = (r'Success rate is (?P<icmp_percent>\d+)\s+\S+\s+[(]+(?P<icmp_packets>\S+)[)]+'
                  r'.*round-trip min/avg/max = (?P<delay>\S+)\s+\S+'
                  r'|Success rate is (?P<icmp_pcent>\d+)\s+\S+\s+[(]+(?P<icmp_pkts>\S+)[)]+')
    for line in split_show:
        match = re.search(regex, line)
        if match:
            gw_list.append(match.group(match.lastgroup))
    for ip in gw_list:
        # convert ip in ipaddress object to compare with the network range of the router intf
        ip_addr = ipaddress.ip_address(ip)
        if ip_addr in isp_rtr_int.network:
            ping_gw = "ping " + str(ip_addr)
            trace_cod = f"traceroute {cod_ip} source {isp_rtr_int.ip}"
            ping_result = ssh.send_command(ping_gw)
            if cod_ip:
                trace_result = ssh.send_command(trace_cod)
                split_trace = trace_result.split('\n')
            # prepare date to parse by regular expressions regex_ping
            split_ping = ping_result.split('\n')
            for lping in split_ping:
                match_ping = re.search(regex_ping, lping)
                if match_ping:
                    ping_dict = match_ping.groupdict()
            # save raw data
            ping_dict["ping_result"] = ping_result
            ping_dict["ip_addr"] = str(ip_addr)
            ping_dict["trace_result"] = split_trace

    return ping_dict


if __name__ == "__main__":
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = GetNetbox(**credentials['netbox'])
    labs.lab_info("Лаборатория Новосибирск")
    #labs.core_ip()
    #labs.core_isp_intf()
    labs.router_ip()
    labs.router_isp_intf()
    username, passw = credentials['cisco'].values()
    isp_gw_dict = check_router_gw(str(labs.router_mgmt_ip), labs.rtr_main_isp_ip, username, passw)
    print(isp_gw_dict)

