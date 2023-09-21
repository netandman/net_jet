from django.shortcuts import render
from net_jet.articles.models import Article

# Create your views here.


def index(request):
    return render(request, 'main/index.html')


def about(request):
    return render(request, 'main/about.html')
