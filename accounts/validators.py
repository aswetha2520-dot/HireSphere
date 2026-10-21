import os
import uuid
from django.core.exceptions import ValidationError
from django.conf import settings


def validate_resume_file(file):
    """
    Validate that the uploaded resume is a valid PDF and does not exceed maximum file size.
    """
    max_size = getattr(settings, 'MAX_RESUME_SIZE', 5 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f"Resume file size exceeds the {max_size // (1024 * 1024)}MB limit.")

    ext = os.path.splitext(file.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError("Only PDF files (.pdf) are allowed for resumes.")

    # Check content type if available on the uploaded file
    content_type = getattr(file, 'content_type', '')
    if content_type and content_type != 'application/pdf':
        raise ValidationError("Uploaded file is not a valid PDF document.")


def validate_image_file(file):
    """
    Validate that the uploaded image has an allowed extension and does not exceed maximum file size.
    """
    max_size = getattr(settings, 'MAX_IMAGE_SIZE', 2 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f"Image file size exceeds the {max_size // (1024 * 1024)}MB limit.")

    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported image format '{ext}'. Allowed formats: {', '.join(allowed_extensions)}."
        )


def candidate_resume_path(instance, filename):
    """Generate safe filename for candidate resumes."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('resumes', 'candidates', unique_name)


def candidate_picture_path(instance, filename):
    """Generate safe filename for candidate profile pictures."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('profile_pics', unique_name)


def employer_logo_path(instance, filename):
    """Generate safe filename for company logos."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('company_logos', unique_name)


def application_resume_path(instance, filename):
    """Generate safe filename for application-specific resumes."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('resumes', 'applications', unique_name)
