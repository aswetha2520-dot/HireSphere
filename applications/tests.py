from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User, CandidateProfile
from accounts.tests import create_test_pdf
from jobs.models import Job
from .models import Application


class ApplicationManagementTests(APITestCase):
    def setUp(self):
        # 1. Employer
        self.employer_user = User.objects.create_user(
            email="employer@jobs.com",
            password="Password123!",
            role=User.Role.EMPLOYER
        )

        # 2. Second Employer
        self.other_employer = User.objects.create_user(
            email="other_employer@jobs.com",
            password="Password123!",
            role=User.Role.EMPLOYER
        )

        # 3. Candidate
        self.candidate_user = User.objects.create_user(
            email="candidate@jobs.com",
            password="Password123!",
            role=User.Role.CANDIDATE
        )
        # Give candidate a resume on profile
        pdf_file = create_test_pdf("profile_resume.pdf")
        self.candidate_user.candidate_profile.resume = pdf_file
        self.candidate_user.candidate_profile.save()

        # 4. Candidate without resume
        self.candidate_no_resume = User.objects.create_user(
            email="no_resume@jobs.com",
            password="Password123!",
            role=User.Role.CANDIDATE
        )

        # 5. Admin
        self.admin_user = User.objects.create_superuser(
            email="admin@jobs.com",
            password="Password123!"
        )

        # Active Job
        self.active_job = Job.objects.create(
            title="Full Stack Django Engineer",
            description="Build scalable web applications.",
            location="Remote",
            is_active=True,
            employer=self.employer_user
        )

        # Inactive Job
        self.inactive_job = Job.objects.create(
            title="Archived Position",
            description="Closed job.",
            location="Remote",
            is_active=False,
            employer=self.employer_user
        )

        # Expired Job
        self.expired_job = Job.objects.create(
            title="Expired Position",
            description="Deadline has passed.",
            location="Remote",
            application_deadline=timezone.now().date() - timedelta(days=5),
            is_active=True,
            employer=self.employer_user
        )

        self.apps_url = reverse('application-list-create')

    def test_candidate_apply_using_profile_resume(self):
        self.client.force_authenticate(user=self.candidate_user)
        data = {
            "job": self.active_job.id,
            "cover_letter": "I am passionate about Django and building great products."
        }
        res = self.client.post(self.apps_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], Application.Status.PENDING)
        self.assertIsNotNone(res.data['resume'])

    def test_candidate_apply_with_custom_resume_upload(self):
        self.client.force_authenticate(user=self.candidate_user)
        custom_pdf = create_test_pdf("custom_resume.pdf")
        data = {
            "job": self.active_job.id,
            "cover_letter": "Custom application resume attached.",
            "resume": custom_pdf
        }
        res = self.client.post(self.apps_url, data, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], Application.Status.PENDING)

    def test_candidate_without_resume_rejected(self):
        self.client.force_authenticate(user=self.candidate_no_resume)
        data = {"job": self.active_job.id, "cover_letter": "No resume attached."}
        res = self.client.post(self.apps_url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume", res.data)

    def test_candidate_cannot_apply_twice_to_same_job(self):
        self.client.force_authenticate(user=self.candidate_user)
        data = {"job": self.active_job.id, "cover_letter": "First submission."}
        res1 = self.client.post(self.apps_url, data)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Second attempt must fail
        res2 = self.client.post(self.apps_url, data)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job", res2.data)

    def test_candidate_cannot_apply_to_closed_job(self):
        self.client.force_authenticate(user=self.candidate_user)
        data = {"job": self.inactive_job.id, "cover_letter": "Applying to closed job."}
        res = self.client.post(self.apps_url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job", res.data)

    def test_candidate_cannot_apply_to_expired_deadline_job(self):
        self.client.force_authenticate(user=self.candidate_user)
        data = {"job": self.expired_job.id, "cover_letter": "Applying to expired job."}
        res = self.client.post(self.apps_url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job", res.data)

    def test_employer_cannot_apply_to_job(self):
        self.client.force_authenticate(user=self.employer_user)
        data = {"job": self.active_job.id, "cover_letter": "Employer trying to apply."}
        res = self.client.post(self.apps_url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_candidate_sees_only_own_applications(self):
        # Create an application
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="My application"
        )
        self.client.force_authenticate(user=self.candidate_user)
        res = self.client.get(self.apps_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        # Verify employer_notes is not in candidate output
        self.assertNotIn("employer_notes", res.data[0])

    def test_employer_can_view_applications_for_their_job(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="Interested candidate.",
            employer_notes="Internal candidate review notes."
        )
        self.client.force_authenticate(user=self.employer_user)
        res = self.client.get(self.apps_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        # Employer can see candidate details and employer notes
        self.assertIn("candidate_details", res.data[0])
        self.assertIn("employer_notes", res.data[0])

    def test_other_employer_cannot_see_applications_for_unowned_job(self):
        Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="Application for employer 1"
        )
        self.client.force_authenticate(user=self.other_employer)
        res = self.client.get(self.apps_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_candidate_can_withdraw_application(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="My application"
        )
        self.client.force_authenticate(user=self.candidate_user)
        url = reverse('application-detail', kwargs={'pk': app.pk})
        res = self.client.patch(url, {"status": "WITHDRAWN"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.WITHDRAWN)

    def test_candidate_cannot_set_privileged_status(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="My application"
        )
        self.client.force_authenticate(user=self.candidate_user)
        url = reverse('application-detail', kwargs={'pk': app.pk})
        res = self.client.patch(url, {"status": "ACCEPTED"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employer_can_update_status_and_notes(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="Applicant"
        )
        self.client.force_authenticate(user=self.employer_user)
        url = reverse('application-status-update', kwargs={'pk': app.pk})
        res = self.client.patch(
            url,
            {"status": "INTERVIEW", "employer_notes": "Passed technical screening round 1."}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.INTERVIEW)
        self.assertEqual(app.employer_notes, "Passed technical screening round 1.")

    def test_candidate_can_delete_pending_application(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            status=Application.Status.PENDING
        )
        self.client.force_authenticate(user=self.candidate_user)
        url = reverse('application-detail', kwargs={'pk': app.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Application.objects.filter(pk=app.pk).exists())

    def test_candidate_cannot_delete_non_pending_application(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            status=Application.Status.SHORTLISTED
        )
        self.client.force_authenticate(user=self.candidate_user)
        url = reverse('application-detail', kwargs={'pk': app.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Application.objects.filter(pk=app.pk).exists())

    def test_get_job_applications_endpoint(self):
        app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.active_job,
            cover_letter="Application for active job"
        )
        url = reverse('job-applications-list', kwargs={'job_id': self.active_job.pk})

        # Owner employer can view
        self.client.force_authenticate(user=self.employer_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

        # Other employer gets 403
        self.client.force_authenticate(user=self.other_employer)
        res_other = self.client.get(url)
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

        # Candidate gets 403
        self.client.force_authenticate(user=self.candidate_user)
        res_candidate = self.client.get(url)
        self.assertEqual(res_candidate.status_code, status.HTTP_403_FORBIDDEN)
