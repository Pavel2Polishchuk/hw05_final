from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост длинной больше 15 символов',
        )

    def setUp(self):
        self.post = PostModelTest.post
        self.group = PostModelTest.group

    def test_models_have_correct_object_names(self):
        vals = (
            (str(self.post), self.post.text[:15]),
            (str(self.group), self.group.title),
        )
        for value, expected in vals:
            with self.subTest(value=value):
                self.assertEqual(value, expected)
