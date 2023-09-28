from django.shortcuts import render
from .scripts import get_info_netbox
# Create your views here.


def index(request):
    return render(request, 'tools/index.html')


def providers(request):
    """"
    Input your url and token
    url =
    token =
    """
    labs = get_info_netbox.GetNetbox(url, token)
    labs.get_tenants("lab")
    labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
    return render(request, 'tools/providers.html', context={'labs': labs_dict})
