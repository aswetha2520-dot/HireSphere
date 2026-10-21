import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, CandidateProfile, EmployerProfile


def create_test_image(filename="test.png"):
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='blue')
    image.save(file, 'png')
    file.seek(0)
    return SimpleUploadedFile(filename, file.read(), content_type='image/png')


def create_test_pdf(filename="resume.pdf", content=b"%PDF-1.4 test resume content"):
    return SimpleUploadedFile(filename, content, content_type='application/pdf')


class AuthenticationAndUserTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.refresh_url = reverse('token-refresh')
        self.logout_url = reverse('auth-logout')
        self.me_url = reverse('auth-me')
        self.change_password_url = reverse('auth-change-password')

    def test_candidate_registration_success(self):
        data = {
            "email": "candidate1@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "role": "CANDIDATE",
            "first_name": "Jane",
            "last_name": "Doe",
            "full_name": "Jane Doe",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertEqual(response.data["user"]["email"], "candidate1@example.com")
        self.assertEqual(response.data["user"]["role"], "CANDIDATE")

        # Verify candidate profile was automatically created
        user = User.objects.get(email="candidate1@example.com")
        self.assertTrue(hasattr(user, 'candidate_profile'))
        self.assertEqual(user.candidate_profile.full_name, "Jane Doe")

    def test_employer_registration_success(self):
        data = {
            "email": "employer1@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "role": "EMPLOYER",
            "first_name": "John",
            "last_name": "Smith",
            "company_name": "Acme Corp",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], "EMPLOYER")

        # Verify employer profile was created with company name
        user = User.objects.get(email="employer1@example.com")
        self.assertTrue(hasattr(user, 'employer_profile'))
        self.assertEqual(user.employer_profile.company_name, "Acme Corp")

    def test_registration_duplicate_email_fails(self):
        User.objects.create_user(email="test@example.com", password="Password123!")
        data = {
            "email": "test@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "role": "CANDIDATE",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_password_mismatch_fails(self):
        data = {
            "email": "mismatch@example.com",
            "password": "Password123!",
            "password_confirm": "DifferentPassword123!",
            "role": "CANDIDATE",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_registration_prevents_admin_role_escalation(self):
        data = {
            "email": "hacker@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "role": "ADMIN",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success_and_jwt_tokens(self):
        User.objects.create_user(email="user@example.com", password="SecurePassword123!")
        data = {"email": "user@example.com", "password": "SecurePassword123!"}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    def test_login_invalid_credentials_fails(self):
        User.objects.create_user(email="user@example.com", password="SecurePassword123!")
        data = {"email": "user@example.com", "password": "WrongPassword!"}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh(self):
        user = User.objects.create_user(email="user@example.com", password="SecurePassword123!")
        login_res = self.client.post(self.login_url, {"email": "user@example.com", "password": "SecurePassword123!"})
        refresh_token = login_res.data["tokens"]["refresh"]

        refresh_res = self.client.post(self.refresh_url, {"refresh": refresh_token})
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_logout_and_token_blacklist(self):
        user = User.objects.create_user(email="user@example.com", password="SecurePassword123!")
        login_res = self.client.post(self.login_url, {"email": "user@example.com", "password": "SecurePassword123!"})
        access_token = login_res.data["tokens"]["access"]
        refresh_token = login_res.data["tokens"]["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_res = self.client.post(self.logout_url, {"refresh": refresh_token})
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Attempting to use the blacklisted refresh token should fail
        refresh_res = self.client.post(self.refresh_url, {"refresh": refresh_token})
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_and_patch_me(self):
        user = User.objects.create_user(email="me@example.com", password="Password123!", first_name="OldFirst")
        self.client.force_authenticate(user=user)

        # GET /api/auth/me/
        get_res = self.client.get(self.me_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["email"], "me@example.com")

        # PATCH /api/auth/me/
        patch_res = self.client.patch(self.me_url, {"first_name": "NewFirst", "role": "ADMIN", "is_staff": True})
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["first_name"], "NewFirst")
        # Ensure role and staff privileges were not escalated
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.CANDIDATE)
        self.assertFalse(user.is_staff)

    def test_change_password(self):
        user = User.objects.create_user(email="change@example.com", password="OldPassword123!")
        self.client.force_authenticate(user=user)

        data = {
            "old_password": "OldPassword123!",
            "new_password": "NewStrongPassword456!",
            "new_password_confirm": "NewStrongPassword456!",
        }
        res = self.client.post(self.change_password_url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify old password no longer works
        self.client.logout()
        login_old = self.client.post(self.login_url, {"email": "change@example.com", "password": "OldPassword123!"})
        self.assertEqual(login_old.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify new password works
        login_new = self.client.post(self.login_url, {"email": "change@example.com", "password": "NewStrongPassword456!"})
        self.assertEqual(login_new.status_code, status.HTTP_200_OK)


class ProfileManagementTests(APITestCase):
    def setUp(self):
        self.candidate_user = User.objects.create_user(
            email="candidate@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE
        )
        self.employer_user = User.objects.create_user(
            email="employer@example.com",
            password="Password123!",
            role=User.Role.EMPLOYER
        )
        self.candidate_me_url = reverse('candidate-profile-me')
        self.employer_me_url = reverse('employer-profile-me')

    def test_candidate_profile_get_and_update(self):
        self.client.force_authenticate(user=self.candidate_user)
        res = self.client.get(self.candidate_me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        pdf_file = create_test_pdf()
        image_file = create_test_image()

        patch_res = self.client.patch(
            self.candidate_me_url,
            {
                "full_name": "Updated Name",
                "skills": "Python, Django, React",
                "location": "New York, NY",
                "resume": pdf_file,
                "profile_picture": image_file,
            },
            format='multipart'
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["full_name"], "Updated Name")
        self.assertEqual(patch_res.data["skills"], "Python, Django, React")
        self.assertIsNotNone(patch_res.data["resume"])
        self.assertIsNotNone(patch_res.data["profile_picture"])

    def test_employer_cannot_access_candidate_profile(self):
        self.client.force_authenticate(user=self.employer_user)
        res = self.client.get(self.candidate_me_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employer_profile_get_and_update(self):
        self.client.force_authenticate(user=self.employer_user)
        res = self.client.get(self.employer_me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        logo_file = create_test_image("logo.png")
        patch_res = self.client.patch(
            self.employer_me_url,
            {
                "company_name": "Globex Corporation",
                "website": "https://globex.example.com",
                "company_location": "Berlin, Germany",
                "company_logo": logo_file,
            },
            format='multipart'
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["company_name"], "Globex Corporation")
        self.assertIsNotNone(patch_res.data["company_logo"])

    def test_candidate_cannot_access_employer_profile(self):
        self.client.force_authenticate(user=self.candidate_user)
        res = self.client.get(self.employer_me_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_resume_non_pdf_rejection(self):
        self.client.force_authenticate(user=self.candidate_user)
        fake_file = SimpleUploadedFile("resume.txt", b"Plain text file", content_type="text/plain")
        res = self.client.patch(
            self.candidate_me_url,
            {"resume": fake_file},
            format='multipart'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume", res.data)


class SwaggerDocumentationTests(APITestCase):
    def test_schema_endpoint(self):
        res = self.client.get(reverse('schema'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_swagger_ui_endpoint(self):
        res = self.client.get(reverse('swagger-ui'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_redoc_endpoint(self):
        res = self.client.get(reverse('redoc'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

