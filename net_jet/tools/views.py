from django.shortcuts import render, redirect, HttpResponseRedirect
from django.views.decorators.cache import cache_page
from django.urls import reverse
from .ip_calc_forms import IpCalcForm
import json
from django.http import HttpResponse
from .scripts import get_info_netbox, get_info_cisco_dev, get_recommendations, get_service_tools
import os
import dotenv
import urllib3
import asyncio

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create your views here.

# CHANGE YOUR PATH TO .ENV FILE
dotenv.load_dotenv()


def index(request):
    return render(request, 'tools/index.html')


def test_isp(request):
    labs_dict = {}
    isp_dict = {}
    if request.user.is_anonymous:
        return HttpResponseRedirect(reverse('login'))
    else:
        core_isp_main = ""
        core_isp_backup = ""
        router_main_gw = ""
        router_backup_gw = ""
        border_trace_main_gw = ""
        border_trace_backup_gw = ""
        recommendations = ""
        rcmd_dict = {}
        try:
            if not labs_dict:
                labs = get_info_netbox.GetNetbox('https://x.x.x.x', os.getenv('NETBOX_API'))
                username = 'netjet'
                passw = os.getenv('CISCO_PASSWORD')
                labs.get_tenants("lab")
                labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
                for lab_item in labs_dict:
                    lab_name = lab_item['name']
                    labs.lab_info(lab_name)
                    labs.isp_lab()
                    isp_dict[lab_name] = labs.isp_dict
            if request.method == 'GET':
                return render(request, 'tools/test_isp.html', context={'labs': labs_dict})
            elif request.method == 'POST':
                user_message = 'Выберите провайдера и ожидайте результаты тестирования'
                print('Lab POST')
                lab_choice = request.POST.get("labs")
                print('Lab choice is ' + str(lab_choice))
                lab_isp_dict = isp_dict[lab_choice]
                labs.lab_info(lab_choice)
                labs.core_ip()
                labs.core_isp_intf()
                labs.router_ip()
                labs.router_isp_intf()
                labs.borders_ip()
                isp_choice = request.POST.get("isp")
                print("ISP POST")
                print("isp choice is " + str(isp_choice))
                if isp_choice == "isp_main":
                    user_message = ''
                    try:
                        core_isp_main = get_info_cisco_dev.check_core_intf_isp(str(labs.core_mgmt_ip),
                                                                               str(labs.main_isp_intf),
                                                                               username, passw)
                        rcmd_dict.update(core_isp_main)
                        recommendations = get_recommendations.get_intf_recommends(rcmd_dict)
                        router_main_gw = get_info_cisco_dev.check_router_gw(str(labs.router_mgmt_ip),
                                                                            labs.rtr_main_isp_ip,
                                                                            username, passw)
                        rcmd_dict.update(router_main_gw)
                        recommendations = get_recommendations.get_intf_recommends(rcmd_dict)
                        border_trace_main_gw = get_info_cisco_dev.check_rtr_from_borders(labs.borders_dict,
                                                                                         labs.rtr_main_isp_ip,
                                                                                         username, passw)
                    except Exception as e:
                        print(e)
                        router_main_gw = {}

                elif isp_choice == "isp_backup":
                    user_message = ''
                    try:
                        core_isp_backup = get_info_cisco_dev.check_core_intf_isp(str(labs.core_mgmt_ip),
                                                                                 str(labs.backup_isp_intf),
                                                                                 username, passw)
                        rcmd_dict.update(core_isp_backup)
                        recommendations = get_recommendations.get_intf_recommends(rcmd_dict)
                        router_backup_gw = get_info_cisco_dev.check_router_gw(str(labs.router_mgmt_ip),
                                                                              labs.rtr_backup_isp_ip,
                                                                              username, passw)
                        rcmd_dict.update(router_backup_gw)
                        recommendations = get_recommendations.get_intf_recommends(rcmd_dict)
                        border_trace_backup_gw = get_info_cisco_dev.check_rtr_from_borders(labs.borders_dict,
                                                                                           labs.rtr_backup_isp_ip,
                                                                                           username, passw)
                    except Exception as e:
                        print(e)
                        router_backup_gw = {}
                return render(request, 'tools/test_isp.html', context={'labs': labs_dict,
                                                                       'isp_dict': lab_isp_dict,
                                                                       'isp_choice': isp_choice,
                                                                       'core_isp_main': core_isp_main,
                                                                       'core_isp_backup': core_isp_backup,
                                                                       'lab_choice': lab_choice,
                                                                       'router_main_gw': router_main_gw,
                                                                       'router_backup_gw': router_backup_gw,
                                                                       'border_trace_main_gw': border_trace_main_gw,
                                                                       'border_trace_backup_gw': border_trace_backup_gw,
                                                                       'recommendations': recommendations,
                                                                       'user_message': user_message})
        except Exception as e:
            print("ERROR EXCEPTION ", e)
            user_message = 'НЕ УДАЕТСЯ ПОДКЛЮЧИТЬСЯ К NETBOX, ПЕРЕЗАГРУЗИТЕ СТРАНИЦУ ' \
                           'ИЛИ ПОПРОБУЙДЕ ВЫПОЛНИТЬ ЗАПРОС ПОЗЖЕ'
            return render(request, 'tools/test_isp.html', context={'labs': labs_dict,
                                                                   'isp_dict': isp_dict,
                                                                   'lab_choice': lab_choice,
                                                                   'user_message': user_message})


