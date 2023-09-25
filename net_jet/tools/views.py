from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, 'tools/index.html')


def providers(request):
    return render(request, 'tools/providers.html')
