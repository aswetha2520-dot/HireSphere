from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User
from .models import Job


class JobManagementTests(APITestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(
            email="employer@company.com",
            password="Password123!",
            role=User.Role.EMPLOYER,
            first_name="Corp"
        )
        self.other_employer = User.objects.create_user(
            email="other@company.com",
            password="Password123!",
            role=User.Role.EMPLOYER
        )
        self.candidate_user = User.objects.create_user(
            email="candidate@jobs.com",
            password="Password123!",
            role=User.Role.CANDIDATE
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@jobs.com",
            password="Password123!"
        )

        self.jobs_url = reverse('job-list')

        # Create sample job
        self.job1 = Job.objects.create(
            title="Senior Python Backend Developer",
            description="We are looking for an experienced Django engineer.",
            responsibilities="Develop APIs, write automated tests, optimize queries.",
            required_skills="Python, Django, PostgreSQL, Docker",
            qualifications="B.S. in Computer Science or equivalent",
            employment_type=Job.EmploymentType.FULL_TIME,
            experience_level=Job.ExperienceLevel.SENIOR,
            salary_min=Decimal('100000.00'),
            salary_max=Decimal('130000.00'),
            location="San Francisco, CA",
            remote_status=Job.RemoteStatus.REMOTE,
            number_of_openings=2,
            is_active=True,
            employer=self.employer_user
        )

        self.inactive_job = Job.objects.create(
            title="Closed Internship",
            description="Old closed job description.",
            employment_type=Job.EmploymentType.INTERNSHIP,
            experience_level=Job.ExperienceLevel.ENTRY,
            location="Chicago, IL",
            is_active=False,
            employer=self.employer_user
        )

    def test_public_can_list_active_jobs(self):
        # Unauthenticated request
        res = self.client.get(self.jobs_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should include active job, but NOT inactive job
        titles = [item['title'] for item in res.data['results']]
        self.assertIn("Senior Python Backend Developer", titles)
        self.assertNotIn("Closed Internship", titles)

    def test_public_can_retrieve_active_job(self):
        url = reverse('job-detail', kwargs={'pk': self.job1.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], "Senior Python Backend Developer")

    def test_public_cannot_retrieve_inactive_job(self):
        url = reverse('job-detail', kwargs={'pk': self.inactive_job.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_candidate_cannot_create_job(self):
        self.client.force_authenticate(user=self.candidate_user)
        data = {
            "title": "Junior Developer",
            "description": "Looking for entry level devs.",
            "employment_type": "FULL_TIME",
            "experience_level": "ENTRY",
            "location": "Boston, MA"
        }
        res = self.client.post(self.jobs_url, data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employer_can_create_job(self):
        self.client.force_authenticate(user=self.employer_user)
        data = {
            "title": "DevOps Engineer",
            "description": "Kubernetes and AWS specialist.",
            "responsibilities": "Maintain cloud infrastructure.",
            "required_skills": "AWS, Terraform, Kubernetes",
            "employment_type": "FULL_TIME",
            "experience_level": "MID",
            "salary_min": "90000.00",
            "salary_max": "110000.00",
            "location": "Austin, TX",
            "remote_status": "HYBRID",
            "number_of_openings": 1,
            "is_active": True
        }
        res = self.client.post(self.jobs_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['title'], "DevOps Engineer")
        # Ensure job belongs to this employer
        created_job = Job.objects.get(title="DevOps Engineer")
        self.assertEqual(created_job.employer, self.employer_user)

    def test_employer_can_update_own_job(self):
        self.client.force_authenticate(user=self.employer_user)
        url = reverse('job-detail', kwargs={'pk': self.job1.pk})
        res = self.client.patch(url, {"title": "Lead Python Backend Developer"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], "Lead Python Backend Developer")

    def test_employer_cannot_update_other_employer_job(self):
        self.client.force_authenticate(user=self.other_employer)
        url = reverse('job-detail', kwargs={'pk': self.job1.pk})
        res = self.client.patch(url, {"title": "Hijacked Title"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employer_can_delete_own_job(self):
        self.client.force_authenticate(user=self.employer_user)
        url = reverse('job-detail', kwargs={'pk': self.job1.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(pk=self.job1.pk).exists())

    def test_admin_can_manage_any_job(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('job-detail', kwargs={'pk': self.job1.pk})
        res = self.client.patch(url, {"title": "Admin Modified Title"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], "Admin Modified Title")

    def test_job_filtering_and_search(self):
        # Search by keyword
        res = self.client.get(f"{self.jobs_url}?search=Python")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        # Filter by remote status
        res_remote = self.client.get(f"{self.jobs_url}?remote_status=REMOTE")
        self.assertEqual(res_remote.status_code, status.HTTP_200_OK)
        self.assertEqual(res_remote.data['count'], 1)

        # Filter by non-matching remote status
        res_onsite = self.client.get(f"{self.jobs_url}?remote_status=ONSITE")
        self.assertEqual(res_onsite.status_code, status.HTTP_200_OK)
        self.assertEqual(res_onsite.data['count'], 0)

        # Salary filter
        res_salary = self.client.get(f"{self.jobs_url}?min_salary=90000")
        self.assertEqual(res_salary.status_code, status.HTTP_200_OK)
        self.assertEqual(res_salary.data['count'], 1)
