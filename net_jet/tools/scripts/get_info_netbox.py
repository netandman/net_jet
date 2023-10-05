import pynetbox
from pprint import pprint
import ipaddress
import yaml


class GetNetbox:

    def __init__(self, url, token):
        self.nb = pynetbox.api(url=url, token=token)
        self.nb.http_session.verify = False

    def get_tenants(self, tag):
        all_tenants = self.nb.tenancy.tenants.filter(tag=tag)
        self.all_tenants = list(all_tenants)

    def lab_info(self, lab_name):
        tenant_get = self.nb.tenancy.tenants.get(name=lab_name)
        self.lab_id = tenant_get.id
        self.lab_slug = tenant_get.slug

    def isp_lab(self):
        circuits = self.nb.circuits.circuits.filter(tenant_id=self.lab_id)
        crts_dict = {}
        isp_dict = {}
        for circuit in circuits:
            isp_get = self.nb.circuits.circuits.get(cid=circuit)
            crts_dict[isp_get] = {"crts_name": isp_get.display, "provider_id": isp_get.provider.id}
            isp_dict[isp_get.cid] = dict(self.nb.circuits.providers.get(id=isp_get.provider.id))
        self.isp_dict = isp_dict

    def core_lab(self):
        core = self.nb.dcim.devices.filter(tenant_id=self.lab_id, tag="core")
        core_get = self.nb.dcim.devices.get(name=core)
        core_intf_filter = self.nb.dcim.interfaces.filter(device_id=core_get.id, description="mgmt")
        mgmt_vlan_intf = ((list(core_intf_filter))[0])
        core_mgmt_intf = self.nb.dcim.interfaces.get(name=mgmt_vlan_intf, device_id=core_get.id)
        self.core_intf = core_mgmt_intf
        """
        {'id': 1776, 'url': 'http://172.17.8.130:8085/api/dcim/interfaces/1776/', 'display': 'Vlan10', 'device': {'id': 1731, 'url': 'http://172.17.8.130:8085/api/dcim/devices/1731/', 'display': 'C9300_AlmatyLab_Core', 'name': 'C9300_AlmatyLab_Core', 'display_name': 'C9300_AlmatyLab_Core'}, 'name': 'Vlan10', 'label': '', 'type': {'value': 'virtual', 'label': 'Virtual'}, 'enabled': True, 'parent': None, 'lag': None, 'mtu': None, 'mac_address': None, 'mgmt_only': False, 'description': 'mgmt', 'mode': {'value': 'tagged', 'label': 'Tagged'}, 'untagged_vlan': None, 'tagged_vlans': [{'id': 13, 'url': 'http://172.17.8.130:8085/api/ipam/vlans/13/', 'display': 'MGMT (10)', 'vid': 10, 'name': 'MGMT', 'display_name': 'MGMT (10)'}], 'mark_connected': False, 'cable': None, 'cable_peer': None, 'cable_peer_type': None, 'connected_endpoint': None, 'connected_endpoint_type': None, 'connected_endpoint_reachable': None, 'tags': [], 'custom_fields': {}, 'created': '2021-09-05', 'last_updated': '2023-10-02T14:53:26.989533+03:00', 'count_ipaddresses': 1, '_occupied': False}
        """

    def core_ip(self):
        core_ipaddr_filter = self.nb.ipam.ip_addresses.filter(tenant_id=self.lab_id, description="mgmt")
        mgmt_int = ipaddress.ip_interface((list(core_ipaddr_filter))[0])
        mgmt_subnet = mgmt_int.network
        core_ipaddr_get = self.nb.ipam.ip_addresses.get(address=mgmt_int.ip, mask_length=mgmt_subnet.prefixlen)
        self.core_intf = mgmt_int
        self.core_ip_dict = core_ipaddr_get

    def core_isp_intf(self):
        core = self.nb.dcim.devices.filter(tenant_id=self.lab_id, tag="core")
        core_get = self.nb.dcim.devices.get(name=core)
        main_isp_intf = self.nb.dcim.interfaces.get(tag="isp_main", device_id=core_get.id)
        backup_isp_inf = self.nb.dcim.interfaces.get(tag="isp_backup", device_id=core_get.id)
        self.main_isp_intf = main_isp_intf
        self.backup_isp_intf = backup_isp_inf


if __name__ == "__main__":
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = GetNetbox(**credentials['netbox'])
    #labs.get_tenants("lab")
    #labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
    labs.lab_info("Лаборатория Казахстан")
    labs.isp_lab()
    #labs.core_lab()
    labs.core_ip()
    labs.core_isp_intf()
    print(labs.isp_dict)
    #labs_cits_dict = {}
    #for lab in labs_dict:
    #    labs.lab_info(lab["name"])
    #    labs.isp_lab()
    #    labs_cits_dict[lab["name"]] = {labs.isp_dict}
    #print(labs_cits_dict)
    # labs_dict = {lab: {"name": lab} for lab in labs_list}
    # id_list = [i for i in range(len(labs_list))]
    # print(labs_dict)
    # print(id_list)