def providers(request):
    if request.user.is_anonymous:
        return HttpResponseRedirect(reverse('login'))
    else:
        try:
            labs = get_info_netbox.GetNetbox('https://x.x.x.x', os.getenv('NETBOX_API'))
            labs.get_tenants("lab")
            labs_dict = {lab: {"name": lab, "id": labs.all_tenants.index(lab)} for lab in labs.all_tenants}
            if request.method == 'GET':
                return render(request, 'tools/providers.html', context={'labs': labs_dict})
            elif request.method == 'POST':
                lab_choice = request.POST["labs"]
                labs.lab_info(lab_choice)
                labs.isp_lab()
                return render(request, 'tools/providers.html', context={'labs': labs_dict,
                                                                        'isp_dict': labs.isp_dict})
        except:
            labs_dict = {}
            isp_dict = {}
            user_message = 'НЕ УДАЕТСЯ ПОДКЛЮЧИТЬСЯ К NETBOX, ПЕРЕЗАГРУЗИТЕ СТРАНИЦУ ' \
                           'ИЛИ ПОПРОБУЙДЕ ВЫПОЛНИТЬ ЗАПРОС ПОЗЖЕ'
            return render(request, 'tools/providers.html', context={'labs': labs_dict,
                                                                    'isp_dict': isp_dict,
                                                                    'user_message': user_message})


@cache_page(60 * 480)
def inactive_intf(request):
    place_dict = {}
    switch_dict = {}
    switch_intf_dict = {}
    username = 'netjet'
    passw = os.getenv('CISCO_PASSWORD')
    user_message = 'Выберите площадку и ожидайте результаты тестирования (проверка может занимать до 5 минут)'
    if request.user.is_anonymous:
        return HttpResponseRedirect(reverse('login'))
    try:
        if not place_dict:
            places = get_info_netbox.GetNetbox('https://x.x.x.x', os.getenv('NETBOX_API'))
            places.get_tenants(["lab", "office", "warehouse"])
            place_dict = {place: {"name": place, "id": places.all_tenants.index(place)} for place in places.all_tenants}
            for place_item in place_dict:
                place_name = place_item['name']
                places.lab_info(place_name)
                switch_dict[place_name] = places.switches_ip()
        if request.method == 'GET':
            return render(request, 'tools/inactive_intf.html', context={'places': place_dict,
                                                                        'user_message': user_message})
        elif request.method == 'POST':
            user_message = {}
            print('Place POST')
            place_choice = request.POST.get("places")
            period = request.POST.get("period")
            print('Place choice is ' + str(place_choice))
            place_switches_dict = switch_dict[place_choice]
            try:
                switch_scrapli_dict = get_info_cisco_dev.gener_dev_dict(place_switches_dict, username, passw)
                switch_intf_dict = asyncio.run(get_info_cisco_dev.get_inactive_intf(switch_scrapli_dict,
                                                                                    period=int(period)))
                # switch_intf_dict = get_info_cisco_dev.parsing_intf(switch_dict[place_choice], username, passw,
                #                                                    period=int(period))
            except Exception as e:
                print(f'Ops! Exception after connections {e}')
            return render(request, 'tools/inactive_intf.html', context={'places': place_dict,
                                                                        'switch_intf_dict': switch_intf_dict,
                                                                        'place_choice': place_choice,
                                                                        'user_message': user_message,
                                                                        'period': period})
    except Exception as e:
        print("ERROR EXCEPTION ", e)
        place_dict = {}
        switch_intf_dict = {}
        user_message = 'НЕ УДАЕТСЯ ПОДКЛЮЧИТЬСЯ К NETBOX, ПЕРЕЗАГРУЗИТЕ СТРАНИЦУ ' \
                       'ИЛИ ПОПРОБУЙДЕ ВЫПОЛНИТЬ ЗАПРОС ПОЗЖЕ'
        return render(request, 'tools/inactive_intf.html', context={'places': place_dict,
                                                                    'switch_intf_dict': switch_intf_dict,
                                                                    'user_message': user_message})


