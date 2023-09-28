from django.urls import path
from net_jet.tools import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='tools_index'),
    path('providers/', views.ProvidersView.as_view(), name='providers'),
]
