from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )

        cls.user = User.objects.create_user(
            username='user')

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

        cls.templates_url_names_general = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
        }

        cls.templates_url_names_private = {
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostModelTest.user)

    def test_urls_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        for adress in self.templates_url_names_general:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_exists_at_desired_location(self):
        """Страницы доступны авторизованному пользователю."""
        for adress in self.templates_url_names_general:
            with self.subTest(adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_redirect_guest_client(self):
        """Редирект неавторизованного пользователя"""
        for adress in self.templates_url_names_private:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertRedirects(
                    response, (f'/auth/login/?next={adress}'))

    def test_posts_post_id_edit_url_exists_at_author(self):
        """Страница доступна только автору."""
        self.user = User.objects.get(username=self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(PostModelTest.user)
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_auth_login(self):
        """Страница доступна авторизованному пользователю."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_unexisting_page_at_desired_location(self):
        """Страница должна выдать ошибку."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        self.templates_url_names_general.update(
            self.templates_url_names_private
        )
        for url, template in self.templates_url_names_general.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
