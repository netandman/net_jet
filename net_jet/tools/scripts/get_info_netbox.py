import pynetbox
from pprint import pprint


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
        isp_dict = {}
        for circuit in circuits:
            isp_get = self.nb.circuits.circuits.get(cid=circuit)
            isp_dict[isp_get.provider] = dict(self.nb.circuits.providers.get(id=isp_get.provider.id))
        self.isp_dict = isp_dict


if __name__ == "__main__":
    url = "http://172.17.8.130:8085"
    token = "58d5158f30a88a96cc92830e5007510269d262ef"
    labs = GetNetbox(url, token)
    labs.get_tenants("lab")
    print(labs.all_tenants)
    labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
    print(labs_dict)
    # labs_dict = {lab: {"name": lab} for lab in labs_list}
    # id_list = [i for i in range(len(labs_list))]
    # print(labs_dict)
    # print(id_list)
