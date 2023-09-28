from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from .scripts import get_info_netbox
# Create your views here.


class IndexView(View):

    def get(self, request, *args, **kwargs):
        return render(request, 'tools/index.html')


class ProvidersView(View):
    def get(self, request, *args, **kwargs):
        #url =
        #token =
        labs = get_info_netbox.GetNetbox(url, token)
        labs.get_tenants("lab")
        labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
        return render(request, 'tools/providers.html', context={'labs': labs_dict})

    def post(self, request, *args, **kwargs):
        test = kwargs.get("name")
        #return render(request, 'tools/providers.html', context={'lab_id': lab_id})
        HttpResponse(f"""
                        <div>Name: {test}</div>
                    """)
