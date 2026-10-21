from django.db import models
from django.conf import settings
from django.utils import timezone


class Job(models.Model):
    """
    Model representing a job posting created by an Employer.
    """

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full-time'
        PART_TIME = 'PART_TIME', 'Part-time'
        CONTRACT = 'CONTRACT', 'Contract'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        FREELANCE = 'FREELANCE', 'Freelance'

    class ExperienceLevel(models.TextChoices):
        ENTRY = 'ENTRY', 'Entry Level'
        MID = 'MID', 'Mid Level'
        SENIOR = 'SENIOR', 'Senior Level'
        LEAD = 'LEAD', 'Lead'
        EXECUTIVE = 'EXECUTIVE', 'Executive'

    class RemoteStatus(models.TextChoices):
        ONSITE = 'ONSITE', 'On-site'
        HYBRID = 'HYBRID', 'Hybrid'
        REMOTE = 'REMOTE', 'Remote'

    title = models.CharField(max_length=255, help_text="e.g. Senior Backend Engineer (Django/Python)")
    description = models.TextField(help_text="Detailed overview of the role.")
    responsibilities = models.TextField(blank=True, help_text="Day-to-day responsibilities.")
    required_skills = models.TextField(blank=True, help_text="List or comma-separated required skills.")
    qualifications = models.TextField(blank=True, help_text="Minimum degrees or experience required.")
    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    experience_level = models.CharField(
        max_length=50,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.MID
    )
    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum annual or monthly salary."
    )
    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum annual or monthly salary."
    )
    location = models.CharField(max_length=255, help_text="e.g. San Francisco, CA or Remote")
    remote_status = models.CharField(
        max_length=50,
        choices=RemoteStatus.choices,
        default=RemoteStatus.ONSITE
    )
    number_of_openings = models.PositiveIntegerField(default=1)
    application_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this job posting is currently open for applications."
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} at {self.company_name}"

    @property
    def is_deadline_passed(self):
        if self.application_deadline:
            return self.application_deadline < timezone.now().date()
        return False

    @property
    def is_open(self):
        return self.is_active and not self.is_deadline_passed

    @property
    def company_name(self):
        if hasattr(self.employer, 'employer_profile'):
            return self.employer.employer_profile.company_name
        return self.employer.email

    @property
    def company_location(self):
        if hasattr(self.employer, 'employer_profile'):
            return self.employer.employer_profile.company_location
        return ""

    @property
    def company_website(self):
        if hasattr(self.employer, 'employer_profile'):
            return self.employer.employer_profile.website
        return ""
