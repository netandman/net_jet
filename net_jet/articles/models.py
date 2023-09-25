from django.db import models

# Create your models here.


class Article(models.Model):
    STATE_TYPE = (
        ('draft', 'draft'),
        ('published', 'published')
    )
    name = models.CharField(max_length=100)
    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    state = models.CharField(choices=STATE_TYPE, max_length=9, default='draft')
    images = models.ImageField(upload_to='static/article/img/', null=True, blank=True, verbose_name='Images')

    def __str__(self):
        return self.name
