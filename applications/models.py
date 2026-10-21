from django.db import models
from django.conf import settings
from accounts.validators import validate_resume_file, application_resume_path


class Application(models.Model):
    """
    Model representing a job application submitted by a candidate.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        REVIEWED = 'REVIEWED', 'Reviewed'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        INTERVIEW = 'INTERVIEW', 'Interview'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    resume = models.FileField(
        upload_to=application_resume_path,
        blank=True,
        null=True,
        validators=[validate_resume_file],
        help_text="Custom resume submitted with this application (PDF only, max 5MB)."
    )
    cover_letter = models.TextField(blank=True, help_text="Cover letter or introduction note.")
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current recruitment stage for this application."
    )
    applied_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    employer_notes = models.TextField(
        blank=True,
        help_text="Private internal notes visible only to the employer and administrators."
    )

    class Meta:
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        ordering = ['-applied_date']
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'job'],
                name='unique_candidate_job_application'
            )
        ]

    def __str__(self):
        return f"{self.candidate.email} -> {self.job.title} ({self.status})"
