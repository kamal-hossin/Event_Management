from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User, Group
from .forms import SignupForm, EventForm, CategoryForm
from .models import Event, Category
from .decorators import admin_required, organizer_required, participant_required

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            # Assign to Participant group
            participant_group, created = Group.objects.get_or_create(name='Participant')
            user.groups.add(participant_group)
            messages.success(request, 'Please check your email to activate your account.')
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated. You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid!')
        return redirect('signup')

@login_required
def dashboard(request):
    user = request.user
    if user.groups.filter(name='Admin').exists():
        events = Event.objects.all()
        categories = Category.objects.all()
        users = User.objects.all()
        return render(request, 'admin_dashboard.html', {'events': events, 'categories': categories, 'users': users})
    elif user.groups.filter(name='Organizer').exists():
        events = Event.objects.filter(organizer=user)
        categories = Category.objects.all()
        return render(request, 'organizer_dashboard.html', {'events': events, 'categories': categories})
    else:
        events = user.rsvp_events.all()
        return render(request, 'participant_dashboard.html', {'events': events})

@login_required
@participant_required
def event_list(request):
    events = Event.objects.all()
    return render(request, 'event_list.html', {'events': events})

@login_required
@participant_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'event_detail.html', {'event': event})

@login_required
@organizer_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect('dashboard')
    else:
        form = EventForm()
    return render(request, 'event_form.html', {'form': form})

@login_required
@organizer_required
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user and not request.user.groups.filter(name='Admin').exists():
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = EventForm(instance=event)
    return render(request, 'event_form.html', {'form': form})

@login_required
@organizer_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user and not request.user.groups.filter(name='Admin').exists():
        messages.error(request, 'You do not have permission to delete this event.')
        return redirect('dashboard')
    if request.method == 'POST':
        event.delete()
        return redirect('dashboard')
    return render(request, 'event_confirm_delete.html', {'event': event})

@login_required
@participant_required
def rsvp_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.user in event.rsvp_users.all():
        messages.info(request, 'You have already RSVP\'d to this event.')
    else:
        event.rsvp_users.add(request.user)
        messages.success(request, 'RSVP successful!')
    return redirect('event_detail', pk=pk)

@login_required
@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = CategoryForm()
    return render(request, 'category_form.html', {'form': form})

@login_required
@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('dashboard')
    return render(request, 'category_confirm_delete.html', {'category': category})

@login_required
@admin_required
def manage_users(request):
    users = User.objects.all()
    return render(request, 'manage_users.html', {'users': users})

@login_required
@admin_required
def change_role(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        role = request.POST.get('role')
        user.groups.clear()
        group, created = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        messages.success(request, f'Role changed to {role}')
        return redirect('manage_users')
    return render(request, 'change_role.html', {'user': user})
