from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'index.html', {'page': page, 'paginator': paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'group.html', {'group': group, 'page': page, 'paginator': paginator})


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post_new = form.save(commit=False)
            post_new.author = request.user
            post_new.save()
            return redirect('index')
        return render(request, 'new_post.html', {'form': form})
    form = PostForm()
    return render(request, 'new_post.html', {'form': form})


def profile(request, username):
    post_author = get_object_or_404(User, username=username)
    post = Post.objects.filter(author=post_author)
    paginator = Paginator(post, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    following = False
    if request.user.is_authenticated:
        following = Follow.objects.filter(author=post_author, user=request.user)
    return render(request, 'includes/profile.html',
        {
            'page': page,
            'paginator': paginator,
            'post_author': post_author,
            'following': following,
        }
    )


def post_view(request, username, post_id):
    post_author = User.objects.get(username=username)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    items = post.comments.all()
    form = CommentForm()
    return render(
        request, 'includes/post.html', {'post_author': post_author, 'post': post, 'form': form, 'items': items}
    )


@login_required
def post_edit(request, username, post_id):
    post_author = User.objects.get(username=username)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('post', username=post_author, post_id=post_id)
    return render(request, 'new_post.html', {'form': form, 'post_author': post_author, 'post': post})


@login_required
def add_comment(request, username, post_id):
    post_author = User.objects.get(username=username)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        new_comment = form.save(commit=False)
        new_comment.author = request.user
        new_comment.post = post
        new_comment.save()
        return redirect('post', username=post_author, post_id=post_id)
    form = PostForm()
    return render(request, 'includes/comments.html', {'form': form, 'post_author': post_author, 'post': post})


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'follow.html', {'page': page, 'paginator': paginator})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    unfollow_profile = Follow.objects.get(author__username=username, user=request.user)
    if Follow.objects.filter(pk=unfollow_profile.pk):
        unfollow_profile.delete()
    return redirect('profile', username=username)


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
