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
        print(error)
        return error

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
            if match.lastgroup == 'prot_status':
                errors_dict = match.groupdict()
            else:
                errors_dict[match.lastgroup] = match.group(match.lastgroup)
    errors_dict["output"] = output
    return errors_dict


def check_router_gw(ipaddr, isp_gw, uname, passw):
    gw_list = []
    ping_dict = {}
    '''
    далее методами ipaddress сравнить в какой диапазон входит какой адрес шлюза и исходя из этого 
    или вернуть соотношения провайдер шлюз или выполнить пинг и вернуть результат 
    '''
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
        ip_addr = ipaddress.ip_address(ip)
        if ip_addr in isp_gw.network:
            ping_gw = "ping " + str(ip_addr)
            ping_result = ssh.send_command(ping_gw)
            split_ping = ping_result.split('\n')
            for lping in split_ping:
                match_ping = re.search(regex_ping, lping)
                if match_ping:
                    ping_dict = match_ping.groupdict()
            ping_dict["ping_result"] = ping_result
            ping_dict["ip_addr"] = str(ip_addr)
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

