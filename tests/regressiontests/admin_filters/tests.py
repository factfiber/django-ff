from __future__ import with_statement

import datetime

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, RequestFactory
from django.utils.encoding import force_unicode

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin import site, ModelAdmin, SimpleListFilter

from models import Book

def select_by(dictlist, key, value):
    return [x for x in dictlist if x[key] == value][0]


class DecadeListFilter(SimpleListFilter):

    def lookups(self, request, model_admin):
        return (
            ('the 80s', "the 1980's"),
            ('the 90s', "the 1990's"),
            ('the 00s', "the 2000's"),
            ('other', "other decades"),
        )

    def queryset(self, request, queryset):
        decade = self.value()
        if decade == 'the 80s':
            return queryset.filter(year__gte=1980, year__lte=1989)
        if decade == 'the 90s':
            return queryset.filter(year__gte=1990, year__lte=1999)
        if decade == 'the 00s':
            return queryset.filter(year__gte=2000, year__lte=2009)

class DecadeListFilterWithTitleAndParameter(DecadeListFilter):
    title = 'publication decade'
    parameter_name = 'publication-decade'

class DecadeListFilterWithoutTitle(DecadeListFilter):
    parameter_name = 'publication-decade'

class DecadeListFilterWithoutParameter(DecadeListFilter):
    title = 'publication decade'

class DecadeListFilterWithNoneReturningLookups(DecadeListFilterWithTitleAndParameter):

    def lookups(self, request, model_admin):
        pass

class DecadeListFilterWithQuerysetBasedLookups(DecadeListFilterWithTitleAndParameter):

    def lookups(self, request, model_admin):
        qs = model_admin.queryset(request)
        if qs.filter(year__gte=1980, year__lte=1989).exists():
            yield ('the 80s', "the 1980's")
        if qs.filter(year__gte=1990, year__lte=1999).exists():
            yield ('the 90s', "the 1990's")
        if qs.filter(year__gte=2000, year__lte=2009).exists():
            yield ('the 00s', "the 2000's")

class CustomUserAdmin(UserAdmin):
    list_filter = ('books_authored', 'books_contributed')

class BookAdmin(ModelAdmin):
    list_filter = ('year', 'author', 'contributors', 'is_best_seller', 'date_registered')
    order_by = '-id'

class DecadeFilterBookAdmin(ModelAdmin):
    list_filter = ('author', DecadeListFilterWithTitleAndParameter)
    order_by = '-id'

class DecadeFilterBookAdminWithoutTitle(ModelAdmin):
    list_filter = (DecadeListFilterWithoutTitle,)

class DecadeFilterBookAdminWithoutParameter(ModelAdmin):
    list_filter = (DecadeListFilterWithoutParameter,)

class DecadeFilterBookAdminWithNoneReturningLookups(ModelAdmin):
    list_filter = (DecadeListFilterWithNoneReturningLookups,)

class DecadeFilterBookAdminWithQuerysetBasedLookups(ModelAdmin):
    list_filter = (DecadeListFilterWithQuerysetBasedLookups,)

