from django.shortcuts import render, get_object_or_404
from django.views import View
from net_jet.articles.models import Article

# Create your views here.


class IndexView(View):

    def get(self, request, *args, **kwargs):
        # query = request.GET.get('q', '')
        articles = Article.objects.all()[:15]
        return render(request, 'articles/index.html', context={
            'articles': articles,
        })


class ArticleView(View):

    def get(self, request, *args, **kwargs):
        article = get_object_or_404(Article, id=kwargs['id'])
        return render(request, 'articles/show.html', context={
            'article': article,
        })
