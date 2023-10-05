from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from .scripts import get_info_netbox
import yaml
# Create your views here.

lab_choice_list = [""]


def index(request):
    return render(request, 'tools/index.html')

def test_isp(request):
    with open("C:/Python/myprojects/net_jet/net_jet/tools/scripts/private.yml") as src:
        credentials = yaml.safe_load(src)
    labs = get_info_netbox.GetNetbox(**credentials['netbox'])
    labs.get_tenants("lab")
    labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
    if request.method == 'GET':
        return render(request, 'tools/test_isp.html', context={'labs': labs_dict})
    elif request.method == 'POST':
        #if request.POST["labs"]:
        lab_choice = request.POST.get("labs", lab_choice_list[-1])
        isp_choice = request.POST.get("isp", None)
        lab_choice_list.append(request.POST.get("labs"))
        if None in lab_choice_list:
            lab_choice_list.remove(None)
        print(lab_choice_list)
        labs.lab_info(lab_choice)
        labs.isp_lab()
        return render(request, 'tools/test_isp.html', context={'labs': labs_dict,
                                                                   'isp_dict': labs.isp_dict,
                                                                   'isp_choice': isp_choice})
        #if request.POST["isp"]:
        #    isp_choice = request.POST.get("isp", None)
        #    return redirect(request, 'tools/test_isp.html', context={'labs': labs_dict,
        #                                                             'isp_dict': labs.isp_dict,
        #                                                             'isp_choice': isp_choice})


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
