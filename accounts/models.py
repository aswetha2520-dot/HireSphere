from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from .validators import (
    validate_resume_file,
    validate_image_file,
    candidate_resume_path,
    candidate_picture_path,
    employer_logo_path,
)


class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email address must be provided.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model supporting Candidate, Employer, and Admin roles
    with email-based authentication.
    """

    class Role(models.TextChoices):
        CANDIDATE = 'CANDIDATE', 'Candidate'
        EMPLOYER = 'EMPLOYER', 'Employer'
        ADMIN = 'ADMIN', 'Admin'

    email = models.EmailField(
        verbose_name='Email address',
        unique=True,
        max_length=255,
        help_text='Unique email address used for login.'
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CANDIDATE,
        help_text='User role defining access permissions.'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this user should be treated as active.'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Designates whether the user can log into the Django admin site.'
    )
    is_superuser = models.BooleanField(
        default=False,
        help_text='Designates whether the user has all permissions without explicitly assigning them.'
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_candidate(self):
        return self.role == self.Role.CANDIDATE

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_staff or self.is_superuser

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email


class CandidateProfile(models.Model):
    """
    Profile specific to Candidates / Job Seekers.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='candidate_profile',
        limit_choices_to={'role': User.Role.CANDIDATE}
    )
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    skills = models.TextField(
        blank=True,
        help_text='Comma-separated or multi-line skills (e.g., Python, Django, Docker, PostgreSQL).'
    )
    education = models.TextField(
        blank=True,
        help_text='Degrees, universities, graduation years.'
    )
    experience = models.TextField(
        blank=True,
        help_text='Work experience history, previous roles and accomplishments.'
    )
    resume = models.FileField(
        upload_to=candidate_resume_path,
        blank=True,
        null=True,
        validators=[validate_resume_file],
        help_text='PDF resume file (max 5MB).'
    )
    profile_picture = models.ImageField(
        upload_to=candidate_picture_path,
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text='Profile photo (JPG, PNG, WebP, max 2MB).'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Candidate Profile'
        verbose_name_plural = 'Candidate Profiles'

    def __str__(self):
        return f"Candidate Profile: {self.full_name or self.user.email}"


class EmployerProfile(models.Model):
    """
    Profile specific to Employers / Recruiters.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employer_profile',
        limit_choices_to={'role': User.Role.EMPLOYER}
    )
    company_name = models.CharField(max_length=255, default='Company Name')
    company_description = models.TextField(blank=True)
    website = models.URLField(max_length=500, blank=True)
    company_location = models.CharField(max_length=255, blank=True)
    company_logo = models.ImageField(
        upload_to=employer_logo_path,
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text='Company logo image (JPG, PNG, WebP, max 2MB).'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Employer Profile'
        verbose_name_plural = 'Employer Profiles'

    def __str__(self):
        return f"Employer Profile: {self.company_name} ({self.user.email})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Automatically initialize appropriate profile on user creation.
    """
    if created:
        if instance.role == User.Role.CANDIDATE:
            CandidateProfile.objects.get_or_create(
                user=instance,
                defaults={'full_name': f"{instance.first_name} {instance.last_name}".strip()}
            )
        elif instance.role == User.Role.EMPLOYER:
            EmployerProfile.objects.get_or_create(
                user=instance,
                defaults={'company_name': f"{instance.first_name}'s Organization" if instance.first_name else "Organization"}
            )
