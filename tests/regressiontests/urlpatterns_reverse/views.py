from django.http import HttpResponse
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy

from django.contrib.auth.decorators import user_passes_test

def empty_view(request, *args, **kwargs):
    return HttpResponse('')

def kwargs_view(request, arg1=1, arg2=2):
    return HttpResponse('')

def absolute_kwargs_view(request, arg1=1, arg2=2):
    return HttpResponse('')

class ViewClass(object):
    def __call__(self, request, *args, **kwargs):
        return HttpResponse('')

view_class_instance = ViewClass()

class LazyRedictView(RedirectView):
    url = reverse_lazy('named-lazy-url-redirected-to')

@user_passes_test(lambda u: u.is_authenticated(), login_url=reverse_lazy('some-login-page'))
def login_required_view(request):
    return HttpResponse('Hello you')

def bad_view(request, *args, **kwargs):
    raise ValueError("I don't think I'm getting good value for this view")