class ListFiltersTests(TestCase):

    def setUp(self):
        self.today = datetime.date.today()
        self.one_week_ago = self.today - datetime.timedelta(days=7)

        self.request_factory = RequestFactory()

        # Users
        self.alfred = User.objects.create_user('alfred', 'alfred@example.com')
        self.bob = User.objects.create_user('bob', 'bob@example.com')
        self.lisa = User.objects.create_user('lisa', 'lisa@example.com')

        # Books
        self.djangonaut_book = Book.objects.create(title='Djangonaut: an art of living', year=2009, author=self.alfred, is_best_seller=True, date_registered=self.today)
        self.bio_book = Book.objects.create(title='Django: a biography', year=1999, author=self.alfred, is_best_seller=False)
        self.django_book = Book.objects.create(title='The Django Book', year=None, author=self.bob, is_best_seller=None, date_registered=self.today)
        self.gipsy_book = Book.objects.create(title='Gipsy guitar for dummies', year=2002, is_best_seller=True, date_registered=self.one_week_ago)
        self.gipsy_book.contributors = [self.bob, self.lisa]
        self.gipsy_book.save()

    def get_changelist(self, request, model, modeladmin):
        return ChangeList(request, model, modeladmin.list_display, modeladmin.list_display_links,
            modeladmin.list_filter, modeladmin.date_hierarchy, modeladmin.search_fields,
            modeladmin.list_select_related, modeladmin.list_per_page, modeladmin.list_editable, modeladmin)

    def test_datefieldlistfilter(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        changelist = self.get_changelist(request, Book, modeladmin)

        request = self.request_factory.get('/', {'date_registered__year': self.today.year,
                                                 'date_registered__month': self.today.month,
                                                 'date_registered__day': self.today.day})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(force_unicode(filterspec.title), u'date_registered')
        choice = select_by(filterspec.choices(changelist), "display", "Today")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?date_registered__day=%s'
                                                 '&date_registered__month=%s'
                                                 '&date_registered__year=%s'
                                                % (self.today.day, self.today.month, self.today.year))

        request = self.request_factory.get('/', {'date_registered__year': self.today.year,
                                                 'date_registered__month': self.today.month})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        if (self.today.year, self.today.month) == (self.one_week_ago.year, self.one_week_ago.month):
            # In case one week ago is in the same month.
            self.assertEqual(list(queryset), [self.gipsy_book, self.django_book, self.djangonaut_book])
        else:
            self.assertEqual(list(queryset), [self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(force_unicode(filterspec.title), u'date_registered')
        choice = select_by(filterspec.choices(changelist), "display", "This month")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?date_registered__month=%s'
                                                 '&date_registered__year=%s'
                                                % (self.today.month, self.today.year))

        request = self.request_factory.get('/', {'date_registered__year': self.today.year})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        if self.today.year == self.one_week_ago.year:
            # In case one week ago is in the same year.
            self.assertEqual(list(queryset), [self.gipsy_book, self.django_book, self.djangonaut_book])
        else:
            self.assertEqual(list(queryset), [self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(force_unicode(filterspec.title), u'date_registered')
        choice = select_by(filterspec.choices(changelist), "display", "This year")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?date_registered__year=%s'
                                                % (self.today.year))

        request = self.request_factory.get('/', {'date_registered__gte': self.one_week_ago.strftime('%Y-%m-%d'),
                                                 'date_registered__lte': self.today.strftime('%Y-%m-%d')})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.gipsy_book, self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(force_unicode(filterspec.title), u'date_registered')
        choice = select_by(filterspec.choices(changelist), "display", "Past 7 days")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?date_registered__gte=%s'
                                                 '&date_registered__lte=%s'
                                                % (self.one_week_ago.strftime('%Y-%m-%d'), self.today.strftime('%Y-%m-%d')))

    def test_allvaluesfieldlistfilter(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/', {'year__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.django_book])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title), u'year')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?year__isnull=True')

        request = self.request_factory.get('/', {'year': '2002'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title), u'year')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?year=2002')

    def test_relatedfieldlistfilter_foreignkey(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/', {'author__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.gipsy_book])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'author')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?author__isnull=True')

        request = self.request_factory.get('/', {'author__id__exact': self.alfred.pk})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'author')
        # order of choices depends on User model, which has no order
        choice = select_by(filterspec.choices(changelist), "display", "alfred")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?author__id__exact=%d' % self.alfred.pk)

    def test_relatedfieldlistfilter_manytomany(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/', {'contributors__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.django_book, self.bio_book, self.djangonaut_book])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEqual(force_unicode(filterspec.title), u'user')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?contributors__isnull=True')

        request = self.request_factory.get('/', {'contributors__id__exact': self.bob.pk})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEqual(force_unicode(filterspec.title), u'user')
        choice = select_by(filterspec.choices(changelist), "display", "bob")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?contributors__id__exact=%d' % self.bob.pk)

    def test_relatedfieldlistfilter_reverse_relationships(self):
        modeladmin = CustomUserAdmin(User, site)

        # FK relationship -----
        request = self.request_factory.get('/', {'books_authored__isnull': 'True'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.lisa])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?books_authored__isnull=True')

        request = self.request_factory.get('/', {'books_authored__id__exact': self.bio_book.pk})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title), u'book')
        choice = select_by(filterspec.choices(changelist), "display", self.bio_book.title)
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?books_authored__id__exact=%d' % self.bio_book.pk)

        # M2M relationship -----
        request = self.request_factory.get('/', {'books_contributed__isnull': 'True'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.alfred])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?books_contributed__isnull=True')

        request = self.request_factory.get('/', {'books_contributed__id__exact': self.django_book.pk})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'book')
        choice = select_by(filterspec.choices(changelist), "display", self.django_book.title)
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?books_contributed__id__exact=%d' % self.django_book.pk)

    def test_booleanfieldlistfilter(self):
        modeladmin = BookAdmin(Book, site)
        self.verify_booleanfieldlistfilter(modeladmin)

    def test_booleanfieldlistfilter_tuple(self):
        modeladmin = BookAdmin(Book, site)
        self.verify_booleanfieldlistfilter(modeladmin)

    def verify_booleanfieldlistfilter(self, modeladmin):
        request = self.request_factory.get('/')
        changelist = self.get_changelist(request, Book, modeladmin)

        request = self.request_factory.get('/', {'is_best_seller__exact': 0})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(force_unicode(filterspec.title), u'is_best_seller')
        choice = select_by(filterspec.choices(changelist), "display", "No")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller__exact=0')

        request = self.request_factory.get('/', {'is_best_seller__exact': 1})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.gipsy_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(force_unicode(filterspec.title), u'is_best_seller')
        choice = select_by(filterspec.choices(changelist), "display", "Yes")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller__exact=1')

        request = self.request_factory.get('/', {'is_best_seller__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.django_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(force_unicode(filterspec.title), u'is_best_seller')
        choice = select_by(filterspec.choices(changelist), "display", "Unknown")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller__isnull=True')

    def test_simplelistfilter(self):
        modeladmin = DecadeFilterBookAdmin(Book, site)

        # Make sure that the first option is 'All' ---------------------------

        request = self.request_factory.get('/', {})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), list(Book.objects.all().order_by('-id')))

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[0]['display'], u'All')
        self.assertEqual(choices[0]['selected'], True)
        self.assertEqual(choices[0]['query_string'], '?')

        # Look for books in the 1980s ----------------------------------------

        request = self.request_factory.get('/', {'publication-decade': 'the 80s'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[1]['display'], u'the 1980\'s')
        self.assertEqual(choices[1]['selected'], True)
        self.assertEqual(choices[1]['query_string'], '?publication-decade=the+80s')

        # Look for books in the 1990s ----------------------------------------

        request = self.request_factory.get('/', {'publication-decade': 'the 90s'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[2]['display'], u'the 1990\'s')
        self.assertEqual(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?publication-decade=the+90s')

        # Look for books in the 2000s ----------------------------------------

        request = self.request_factory.get('/', {'publication-decade': 'the 00s'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.gipsy_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[3]['display'], u'the 2000\'s')
        self.assertEqual(choices[3]['selected'], True)
        self.assertEqual(choices[3]['query_string'], '?publication-decade=the+00s')

        # Combine multiple filters -------------------------------------------

        request = self.request_factory.get('/', {'publication-decade': 'the 00s', 'author__id__exact': self.alfred.pk})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set(request)
        self.assertEqual(list(queryset), [self.djangonaut_book])

        # Make sure the correct choices are selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title), u'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[3]['display'], u'the 2000\'s')
        self.assertEqual(choices[3]['selected'], True)
        self.assertEqual(choices[3]['query_string'], '?publication-decade=the+00s&author__id__exact=%s' % self.alfred.pk)

        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title), u'author')
        choice = select_by(filterspec.choices(changelist), "display", "alfred")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?publication-decade=the+00s&author__id__exact=%s' % self.alfred.pk)

    def test_listfilter_without_title(self):
        """
        Any filter must define a title.
        """
        modeladmin = DecadeFilterBookAdminWithoutTitle(Book, site)
        request = self.request_factory.get('/', {})
        self.assertRaisesRegexp(ImproperlyConfigured,
            "The list filter 'DecadeListFilterWithoutTitle' does not specify a 'title'.",
            self.get_changelist, request, Book, modeladmin)

    def test_simplelistfilter_without_parameter(self):
        """
        Any SimpleListFilter must define a parameter_name.
        """
        modeladmin = DecadeFilterBookAdminWithoutParameter(Book, site)
        request = self.request_factory.get('/', {})
        self.assertRaisesRegexp(ImproperlyConfigured,
            "The list filter 'DecadeListFilterWithoutParameter' does not specify a 'parameter_name'.",
            self.get_changelist, request, Book, modeladmin)

    def test_simplelistfilter_with_none_returning_lookups(self):
        """
        A SimpleListFilter lookups method can return None but disables the
        filter completely.
        """
        modeladmin = DecadeFilterBookAdminWithNoneReturningLookups(Book, site)
        request = self.request_factory.get('/', {})
        changelist = self.get_changelist(request, Book, modeladmin)
        filterspec = changelist.get_filters(request)[0]
        self.assertEqual(len(filterspec), 0)

    def test_simplelistfilter_with_queryset_based_lookups(self):
        modeladmin = DecadeFilterBookAdminWithQuerysetBasedLookups(Book, site)
        request = self.request_factory.get('/', {})
        changelist = self.get_changelist(request, Book, modeladmin)

        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title), u'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(len(choices), 3)

        self.assertEqual(choices[0]['display'], u'All')
        self.assertEqual(choices[0]['selected'], True)
        self.assertEqual(choices[0]['query_string'], '?')

        self.assertEqual(choices[1]['display'], u'the 1990\'s')
        self.assertEqual(choices[1]['selected'], False)
        self.assertEqual(choices[1]['query_string'], '?publication-decade=the+90s')

        self.assertEqual(choices[2]['display'], u'the 2000\'s')
        self.assertEqual(choices[2]['selected'], False)
        self.assertEqual(choices[2]['query_string'], '?publication-decade=the+00s')
