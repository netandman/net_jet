import ipaddress
from pprint import pprint


def get_net(ip_addr, net_pfx):
    user_pfx = f'{ip_addr}/{net_pfx}'
    net = ipaddress.ip_interface(user_pfx)
    net_dict = {'network': str(net.network),
                'broadcast': str(net.network.broadcast_address),
                'num_address': net.network.num_addresses,
                'with_netmask': net.network.with_netmask,
                'with_hostmask': net.network.with_hostmask}
    return net_dict
