from django.urls import path
from net_jet.tools import views

urlpatterns = [
    path('', views.index, name='tools_index'),
    path('test_isp/', views.test_isp, name='test_isp'),
    path('providers/', views.providers, name='providers'),
    path('inactive_intf/', views.inactive_intf, name='inactive_intf'),
    path('search_arp_by_mac/', views.search_arp_by_mac, name='search_arp_by_mac'),
    path('ip_calc/', views.ip_calc, name='ip_calc'),
    path('switch_intf/', views.switch_intf, name='switch_intf')
]
