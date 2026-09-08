from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import login


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get('email', '')
        if not email:
            return

        from accounts.models import User
        try:
            user = User.objects.get(email=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        extra = sociallogin.account.extra_data

        if not user.phone:
            user.phone = ''

        user.save()
        return user
