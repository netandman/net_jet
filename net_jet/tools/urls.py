from django.urls import path
from net_jet.tools import views

urlpatterns = [
    path('', views.index, name='tools_index'),
    path('test_isp/', views.test_isp, name='test_isp'),
    path('providers/', views.providers, name='providers'),
]
