from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.core.paginator import Page

from posts.forms import PostForm

from ..models import Follow, Group, Post

TEST_OF_POST = settings.NUMBER_OF_POSTS + 3
User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )

        cls.templates_url_names = {
            'posts:index': ('posts:index', '', 'posts/index.html'),
            'posts:group_list': (
                'posts:group_list',
                {'slug': cls.group.slug},
                'posts/group_list.html'
            ),
            'posts:profile': (
                'posts:profile',
                {'username': cls.user.username},
                'posts/profile.html'
            ),
            'posts:post_detail': (
                'posts:post_detail',
                {'post_id': cls.post.id},
                'posts/post_detail.html'
            ),
            'posts:post_create': (
                'posts:post_create',
                '',
                'posts/create_post.html'
            ),
            'posts:post_edit': (
                'posts:post_edit',
                {'post_id': cls.post.id},
                'posts/create_post.html'
            )
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_views_correct_template(self):
        '''URL-адрес использует соответствующий шаблон.'''
        for adress, kwargs, template in self.templates_url_names.values():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(
                    reverse(adress, kwargs=kwargs)
                )
                message = f'Ошибка: {adress} ожидал шаблон {template}'
                self.assertTemplateUsed(response, template, message)

    def check_post_info(self, context, page=True):
        if page:
            page_obj = context.get('page_obj')
            self.assertIsInstance(page_obj, Page, 'Ожидается модель Page')
            post = page_obj[0]
        else:
            post = context.get('post')
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)

    def test_forms_show_correct(self):
        """Проверка коректности формы."""
        pages_forms = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id, }),
        }
        for value in pages_forms:
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertIsInstance(
                    response.context.get('form'),
                    PostForm)
                self.assertIsInstance(
                    response.context.get('form').fields.get('text'),
                    forms.fields.CharField
                )
                self.assertIsInstance(
                    response.context.get('form').fields.get('group'),
                    forms.fields.ChoiceField
                )

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_info(response.context)

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context.get('group'), self.group)
        self.check_post_info(response.context)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context.get('author'), self.user)
        self.check_post_info(response.context)

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        self.check_post_info(response.context, False)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        post = Post.objects.create(
            text='Тестовый текст проверка как добавился',
            author=self.user,
            group=self.group)
        response_index = self.authorized_client.get(
            reverse('posts:index'))
        response_group = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': f'{self.group.slug}'}))
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        self.assertIn(post, index, 'поста нет на главной')
        self.assertIn(post, group, 'поста нет в профиле')
        self.assertIn(post, profile, 'поста нет в группе')

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попап в чужую группу."""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        posts_count = Post.objects.filter(group=self.group).count()
        post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user2,
            group=group2)
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        group = Post.objects.filter(group=self.group).count()
        profile = response_profile.context['page_obj']
        self.assertEqual(
            group, posts_count,
            'пост есть на странице группы, к которой не относится'
        )
        self.assertNotIn(post, profile,
                         'пост есть на странице чужого профиля')

    def test_cache_index_page(self):
        """Проверка работы кеша"""
        post = Post.objects.create(
            text='Пост под кеш',
            author=self.user)
        content_add = self.authorized_client.get(
            reverse('posts:index')).content
        post.delete()
        content_delete = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(content_add, content_delete)
        cache.clear()
        content_cache_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(content_add, content_cache_clear)

    def test_follow_page(self):
        # Проверяем, что страница подписок пуста
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)
        # Проверка подписки на автора поста
        Follow.objects.get_or_create(user=self.user, author=self.post.author)
        r_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(r_2.context["page_obj"]), 1)
        # проверка подписки у фоловера
        self.assertIn(self.post, r_2.context["page_obj"])

        # Проверка что пост не появился в избранных
        outsider = User.objects.create(username="NoName")
        self.authorized_client.force_login(outsider)
        r_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertNotIn(self.post, r_2.context["page_obj"])

        # Проверка отписки от автора поста
        Follow.objects.all().delete()
        r_3 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(r_3.context["page_obj"]), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='auth',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )

        for i in range(TEST_OF_POST):
            Post.objects.create(
                text=f'Пост #{i}',
                author=cls.user,
                group=cls.group
            )
        cls.url_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username}),
        ]

    def setUp(self):
        self.unauthorized_client = Client()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        posts_on_first_page = settings.NUMBER_OF_POSTS

        for reverse_ in self.url_pages:
            with self.subTest(reverse_=reverse_):
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_).context.get('page_obj')),
                    posts_on_first_page
                )

    def test_paginator_on_pages_two(self):
        """Проверка 2 страницы."""
        for page in self.url_pages:
            with self.subTest(page=page):
                posts_on_second_page = TEST_OF_POST - settings.NUMBER_OF_POSTS
                self.assertEqual(len(self.unauthorized_client.get(
                    page + '?page=2').context.get('page_obj')),
                    posts_on_second_page
                )
