from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=75, unique=True)
    description = models.TextField(max_length=400)

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name='Введите текст', help_text='Все что хотите')
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True, null=True, related_name='posts',
        verbose_name='Выберите группу', help_text='(необязательно)'
    )
    image = models.ImageField(upload_to='posts/', blank=True, null=True, verbose_name='Добавьте изображение')

    class Meta:
        ordering = ['-pub_date']

    def __str__(self):
        auth = self.author
        date = self.pub_date
        text_part = self.text[:30]
        return f'{auth}. {date}. {text_part}'


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, blank=True, null=False, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(verbose_name='Введите комментарий')
    created = models.DateTimeField('created', auto_now_add=True)


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
