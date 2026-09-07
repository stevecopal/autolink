# accounts/views/team.py
"""
Accounts team-specific views (split from the main module).
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext_lazy as _

from ..forms import CustomUserCreationForm


class TeamDashboardView(View):
    """Team space landing view."""

    template_name = "dashboard/pages/client/team_dashboard.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        return render(request, self.template_name, {"team": "public"})


class TeamCreateView(View):
    """Create a private team."""

    template_name = "dashboard/pages/client/team_create.html"

    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.owner = request.user
            team.save()
            request.user.teams.add(team)
            messages.success(request, _("Team created successfully."))
            return redirect("accounts:team_dashboard")
        return render(request, self.template_name, {"form": form})
