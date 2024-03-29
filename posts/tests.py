import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Follow, Group, Post, User


class TestProfile(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        user_name = 'Test_user'
        self.user = User.objects.create_user(username=user_name, email='test@testmail.com', password='test1234')
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Test', slug='Test', description='Test')

    def post_is_real(self):
        last_post = Post.objects.first()
        cache.clear()
        response = self.client.get(reverse('index'))
        paginator = response.context.get('paginator')
        if paginator is not None:
            self.assertEqual(paginator.count, 1)
            post = response.context['page'][0]
        else:
            post = response.context['post']
        self.assertEqual(post.text, last_post.text)
        self.assertEqual(post.author, last_post.author)
        self.assertEqual(post.group, last_post.group)

    def post_on_pages(self):
        post = Post.objects.first()
        cache.clear()
        response = self.authorized_client.get(reverse('index'))
        self.assertContains(response, post.text)
        response = self.authorized_client.get(reverse('profile', kwargs={'username': post.author.username}))
        self.assertContains(response, post.text)
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': post.author.username, 'post_id': post.id})
        )
        self.assertContains(response, post.text)
        if post.group is not None:
            response = self.authorized_client.get(reverse('group_posts', kwargs={'slug': post.group.slug}))
            self.assertContains(response, post.text)
        if self.user.follower.count() == 1:
            response = self.authorized_client.get(reverse('follow_index'))
            self.assertContains(response, post.text)

    def test_profile(self):
        response = self.client.get(reverse('profile', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)

    def test_auth_post(self):
        posts_before = Post.objects.all().count()
        test_post = self.authorized_client.post(
            reverse('new_post'), {'text': "Тест для тестового поста",
                                  'author': self.user, 'group': self.group.pk}
        )
        posts_after = Post.objects.all().count()
        self.assertNotEqual(posts_before, posts_after)
        self.post_is_real()

    def test_un_auth_post(self):
        posts_before = Post.objects.all().count()
        test_post = self.unauthorized_client.post(reverse('new_post'))
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        target_url = f'{login_url}?next={new_post_url}'
        self.assertRedirects(test_post, target_url, status_code=302, target_status_code=200)
        posts_after = Post.objects.all().count()
        self.assertEqual(posts_before, posts_after)

    def test_new_post_all_pages(self):
        self.client.force_login(self.user)
        TEST_TEXT = 'Тестовый текст для теста'
        self.post = Post.objects.create(text=TEST_TEXT, author=self.user)
        checked_post = Post.objects.filter(text=TEST_TEXT).first()
        self.assertIsNotNone(checked_post)
        self.post_is_real()
        self.post_on_pages()

    def test_auth_edit(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(text='Текст для теста', author=self.user)
        ed_test_text = 'This is a test post without any meaning and edited'
        edit_post = self.client.post(
            reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
            {'text': ed_test_text, 'group': self.group.pk},
        )
        ed_post = Post.objects.filter(id=self.post.id).first()
        self.assertIsNotNone(ed_post)
        self.assertIn(ed_test_text, ed_post.text)
        self.post_is_real()
        self.post_on_pages()

    def test_page_not_found(self):
        response = self.client.get('something/for/test/')
        self.assertEqual(response.status_code, 404)

    def test_cache_index(self):
        response = self.authorized_client.get(reverse('index'))
        text_for_post = 'Тест для проверки кэша'
        self.assertNotContains(response, text_for_post)
        new_post = self.authorized_client.post(
            reverse('new_post'), {'text': text_for_post, 'author': self.user, 'group': self.group.pk}
        )
        response = self.authorized_client.get(reverse('index'))
        self.assertNotContains(response, text_for_post)
        cache.clear()
        response = self.authorized_client.get(reverse('index'))
        self.assertContains(response, text_for_post)

    def test_auth_follow(self):
        new_user = User.objects.create_user(username='second', email='testmail@testmail.com', password='testtest')
        response = self.authorized_client.post(reverse('profile_follow', args=[new_user]),follow=True)
        self.assertEqual(response.status_code, 200)
        find_follow = Follow.objects.get(user=self.user, author=new_user)
        self.assertTrue(find_follow)
        self.assertEqual(self.user, find_follow.user)
        self.assertEqual(self.user.follower.count(), 1)
        self.assertEqual(new_user, find_follow.author)

    def test_auth_unfollow(self):
        new_user = User.objects.create_user(username='second', email='testmail@testmail.com', password='testtest')
        follow = Follow.objects.create(user=self.user, author=new_user)
        response = self.authorized_client.get(reverse('profile_unfollow', args=[new_user]), follow=True)
        self.assertEqual(response.status_code, 200)
        find_follow = Follow.objects.exists()
        self.assertFalse(find_follow)
        self.assertEqual(self.user.follower.count(), 0)

    def test_new_post_follow(self):
        new_user = User.objects.create_user(username='second', email='secondd@testmail.com', password='testtest')
        self.authorized_client.get(reverse('profile_follow', args=[new_user]))
        find_text = 'Text for find on page'
        new_post = Post.objects.create(text=find_text, author=new_user)
        self.post_on_pages()

    def test_new_post_unfollow(self):
        new_user = User.objects.create_user(username='second', email='testmail@testmail.com', password='testtest')
        find_text = 'Text for find on page'
        new_post = Post.objects.create(text=find_text, author=new_user)
        self.post_on_pages()

    def test_un_auth_comment(self):
        test_post = Post.objects.create(text='text for test post', author=self.user)
        comment_text = 'text for comment'
        self.authorized_client.post(
            reverse('add_comment', kwargs={'username': self.user.username, 'post_id': test_post.id}),
            {'text': comment_text}
        )
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': self.user.username, 'post_id': test_post.id})
        )
        self.assertContains(response, comment_text)


def get_temporary_image(temp_file):
    image = Image.new('RGB', (100, 30), color=(73, 109, 137))
    image.save(temp_file, 'jpeg')
    return temp_file


class TestProfileImage(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        user_name = 'Test_user'
        self.user = User.objects.create_user(username=user_name, email='test@testmail.com', password='test1234')
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Test', slug='Test', description='Test')
        self.post = Post.objects.create(text='Текст для теста', author=self.user)

    def image_on_pages(self):
        post = Post.objects.first()
        cache.clear()
        response = self.authorized_client.get(reverse('index'))
        self.assertIn('img', str(response.content))
        response = self.authorized_client.get(reverse('profile', kwargs={'username': post.author.username}))
        self.assertIn('img', str(response.content))
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': post.author.username, 'post_id': post.id})
        )
        self.assertIn('img', str(response.content))
        if post.group is not None:
            response = self.authorized_client.get(reverse('group_posts', kwargs={'slug': post.group.slug}))
            self.assertIn('img', str(response.content))
        if self.user.follower.count() == 1:
            response = self.authorized_client.get(reverse('follow_index'))
            self.assertIn('img', str(response.content))

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_image_all_pages_version_1(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            test_image = get_temporary_image(temp_file)
            post = Post.objects.create(
                text='abc',
                author=self.user,
                group=self.group,
                image=test_image.name
            )
            self.assertEqual(len(Post.objects.all()), 2)
            self.image_on_pages()

    def test_image_all_pages_version_2(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif')
        post = Post.objects.create(
            text='abc',
            author=self.user,
            group=self.group,
            image=uploaded,
        )
        self.image_on_pages()
        # self.assertContains(response, 'img')  Оставил для себя
        # self.assertIn('img', response.content.decode())   Оставил для себя
        # self.assertIn('img', str(response.content))   Оставил для себя

    def test_no_image_push(self):
        not_image = SimpleUploadedFile(
            name='some.txt',
            content=b'abc',
            content_type='text/plain'
        )
        response = self.authorized_client.post(
            reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
            {'text': 'Тестовая запись', 'image': not_image, 'group': self.group.pk}, follow=True
        )
        self.assertFormError(
            response, 'form', 'image', 'Загрузите правильное изображение. '
            'Файл, который вы загрузили, поврежден или не является изображением.'
        )