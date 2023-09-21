from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='articles_index'),
    path('<int:id>', views.ArticleView.as_view(), name='article_show'),
]