@cache_page(60 * 480)
def search_arp_by_mac(request):
    place_dict = {}
    switch_dict = {}
    core_dict = {}
    switch_intf_dict = {}
    arp_result = {'ip_addr': 'Запрошенная информация не обнаружена'}
    username = 'netjet'
    passw = os.getenv('CISCO_PASSWORD')
    user_message = 'Выберите площадку'
    if request.user.is_anonymous:
        return HttpResponseRedirect(reverse('login'))
    try:
        if not place_dict:
            places = get_info_netbox.GetNetbox('https://x.x.x.x', os.getenv('NETBOX_API'))
            places.get_tenants(["lab", "office", "warehouse"])
            place_dict = {place: {"name": place, "id": places.all_tenants.index(place)} for place in places.all_tenants}
            for place_item in place_dict:
                place_name = place_item['name']
                places.lab_info(place_name)
                switch_dict[place_name] = places.switches_ip()
                core_dict[place_name] = places.core_ip_scrapli()
        if request.method == 'GET':
            return render(request, 'tools/search_arp_by_mac.html', context={'core_dict': core_dict,
                                                                            'user_message': user_message})
        elif request.method == 'POST':
            print('!!!Print POST request')
            user_message = 'Выберите коммутатор'
            place_choice = request.POST.get("places")
            switch_choice = request.POST.get("switches")
            intf_choice = request.POST.get("interfaces")
            print(f'Place choice is {place_choice} and type is {type(place_choice)}')
            print(f'Switch choice is {switch_choice} and type is {type(switch_choice)}')
            print(f'Intf choice {intf_choice}')
            place_switches_dict = switch_dict[place_choice]
            core_dict_scrapli = get_info_cisco_dev.gener_dev_dict(core_dict[place_choice], username, passw)
            if intf_choice:
                user_message = ''
                try:
                    place_switch = {switch_choice: value for switch, value in place_switches_dict.items()
                                    if str(switch) == switch_choice}
                    switch_scrapli_dict = get_info_cisco_dev.gener_dev_dict(place_switch, username, passw)
                    arp_task = asyncio.run(get_info_cisco_dev.get_mac_arp(core_dict_scrapli['cisco'],
                                                                          switch_scrapli_dict,
                                                                          intf_choice))
                    print(f'Arp task is {arp_task}')
                    arp_result = arp_task['core'][0]
                except Exception as e:
                    print(f'Ops! Exception after interface choice is {e}')
            elif switch_choice:
                user_message = 'Выберите интерфейс'
                try:
                    place_switch = {switch_choice: value for switch, value in place_switches_dict.items()
                                    if str(switch) == switch_choice}
                    switch_scrapli_dict = get_info_cisco_dev.gener_dev_dict(place_switch, username, passw)
                    switch_intf_dict = asyncio.run(get_info_cisco_dev.send_sh_int_status(switch_scrapli_dict,
                                                                                         'show interface status'))
                    switch_intf_dict = switch_intf_dict[0]
                    print(f'Switch interface dictionary is {switch_intf_dict}')
                except Exception as e:
                    print(f'Ops! Exception after switch choice is {e}')

            return render(request, 'tools/search_arp_by_mac.html', context={'core_dict': core_dict,
                                                                            'place_choice': place_choice,
                                                                            'place_switches_dict': place_switches_dict,
                                                                            'switch_choice': switch_choice,
                                                                            'switch_intf_dict': switch_intf_dict,
                                                                            'interface_choice': intf_choice,
                                                                            'user_message': user_message,
                                                                            'arp_result': arp_result
                                                                            })
    except Exception as e:
        print("ERROR EXCEPTION ", e)
        core_dict = {}
        user_message = 'НЕ УДАЕТСЯ ПОДКЛЮЧИТЬСЯ К NETBOX, ПЕРЕЗАГРУЗИТЕ СТРАНИЦУ ' \
                       'ИЛИ ПОПРОБУЙДЕ ВЫПОЛНИТЬ ЗАПРОС ПОЗЖЕ'
        return render(request, 'tools/search_arp_by_mac.html', context={'core_dict': core_dict,
                                                                        'user_message': user_message})


