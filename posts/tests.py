from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

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
        cache.clear()
        post = Post.objects.first()
        response = self.authorized_client.get(reverse('index'))
        self.assertContains(response, post.text)
        response = self.authorized_client.get(reverse('profile', kwargs={'username': self.user.username}))
        self.assertContains(response, post.text)
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id})
        )
        self.assertContains(response, post.text)
        if post.group is not None:
            response = self.authorized_client.get(reverse('group_posts', kwargs={'slug': self.group.slug}))
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
        cache.clear()
        posts_after = Post.objects.all().count()
        self.assertNotEqual(posts_before, posts_after)
        self.post_is_real()
        response = self.authorized_client.get(reverse('index'))
        page = response.context['page']
        for test_post in page:
            self.assertContains(response, test_post.text)

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
        second_user = User.objects.create_user(username='second', email='testmail@testmail.com', password='testtest')
        find_text = 'Text for find on page'
        second_post = Post.objects.create(text=find_text, author=second_user)
        self.client.force_login(self.user)
        self.client.get(reverse('profile_follow', args=[second_user]))
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertContains(response, find_text)
        find_follow = Follow.objects.get(user=self.user, author=second_user)
        self.assertEqual(self.user, find_follow.user)
        self.client.get(reverse('profile_unfollow', args=[second_user]))
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertNotContains(response, find_text)

    def test_new_post_follow(self):
        second_user = User.objects.create_user(username='second', email='secondd@testmail.com', password='testtest')
        third_user = User.objects.create_user(username='third', email='third@testmail.com', password='testtest')
        self.client.force_login(self.user)
        self.client.get(reverse('profile_follow', args=[second_user]))
        find_text = 'Text for find on page'
        second_post = Post.objects.create(text=find_text, author=second_user)
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertContains(response, find_text)
        self.client.force_login(third_user)
        response = self.client.get(reverse('follow_index'))
        self.assertNotContains(response, find_text)

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
        response = self.authorized_client.get(reverse('index'))
        self.assertIn('img', str(response.content))
        response = self.authorized_client.get(reverse('profile', kwargs={'username': self.user.username}))
        self.assertIn('img', str(response.content))
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id})
        )
        self.assertIn('img', str(response.content))
        if post.group is not None:
            response = self.authorized_client.get(reverse('group_posts', kwargs={'slug': self.group.slug}))
            self.assertIn('img', str(response.content))

    def test_image_on_post_page(self):
        from PIL import Image
        img = Image.new('RGB', (60, 30), color='red')
        img.save('pil_red.png')
        with open(img, 'rb') as img:
            response = self.authorized_client.post(
                reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
                {'text': 'Тестовая запись', 'image': img, 'group': self.group.pk}, follow=True
            )
        self.assertEqual(response.status_code, 200)
        cache.clear()
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': self.user.username, 'post_id': self.post.id})
        )
        print(response.context)
        self.assertContains(response, 'img')
        self.assertIn('img', response.content.decode())  # Оставил для себя
        self.assertIn('img', str(response.content))  # Оставил для себя

    def test_image_on_pages(self):
        with open('/home/dvg/Изображения/1.jpg', 'rb') as img:
            response = self.authorized_client.post(
                reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
                {'text': 'Тестовая запись', 'image': img, 'group': self.group.pk}, follow=True
            )
            self.assertEqual(response.status_code, 200)
            response = self.authorized_client.get(
                reverse('post', kwargs={'username': self.user.username, 'post_id': self.post.id})
            )
            self.image_on_pages()

    def test_no_image_push(self):
        with open('/home/dvg/hw04_tests-master/manage.py', 'rb') as img:
            response = self.authorized_client.post(
                reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
                {'text': 'Тестовая запись', 'image': img, 'group': self.group.pk}, follow=True
            )
            self.assertFormError(
                response, 'form', 'image', 'Загрузите правильное изображение. '
                'Файл, который вы загрузили, поврежден или не является изображением.'
            )
