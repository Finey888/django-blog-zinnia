"""Test cases for Zinnia's admin"""
from __future__ import unicode_literals

from django.test import TestCase
from django.test import RequestFactory
from django.contrib.sites.models import Site
from django.utils.translation import activate
from django.utils.translation import deactivate
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.tests.utils import skipIfCustomUser

from zinnia import settings
from zinnia.managers import PUBLISHED
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.admin.entry import EntryAdmin
from zinnia.admin.category import CategoryAdmin


class BaseAdminTestCase(TestCase):
    rich_urls = 'zinnia.tests.urls'
    poor_urls = 'zinnia.tests.poor_urls'
    urls = rich_urls
    model_class = None
    admin_class = None

    def setUp(self):
        activate('en')
        self.site = AdminSite()
        self.admin = self.admin_class(
            self.model_class, self.site)

    def tearDown(self):
        """
        Be sure to restore the good urls to use
        if a test fail before restoring the urls.
        """
        self.urls = self.rich_urls
        self._urlconf_setup()
        deactivate()

    def check_with_rich_and_poor_urls(self, func, args,
                                      result_rich, result_poor):
        self.assertEquals(func(*args), result_rich)
        self.urls = self.poor_urls
        self._urlconf_setup()
        self.assertEquals(func(*args), result_poor)
        self.urls = self.rich_urls
        self._urlconf_setup()


class TestMessageBackend(object):
    """Message backend for testing"""
    def __init__(self, *ka, **kw):
        self.messages = []

    def add(self, *ka, **kw):
        self.messages.append((ka, kw))


