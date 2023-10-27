import pynetbox
import ipaddress
import yaml
from pprint import pprint


class GetNetbox:

    def __init__(self, url, token):
        self.nb = pynetbox.api(url=url, token=token)
        self.nb.http_session.verify = False

    '''
    GET ALL TENANT USING TAG
    '''

    def get_tenants(self, tag):
        all_tenants = self.nb.tenancy.tenants.filter(tag=tag)
        self.all_tenants = list(all_tenants)

    '''
    GET A TENANT ID AND SLUG BY TENANT NAME
    '''

    def lab_info(self, lab_name):
        tenant_get = self.nb.tenancy.tenants.get(name=lab_name)
        self.lab_id = tenant_get.id
        self.lab_slug = tenant_get.slug

    '''
    CREATE AN ISP DICTIONARY BY FILTERING CIRCUITS WITH TENANT ID AND STATUS,
    USING A CYCLE FOR TO GET INFORMATION OF THE CIRCUIT PROVIDER
    '''

    def isp_lab(self):
        circuits = self.nb.circuits.circuits.filter(tenant_id=self.lab_id, status='active')
        crts_dict = {}
        isp_dict = {}
        for circuit in circuits:
            isp_get = self.nb.circuits.circuits.get(cid=circuit)
            #crts_dict[isp_get] = {"crts_name": isp_get.display, "provider_id": isp_get.provider.id}
            isp_dict[isp_get.cid] = dict(self.nb.circuits.providers.get(id=isp_get.provider.id))
        self.isp_dict = isp_dict

    '''
    GET PRIMARY IP ADDRESS OF DEVICES WITH CORE TAG,
    USING THE IPADDRESS MODULE TO TRANSFORM THE IP ADDRESS WITH THE MASK TO
    IPADDRESS OBJECT THAT HAS ADDITION METHOD LIKE .IP
    '''

    def core_ip(self):
        core = self.nb.dcim.devices.filter(tenant_id=self.lab_id, tag="core")
        if core:
            core_get = self.nb.dcim.devices.get(name=core)
            mgmt_intf = ipaddress.ip_interface(core_get.primary_ip4)
            core_mgmt_ip = mgmt_intf.ip
            #core_intf_filter = self.nb.dcim.interfaces.filter(device_id=core_get.id, description="mgmt")
            #mgmt_vlan_intf = ((list(core_intf_filter))[0])
            #core_mgmt_intf = self.nb.dcim.interfaces.get(name=mgmt_vlan_intf, device_id=core_get.id)
            #self.core_intf = core_mgmt_intf
            self.core_mgmt_ip = core_mgmt_ip
        else:
            self.core_mgmt_ip = None

    '''
    GET ROUTER IP ADDRESS FROM FILTERING BY TENANT_ID AND TAG ROUTER, THEN GET FULL INFORMATION
    ABOUT ROUTER WITH GET REQUEST
    '''

    def router_ip(self):
        router = self.nb.dcim.devices.filter(tenant_id=self.lab_id, tag="router")
        if router:
            router_get = self.nb.dcim.devices.get(name=router)
            mgmt_intf = ipaddress.ip_interface(router_get.primary_ip4)
            router_mgmt_ip = mgmt_intf.ip
            self.router_mgmt_ip = router_mgmt_ip
        else:
            self.router_mgmt_ip = None

            #def core_ip(self):
    #    """
    #    Filtering ip address by id of tenant and tag with mgmt value
    #    """
    #    core_ipaddr_filter = self.nb.ipam.ip_addresses.filter(tenant_id=self.lab_id,
    #                                                          tag="mgmt")
    #    mgmt_int = ipaddress.ip_interface((list(core_ipaddr_filter))[0])
    #    mgmt_subnet = mgmt_int.network
    #    core_ipaddr_get = self.nb.ipam.ip_addresses.get(address=mgmt_int.ip, mask_length=mgmt_subnet.prefixlen)
    #    self.core_intf = mgmt_int
    #    self.core_ip_dict = core_ipaddr_get

    '''
    GET INTERFACES OF THE CORE SWITCH WHICH CONNECT TO INTERNET SERVICE PROVIDERS
    '''

    def core_isp_intf(self):
        core = self.nb.dcim.devices.filter(tenant_id=self.lab_id, tag="core")
        core_get = self.nb.dcim.devices.get(name=core)
        main_isp_intf = self.nb.dcim.interfaces.get(tag="isp_main", device_id=core_get.id)
        backup_isp_inf = self.nb.dcim.interfaces.get(tag="isp_backup", device_id=core_get.id)
        self.main_isp_intf = main_isp_intf
        self.backup_isp_intf = backup_isp_inf

    '''
    GET THE INTERFACES OF THE ROUTER WHICH CONNECT TO INTERNET SERVICE PROVIDERS
    FIRST OF ALL, RECEIVE THE DATA BY FILTERING LAB_ID AND TAG=ROUTER, THEN GET
    DATA BY TAG=ISP_MAIN/BACKUP, AND ROUTER ID
    '''

    def router_isp_intf(self):
        router = self.nb.dcim.devices.filter(tenant_id=self.lab_id, tag="router")
        if router:
            router_get = self.nb.dcim.devices.get(name=router)
            main_isp_intf = self.nb.dcim.interfaces.get(tag="isp_main", device_id=router_get.id)
            backup_isp_intf = self.nb.dcim.interfaces.get(tag="isp_backup", device_id=router_get.id)
            main_isp_ip_filter = self.nb.ipam.ip_addresses.filter(tenant_id=self.lab_id,
                                                                  device_id=router_get.id,
                                                                  interface=main_isp_intf.display,
                                                                  status='active')
            back_isp_ip_filter = self.nb.ipam.ip_addresses.filter(tenant_id=self.lab_id,
                                                                  device_id=router_get.id,
                                                                  interface=backup_isp_intf.display,
                                                                  status='active')
            main_isp_ip = ipaddress.ip_interface((list(main_isp_ip_filter))[0])
            back_isp_ip = ipaddress.ip_interface((list(back_isp_ip_filter))[0])
            self.rtr_main_isp_ip = main_isp_ip
            self.rtr_backup_isp_ip = back_isp_ip
        else:
            self.rtr_main_isp_ip = None
            self.rtr_backup_isp_ip = None

    '''
    GET THE BORDER MGMT IP ADDRESS AND AS INTERFACE BY TAGS "BORDER", "AS_INTF"
    '''

    def borders_ip(self):
        borders_dict = {}
        borders = self.nb.dcim.devices.filter(tag="border")
        for border in list(borders):
            border_get = self.nb.dcim.devices.get(name=border)
            as_intf = self.nb.dcim.interfaces.get(tag="as_intf", device_id=border_get.id)
            mgmt_intf = ipaddress.ip_interface(border_get.primary_ip4)
            border_mgmt_ip = str(mgmt_intf.ip)
            borders_dict[str(border)] = {"mgmt_ip": border_mgmt_ip, "as_intf": as_intf}
        self.borders_dict = borders_dict


if __name__ == "__main__":
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = GetNetbox(**credentials['netbox'])
    labs.borders_ip()
    print(labs.borders_dict)
    #labs.get_tenants("lab")
    #labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
    #labs.lab_info("Лаборатория Новосибирск")
    #labs.router_isp_intf()
    #print(labs.rtr_main_isp_ip)
    #print(labs.rtr_backup_isp_ip)
    #labs.isp_lab()
    #print(labs.isp_dict)
    #labs.core_ip()
    #labs.core_isp_intf()
    #print(labs.core_ip_dict)
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
