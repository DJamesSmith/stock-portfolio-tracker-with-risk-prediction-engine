from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from config.application_logger import ApplicationLogger
from .models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirmation = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")

        if not password or not password_confirmation:
            return cleaned_data

        if password != password_confirmation:
            self.add_error("password_confirmation", "Passwords do not match.")
            return cleaned_data

        temporary_user = User(username=cleaned_data.get("username"), email=cleaned_data.get("email"))

        try:
            validate_password(password, temporary_user)
        except forms.ValidationError as error:
            self.add_error("password", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.INVESTOR
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            ApplicationLogger.info(f"Investor registration completed: username={user.username}")

        return user


class LoginForm(forms.Form):
    username_or_email = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        other_users = User.objects.exclude(pk=self.instance.pk)

        if other_users.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        other_users = User.objects.exclude(pk=self.instance.pk)

        if other_users.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already exists.")

        return email


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    new_password_confirmation = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data["old_password"]

        if not self.user.check_password(old_password):
            raise forms.ValidationError("Current password is incorrect.")

        return old_password

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        new_password_confirmation = cleaned_data.get("new_password_confirmation")

        if not new_password or not new_password_confirmation:
            return cleaned_data

        if new_password != new_password_confirmation:
            self.add_error("new_password_confirmation", "Passwords do not match.")
            return cleaned_data

        if old_password and new_password == old_password:
            self.add_error("new_password", "New password must be different from the current password.")
            return cleaned_data

        try:
            validate_password(new_password, self.user)
        except forms.ValidationError as error:
            self.add_error("new_password", error)

        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save()
        ApplicationLogger.info(f"Password changed: username={self.user.username}")
        return self.user


class AdminUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["role", "assigned_analyst"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_role = self.instance.role
        self.fields["assigned_analyst"].required = False
        self.fields["assigned_analyst"].queryset = User.objects.filter(role=User.Role.ANALYST, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        analyst = cleaned_data.get("assigned_analyst")

        if analyst is None:
            return cleaned_data

        if role != User.Role.INVESTOR:
            self.add_error("assigned_analyst", "Only investors can have an assigned analyst.")
        elif analyst.pk == self.instance.pk:
            self.add_error("assigned_analyst", "A user cannot be their own analyst.")

        return cleaned_data

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save()

            if self.old_role == User.Role.ANALYST and user.role != User.Role.ANALYST:
                cleared = user.assigned_investors.update(assigned_analyst=None)
                ApplicationLogger.info(f"Analyst demoted: username={user.username}, investors_unassigned={cleared}")

        ApplicationLogger.info(
            f"Admin updated user: username={user.username}, role={self.old_role}->{user.role}, "
            f"assigned_analyst={user.assigned_analyst_id}"
        )
        return user


def build_admin_update_data(user, submitted_data):
    role = submitted_data.get("role") or user.role

    if "assigned_analyst" in submitted_data:
        analyst = submitted_data.get("assigned_analyst")
    elif role == User.Role.INVESTOR:
        analyst = user.assigned_analyst_id
    else:
        analyst = None

    if analyst is None:
        analyst = ""

    return {"role": role, "assigned_analyst": analyst}


def build_profile_data(user, submitted_data):
    return {
        "username": submitted_data.get("username", user.username),
        "email": submitted_data.get("email", user.email),
    }