@skipIfCustomUser
class EntryAdminTestCase(BaseAdminTestCase):
    """Test case for Entry Admin"""
    model_class = Entry
    admin_class = EntryAdmin

    def setUp(self):
        super(EntryAdminTestCase, self).setUp()
        params = {'title': 'My title',
                  'content': 'My content',
                  'slug': 'my-title'}
        self.entry = Entry.objects.create(**params)
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')

    def test_get_title(self):
        self.assertEquals(self.admin.get_title(self.entry),
                          'My title (2 words)')
        self.entry.comment_count = 1
        self.entry.save()
        self.assertEquals(self.admin.get_title(self.entry),
                          'My title (2 words) (1 reaction)')
        self.entry.pingback_count = 1
        self.entry.save()
        self.assertEquals(self.admin.get_title(self.entry),
                          'My title (2 words) (2 reactions)')

    def test_get_authors(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_authors, (self.entry,),
            '', '')
        author_1 = Author.objects.create_user(
            'author-1', 'author1@example.com')
        author_2 = Author.objects.create_user(
            'author-2', 'author2@example.com')
        self.entry.authors.add(author_1)
        self.check_with_rich_and_poor_urls(
            self.admin.get_authors, (self.entry,),
            '<a href="/authors/author-1/" target="blank">author-1</a>',
            'author-1')
        self.entry.authors.add(author_2)
        self.check_with_rich_and_poor_urls(
            self.admin.get_authors, (self.entry,),
            '<a href="/authors/author-1/" target="blank">author-1</a>, '
            '<a href="/authors/author-2/" target="blank">author-2</a>',
            'author-1, author-2',)

    def test_get_catgories(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_categories, (self.entry,),
            '', '')
        category_1 = Category.objects.create(title='Category 1',
                                             slug='category-1')
        category_2 = Category.objects.create(title='Category 2',
                                             slug='category-2')
        self.entry.categories.add(category_1)
        self.check_with_rich_and_poor_urls(
            self.admin.get_categories, (self.entry,),
            '<a href="/categories/category-1/" target="blank">Category 1</a>',
            'Category 1')
        self.entry.categories.add(category_2)
        self.check_with_rich_and_poor_urls(
            self.admin.get_categories, (self.entry,),
            '<a href="/categories/category-1/" target="blank">Category 1</a>, '
            '<a href="/categories/category-2/" target="blank">Category 2</a>',
            'Category 1, Category 2')

    def test_get_tags(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_tags, (self.entry,),
            '', '')
        self.entry.tags = 'zinnia'
        self.check_with_rich_and_poor_urls(
            self.admin.get_tags, (self.entry,),
            '<a href="/tags/zinnia/" target="blank">zinnia</a>',
            'zinnia')
        self.entry.tags = 'zinnia, test'
        self.check_with_rich_and_poor_urls(
            self.admin.get_tags, (self.entry,),
            '<a href="/tags/test/" target="blank">test</a>, '
            '<a href="/tags/zinnia/" target="blank">zinnia</a>',
            'zinnia, test')  # Yes, this is not the same order...

    def test_get_sites(self):
        self.assertEquals(self.admin.get_sites(self.entry), '')
        self.entry.sites.add(Site.objects.get_current())
        self.check_with_rich_and_poor_urls(
            self.admin.get_sites, (self.entry,),
            '<a href="http://example.com/" target="blank">example.com</a>',
            '<a href="http://example.com" target="blank">example.com</a>')

    def test_get_short_url(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_short_url, (self.entry,),
            '<a href="http://example.com/1/" target="blank">'
            'http://example.com/1/</a>',
            '<a href="%(url)s" target="blank">'
            '%(url)s</a>' % {'url': self.entry.get_absolute_url()})

    def test_get_is_visible(self):
        self.assertEquals(self.admin.get_is_visible(self.entry),
                          self.entry.is_visible)

    def test_save_model(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        self.request.user = user
        form = EntryAdmin.form({'title': 'title'})
        form.is_valid()
        self.entry.status = PUBLISHED
        self.admin.save_model(self.request, self.entry,
                              form, False)
        self.assertEquals(len(form.cleaned_data['authors']), 1)
        self.assertEquals(self.entry.excerpt, self.entry.content)

    def test_queryset(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        self.entry.authors.add(user)
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        params = {'title': 'My root title',
                  'content': 'My root content',
                  'slug': 'my-root-titile'}
        root_entry = Entry.objects.create(**params)
        root_entry.authors.add(root)
        self.request.user = user
        self.assertEquals(len(self.admin.queryset(self.request)), 1)
        self.request.user = root
        self.assertEquals(len(self.admin.queryset(self.request)), 2)

    def test_formfield_for_manytomany(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        user.is_staff = True
        user.save()
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        self.request.user = user
        field = self.admin.formfield_for_manytomany(
            Entry.authors.field, self.request)
        self.assertEquals(field.queryset.count(), 1)
        self.request.user = root
        field = self.admin.formfield_for_manytomany(
            Entry.authors.field, self.request)
        self.assertEquals(field.queryset.count(), 2)

    def test_get_readonly_fields(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        self.request.user = user
        self.assertEquals(self.admin.get_readonly_fields(self.request),
                          ['status'])
        self.request.user = root
        self.assertEquals(self.admin.get_readonly_fields(self.request),
                          ())

    def test_get_actions(self):
        original_user_twitter = settings.USE_TWITTER
        original_ping_directories = settings.PING_DIRECTORIES
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        self.request.user = user
        settings.USE_TWITTER = True
        settings.PING_DIRECTORIES = True
        self.assertEquals(
            self.admin.get_actions(self.request).keys(),
            ['delete_selected',
             'close_comments',
             'close_pingbacks',
             'close_trackbacks',
             'ping_directories',
             'make_tweet',
             'put_on_top',
             'mark_featured',
             'unmark_featured'])
        settings.USE_TWITTER = False
        settings.PING_DIRECTORIES = False
        self.assertEquals(
            self.admin.get_actions(self.request).keys(),
            ['delete_selected',
             'close_comments',
             'close_pingbacks',
             'close_trackbacks',
             'put_on_top',
             'mark_featured',
             'unmark_featured'])
        self.request.user = root
        self.assertEquals(
            self.admin.get_actions(self.request).keys(),
            ['delete_selected',
             'make_mine',
             'make_published',
             'make_hidden',
             'close_comments',
             'close_pingbacks',
             'close_trackbacks',
             'put_on_top',
             'mark_featured',
             'unmark_featured'])
        settings.USE_TWITTER = original_user_twitter
        settings.PING_DIRECTORIES = original_ping_directories

    def test_make_mine(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        self.request.user = user
        self.request._messages = TestMessageBackend()
        self.assertEquals(user.entries.count(), 0)
        self.admin.make_mine(self.request, Entry.objects.all())
        self.assertEquals(user.entries.count(), 1)
        self.assertEquals(len(self.request._messages.messages), 1)


class CategoryAdminTestCase(BaseAdminTestCase):
    """Test cases for Category Admin"""
    model_class = Category
    admin_class = CategoryAdmin

    def test_get_tree_path(self):
        category = Category.objects.create(title='Category', slug='cat')

        self.check_with_rich_and_poor_urls(
            self.admin.get_tree_path, (category,),
            '<a href="/categories/cat/" target="blank">/cat/</a>',
            '/cat/')
