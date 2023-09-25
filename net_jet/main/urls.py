from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='main_index'),
    path('about/', views.about, name='about'),
]
