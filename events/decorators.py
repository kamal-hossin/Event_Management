from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test

def admin_required(function):
    def wrap(request, *args, **kwargs):
        if request.user.groups.filter(name='Admin').exists():
            return function(request, *args, **kwargs)
        else:
            raise PermissionDenied
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap

def organizer_required(function):
    def wrap(request, *args, **kwargs):
        if request.user.groups.filter(name__in=['Admin', 'Organizer']).exists():
            return function(request, *args, **kwargs)
        else:
            raise PermissionDenied
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap

def participant_required(function):
    def wrap(request, *args, **kwargs):
        if request.user.groups.filter(name__in=['Admin', 'Organizer', 'Participant']).exists():
            return function(request, *args, **kwargs)
        else:
            raise PermissionDenied
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
