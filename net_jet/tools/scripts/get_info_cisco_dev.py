import re
from get_info_netbox import GetNetbox
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


def intf_isp_main(ipaddr, uname, passw):
    result = {}
    ssh = connect_dev(ipaddr, uname, passw)
    command = "show int description | i ISP"
    output = ssh.send_command(command)
    #match = re.search(r'')
    #result[command] = output
    return output


if __name__ == "__main__":
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = GetNetbox(**credentials['netbox'])
    labs.lab_info("Лаборатория Казахстан")
    labs.core_ip()
    username, passw = credentials['cisco'].values()
    print(intf_isp_main(str(labs.core_intf.ip), username, passw))