def ip_calc(request):
    user_massage = ''
    if request.method == 'POST':
        form = IpCalcForm(data=request.POST)
        if form.is_valid():
            try:
                ip_choice = request.POST['network']
                net_choice = request.POST['mask']
                network_dict = get_service_tools.get_net(ip_choice, net_choice)
                return render(request, 'tools/ip_calc.html', context={'form': form,
                                                                      'network_dict': network_dict})
            except Exception as e:
                user_massage = 'Введите корректные данные'
                form = IpCalcForm()
                return render(request, 'tools/ip_calc.html', context={'form': form, 'user_massage': user_massage})
    else:
        form = IpCalcForm()
    context = {'form': form}
    return render(request, 'tools/ip_calc.html', context)


@cache_page(60 * 480)
def switch_intf(request):
    switch_dict = {}
    intf_selected = {}
    switch_intf_json = {}
    username = 'netjet'
    passw = os.getenv('CISCO_PASSWORD')
    user_message = 'ВЫБЕРИТЕ ПЛОЩАДКУ И ОЖИДАЙТЕ ФОРМИРОВАНИЯ СПИСКА КОММУТАТОРОВ'
    if request.user.is_anonymous:
        return HttpResponseRedirect(reverse('login'))
    try:
        places = get_info_netbox.GetNetbox('https://x.x.x.x', os.getenv('NETBOX_API'))
        places.get_tenants(["lab", "office", "warehouse"])
        place_dict = {place: {"name": place, "id": places.all_tenants.index(place)} for place in places.all_tenants}
        for place_item in place_dict:
            place_name = place_item['name']
            places.lab_info(place_name)
            switch_dict[place_name] = places.switches_ip()
        if request.method == 'GET':
            return render(request, 'tools/switch_intf.html', context={'places': place_dict,
                                                                      'user_message': user_message})
        elif request.method == 'POST':
            print('Place POST')
            place_choice = request.POST.get("places")
            switch_choice = request.POST.get("switches")
            intf_choice = request.POST.get("interfaces")
            print(f'Place choice is {place_choice} and type is {type(place_choice)}')
            print(f'Switch choice is {switch_choice} and type is {type(switch_choice)}')
            print(f'Intf choice {intf_choice} and type is {type(intf_choice)}')
            place_switches_dict = switch_dict[place_choice]
            if intf_choice:
                user_message = ''
                intf_selected = json.loads(intf_choice)
                # print(f"Interface selected is {intf_selected}")
            else:
                user_message = 'ВЫБЕРИТЕ КОММУТАТОР И ПОСЛЕ ПОЯВЛЕНИЯ СПИСКА ИНТЕРФЕЙСОВ ВЫБЕРИТЬ ПОРТ'
                try:
                    place_switch = {switch_choice: value for switch, value in place_switches_dict.items()
                                    if str(switch) == switch_choice}
                    switch_scrapli_dict = get_info_cisco_dev.gener_dev_dict(place_switch, username, passw)
                    switch_intf_dict = asyncio.run(get_info_cisco_dev.send_sh_int_status(switch_scrapli_dict,
                                                                                         'show interface status'))

                    for k, v in switch_intf_dict[0].items():
                        switch_intf_json[k] = [[i, json.dumps(i)] for i in v]
                    # print(f'!!!ATTENTION!!! Switch_intf_dict is {switch_intf_dict} and type {type(switch_intf_dict)}')
                except Exception as e:
                    print(f'Ops! Exception after connections {e}')
            return render(request, 'tools/switch_intf.html', context={'places': place_dict,
                                                                      'place_choice': place_choice,
                                                                      'place_switches_dict': place_switches_dict,
                                                                      'switch_choice': switch_choice,
                                                                      'switch_intf_json': switch_intf_json,
                                                                      'intf_choice': intf_choice,
                                                                      'intf_selected': intf_selected,
                                                                      'user_message': user_message})
    except Exception as e:
        print("ERROR EXCEPTION ", e)
        place_dict = {}
        switch_intf_dict = {}
        user_message = 'НЕ УДАЕТСЯ ПОДКЛЮЧИТЬСЯ К NETBOX, ПЕРЕЗАГРУЗИТЕ СТРАНИЦУ ' \
                       'ИЛИ ПОПРОБУЙДЕ ВЫПОЛНИТЬ ЗАПРОС ПОЗЖЕ'
        return render(request, 'tools/switch_intf.html', context={'places': place_dict,
                                                                  'switch_intf_dict': switch_intf_dict,
                                                                  'user_message': user_message})
