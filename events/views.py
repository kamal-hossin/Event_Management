from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db import models
from .forms import SignupForm, EventForm, CategoryForm, ProfileForm
from .models import Event, Category, CustomUser
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
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
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
        users = CustomUser.objects.all()
        return render(request, 'admin_dashboard.html', {'events': events, 'categories': categories, 'users': users})
    elif user.groups.filter(name='Organizer').exists():
        events = Event.objects.filter(organizer=user)
        categories = Category.objects.all()
        return render(request, 'organizer_dashboard.html', {'events': events, 'categories': categories})
    else:
        events = user.rsvp_events.all()
        return render(request, 'participant_dashboard.html', {'events': events})

@method_decorator([login_required, participant_required], name='dispatch')
class EventListView(ListView):
    model = Event
    template_name = 'event_list.html'
    context_object_name = 'events'

@method_decorator([login_required, participant_required], name='dispatch')
class EventDetailView(DetailView):
    model = Event
    template_name = 'event_detail.html'
    context_object_name = 'event'

@method_decorator([login_required, organizer_required], name='dispatch')
class EventCreateView(CreateView):
    model = Event
    form_class = EventForm
    template_name = 'event_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        return super().form_valid(form)

@method_decorator([login_required, organizer_required], name='dispatch')
class EventUpdateView(UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'event_form.html'
    success_url = reverse_lazy('dashboard')

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            models.Q(organizer=self.request.user) |
            models.Q(organizer__groups__name='Admin')
        )

    def dispatch(self, request, *args, **kwargs):
        event = self.get_object()
        if event.organizer != request.user and not request.user.groups.filter(name='Admin').exists():
            messages.error(request, 'You do not have permission to edit this event.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

@method_decorator([login_required, organizer_required], name='dispatch')
class EventDeleteView(DeleteView):
    model = Event
    template_name = 'event_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            models.Q(organizer=self.request.user) |
            models.Q(organizer__groups__name='Admin')
        )

    def dispatch(self, request, *args, **kwargs):
        event = self.get_object()
        if event.organizer != request.user and not request.user.groups.filter(name='Admin').exists():
            messages.error(request, 'You do not have permission to delete this event.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

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
def profile_view(request):
    return render(request, 'profile.html', {'user': request.user})

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

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
    users = CustomUser.objects.all()
    return render(request, 'manage_users.html', {'users': users})

@login_required
@admin_required
def change_role(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        role = request.POST.get('role')
        user.groups.clear()
        group, created = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        messages.success(request, f'Role changed to {role}')
        return redirect('manage_users')
    return render(request, 'change_role.html', {'user': user})
