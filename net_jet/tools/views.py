from django.shortcuts import render, redirect
import json
from django.http import HttpResponse
from .scripts import get_info_netbox, get_info_cisco_dev
import yaml
# Create your views here.

lab_choice_list = [""]

def index(request):
    return render(request, 'tools/index.html')

def test_isp(request):
    core_isp_main = ""
    core_isp_backup = ""
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    try:
        labs = get_info_netbox.GetNetbox(**credentials['netbox'])
        username, passw = credentials['cisco'].values()
        labs.get_tenants("lab")
        labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
        if request.method == 'GET':
            return render(request, 'tools/test_isp.html', context={'labs': labs_dict})
        elif request.method == 'POST':
            lab_choice = request.POST.get("labs", lab_choice_list[-1])
            isp_choice = request.POST.get("isp", None)
            lab_choice_list.append(request.POST.get("labs"))
            if None in lab_choice_list:
                lab_choice_list.remove(None)
            labs.lab_info(lab_choice)
            labs.isp_lab()
            if isp_choice:
                labs.core_ip()
                labs.core_isp_intf()
                if isp_choice == "isp_main":
                    core_isp_main = get_info_cisco_dev.check_core_intf_isp(str(labs.core_mgmt_ip),
                                                                str(labs.main_isp_intf), username, passw)
                elif isp_choice == "isp_backup":
                    core_isp_backup = get_info_cisco_dev.check_core_intf_isp(str(labs.core_mgmt_ip),
                                                                  str(labs.backup_isp_intf), username, passw)
            return render(request, 'tools/test_isp.html', context={'labs': labs_dict,
                                                                   'isp_dict': labs.isp_dict,
                                                                   'isp_choice': isp_choice,
                                                                   'core_isp_main': core_isp_main,
                                                                   'core_isp_backup': core_isp_backup,
                                                                   'lab_choice': lab_choice,})
    except ConnectionError:
        labs_dict = {}
        isp_dict = {}
        user_message = 'НЕ УДАЕТСЯ ПОДКЛЮЧИТЬСЯ К NETBOX, ПЕРЕЗАГРУЗИТЕ СТРАНИЦУ'
        return render(request, 'tools/test_isp.html', context={'labs': labs_dict,
                                                               'isp_dict': isp_dict,
                                                               'user_message': user_message,})


def providers(request):
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = get_info_netbox.GetNetbox(**credentials['netbox'])
    labs.get_tenants("lab")
    labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
    if request.method == 'GET':
        return render(request, 'tools/providers.html', context={'labs': labs_dict})
    elif request.method == 'POST':
        lab_choice = request.POST["labs"]
        labs.lab_info(lab_choice)
        labs.isp_lab()
        return render(request, 'tools/providers.html', context={'labs': labs_dict, 'isp_dict': labs.isp_dict})
