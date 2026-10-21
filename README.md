# JobNest Backend — Complete Job Portal REST API

Welcome to **JobNest Backend**, a production-ready, modular RESTful backend built with Python, Django, and Django REST Framework (DRF). It provides complete authentication, role-based workflows for Candidates and Employers, job posting management, file uploads (PDF resumes and logos), and application tracking with full Swagger/OpenAPI documentation.

---

## 🌟 Features Overview

- **Custom User Model**: Clean email-based authentication with three roles (`CANDIDATE`, `EMPLOYER`, `ADMIN`).
- **JWT Authentication**: Simple JWT integration with access tokens, refresh token rotation, and blacklisting on logout.
- **Role-Based Profiles**:
  - **Candidate Profile**: Full name, contact info, skills, education, experience, PDF resume, and avatar.
  - **Employer Profile**: Company name, website, description, location, and company logo.
- **Job Management CRUD**:
  - Public job browsing with filtering (employment type, experience level, remote status, salary range) and full-text search.
  - Employers can create, update, and manage their own listings.
  - Inactive listings are hidden from public discovery.
- **Job Application Lifecycle**:
  - Candidates apply to open positions using their profile resume or a custom PDF upload.
  - Built-in duplicate prevention and deadline checks.
  - Status pipeline: `PENDING` ➔ `REVIEWED` ➔ `SHORTLISTED` ➔ `INTERVIEW` ➔ `ACCEPTED` / `REJECTED` / `WITHDRAWN`.
  - Confidential employer notes visible only to recruiters and administrators.
- **Secure File Uploads**: Validated PDF resumes (up to 5MB) and images (PNG, JPG, WebP up to 2MB) with collision-free filenames.
- **Comprehensive API Docs**: Interactive Swagger UI (`/api/docs/`), ReDoc (`/api/redoc/`), and OpenAPI 3.0 schema (`/api/schema/`).
- **Postman Collection Included**: Pre-configured `jobnest_postman_collection.json` ready for one-click import.
- **Flexible Database**: Zero-config SQLite for local development, ready for PostgreSQL in production via environment variables.

---

## 📂 Project Structure

```text
JobNestBackend/
├── manage.py                          # Django management script
├── requirements.txt                   # Production & development dependencies
├── .env.example                       # Template for environment variables
├── .env                               # Local environment configuration
├── .gitignore                         # Git exclusion rules
├── jobnest_postman_collection.json    # Complete Postman Collection
├── README.md                          # Documentation and beginner setup guide
│
├── config/                            # Core project settings and URL configuration
│   ├── __init__.py
│   ├── settings.py                    # DRF, Simple JWT, CORS, Database & Spectacular configs
│   ├── urls.py                        # Root URL routing & Swagger endpoints
│   ├── wsgi.py                        # WSGI entry point
│   └── asgi.py                        # ASGI entry point
│
├── accounts/                          # Custom User, Auth, and Profiles app
│   ├── __init__.py
│   ├── models.py                      # User, CandidateProfile, EmployerProfile models
│   ├── serializers.py                 # Registration, login, profile serializers
│   ├── views.py                       # Auth and profile view endpoints
│   ├── permissions.py                 # IsCandidate, IsEmployer, IsAdmin
│   ├── validators.py                  # File size, PDF, image validators & path generators
│   ├── urls_auth.py                   # /api/auth/* endpoints
│   ├── urls_profiles.py               # /api/candidates/me/ and /api/employers/me/
│   ├── admin.py                       # Django Admin customization
│   └── tests.py                       # Automated test suite for accounts & Swagger
│
├── jobs/                              # Job listings and recruitment app
│   ├── __init__.py
│   ├── models.py                      # Job model with employment types and deadlines
│   ├── serializers.py                 # JobList, JobDetail, JobCreateUpdate serializers
│   ├── views.py                       # JobViewSet with pagination & search
│   ├── filters.py                     # django-filter FilterSet for Jobs
│   ├── permissions.py                 # IsJobEmployerOrReadOnly object permissions
│   ├── urls.py                        # /api/jobs/* routes
│   ├── admin.py                       # Django Admin customization
│   └── tests.py                       # Automated test suite for jobs
│
└── applications/                      # Job applications tracking app
    ├── __init__.py
    ├── models.py                      # Application model with unique constraint
    ├── serializers.py                 # Candidate & Employer application serializers
    ├── views.py                       # Application list, detail, and status update views
    ├── permissions.py                 # Application access & update rules
    ├── urls.py                        # /api/applications/* routes
    ├── admin.py                       # Django Admin customization
    └── tests.py                       # Automated test suite for applications
```

---

## 🚀 Beginner Setup Guide for VS Code on Windows (PowerShell)

### Step 1: Open the Workspace in VS Code
1. Launch **Visual Studio Code**.
2. Go to **File** > **Open Folder...** and select the project directory (`QuickHire` or `JobNestBackend`).
3. Open a terminal by pressing ``Ctrl + ` `` or going to **Terminal** > **New Terminal**.
4. Confirm PowerShell is your active shell.

### Step 2: (Optional) Create & Activate Virtual Environment
```powershell
# Create a virtual environment named .venv
python -m venv .venv

# If PowerShell blocks script execution, run:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Environment Variables Setup
A default `.env` file is already created for local SQLite development. To review configuration options:
```powershell
# Check .env or copy from template
Copy-Item .env.example .env
```

### Step 5: Run Database Migrations
```powershell
python manage.py makemigrations accounts jobs applications
python manage.py migrate
```

### Step 6: Create an Administrator (Superuser)
```powershell
python manage.py createsuperuser
```
Follow the prompts to enter an email (e.g. `admin@jobnest.com`) and a secure password.

### Step 7: Run Automated Tests
```powershell
python manage.py test
```
All 45 automated tests will execute and verify authentication, permissions, filtering, file uploads, and endpoints.

### Step 8: Start the Local Development Server
```powershell
python manage.py runserver
```
Your backend will start running at:
- **Base API URL**: `http://127.0.0.1:8000/`
- **Swagger UI**: `http://127.0.0.1:8000/api/docs/`
- **ReDoc UI**: `http://127.0.0.1:8000/api/redoc/`
- **OpenAPI Schema**: `http://127.0.0.1:8000/api/schema/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`

---

## 📖 Complete API Reference

### 1. Authentication (`/api/auth/`)

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/api/auth/register/` | Register Candidate or Employer | Public |
| `POST` | `/api/auth/login/` | Obtain JWT Access and Refresh tokens | Public |
| `POST` | `/api/auth/token/refresh/` | Refresh expired access token | Public |
| `POST` | `/api/auth/logout/` | Blacklist refresh token & logout | Authenticated |
| `GET` | `/api/auth/me/` | Get current user account details | Authenticated |
| `PATCH`| `/api/auth/me/` | Update first/last name (no role escalation) | Authenticated |
| `POST` | `/api/auth/change-password/` | Change account password | Authenticated |

### 2. Profiles (`/api/candidates/` & `/api/employers/`)

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/candidates/me/` | Retrieve current candidate's profile | Candidate |
| `PATCH`| `/api/candidates/me/` | Update skills, education, PDF resume, picture | Candidate |
| `GET` | `/api/employers/me/` | Retrieve current employer's company profile | Employer |
| `PATCH`| `/api/employers/me/` | Update company name, website, logo | Employer |

### 3. Job Listings (`/api/jobs/`)

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/jobs/` | List active jobs (supports search & filter) | Public |
| `POST` | `/api/jobs/` | Create a new job listing | Employer / Admin |
| `GET` | `/api/jobs/<id>/` | View job details | Public (Active) / Owner |
| `PUT` | `/api/jobs/<id>/` | Update entire job listing | Job Employer / Admin |
| `PATCH`| `/api/jobs/<id>/` | Partially update job listing | Job Employer / Admin |
| `DELETE`| `/api/jobs/<id>/` | Delete job listing | Job Employer / Admin |
| `GET` | `/api/jobs/<job_id>/applications/` | List all applications for a specific job | Job Employer / Admin |

#### Query Parameters for `GET /api/jobs/`:
- `?search=python`: Searches titles, descriptions, required skills, locations, and company names.
- `?employment_type=FULL_TIME`: Options: `FULL_TIME`, `PART_TIME`, `CONTRACT`, `INTERNSHIP`, `FREELANCE`.
- `?experience_level=SENIOR`: Options: `ENTRY`, `MID`, `SENIOR`, `LEAD`, `EXECUTIVE`.
- `?remote_status=REMOTE`: Options: `ONSITE`, `HYBRID`, `REMOTE`.
- `?min_salary=90000` & `?max_salary=150000`: Salary range filtering.
- `?ordering=-created_at`: Order by `created_at`, `application_deadline`, `salary_min`, `salary_max`.
- `?my_jobs=true`: For logged-in employers to view all jobs they posted.

### 4. Job Applications (`/api/applications/`)

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/applications/` | List applications (Candidates see own; Employers see for their jobs) | Authenticated |
| `POST` | `/api/applications/` | Apply to an active job with PDF resume | Candidate |
| `GET` | `/api/applications/<id>/` | View application details | Applicant / Employer |
| `PATCH`| `/api/applications/<id>/` | Update application (Candidate withdraws; Employer updates status/notes) | Applicant / Employer |
| `DELETE`| `/api/applications/<id>/` | Cancel pending application | Candidate (Pending) / Admin |
| `PATCH`| `/api/applications/<id>/status/` | Update status & employer notes | Job Employer / Admin |

---

## 💡 Step-by-Step API Testing Walkthrough

### Step A: Register an Employer & Create a Job
1. **Register Employer**:
   - `POST http://127.0.0.1:8000/api/auth/register/`
   ```json
   {
     "email": "recruiter@techcorp.com",
     "password": "Password123!",
     "password_confirm": "Password123!",
     "role": "EMPLOYER",
     "first_name": "Sarah",
     "last_name": "Connor",
     "company_name": "TechCorp Solutions"
   }
   ```
   *Copy the `access` token from the response!*

2. **Create a Job**:
   - `POST http://127.0.0.1:8000/api/jobs/`
   - Header: `Authorization: Bearer <EMPLOYER_ACCESS_TOKEN>`
   ```json
   {
     "title": "Senior Python Backend Engineer",
     "description": "Lead development of high-throughput REST APIs.",
     "responsibilities": "Design microservices, write clean code and tests.",
     "required_skills": "Python, Django, PostgreSQL, Docker",
     "qualifications": "3+ years professional experience",
     "employment_type": "FULL_TIME",
     "experience_level": "SENIOR",
     "salary_min": "100000.00",
     "salary_max": "130000.00",
     "location": "Remote",
     "remote_status": "REMOTE",
     "number_of_openings": 2,
     "application_deadline": "2026-12-31",
     "is_active": true
   }
   ```
   *Note the `id` of the created job (e.g. `1`).*

---

### Step B: Register a Candidate & Submit an Application
1. **Register Candidate**:
   - `POST http://127.0.0.1:8000/api/auth/register/`
   ```json
   {
     "email": "alex.dev@gmail.com",
     "password": "Password123!",
     "password_confirm": "Password123!",
     "role": "CANDIDATE",
     "first_name": "Alex",
     "last_name": "Johnson",
     "full_name": "Alex Johnson"
   }
   ```
   *Copy the `access` token for the candidate.*

2. **Upload Resume to Candidate Profile**:
   - `PATCH http://127.0.0.1:8000/api/candidates/me/`
   - Header: `Authorization: Bearer <CANDIDATE_ACCESS_TOKEN>`
   - Body format: `multipart/form-data`
   - Fields:
     - `skills`: `Python, Django, Docker, PostgreSQL`
     - `resume`: Attach a valid `.pdf` file

3. **Apply for the Job**:
   - `POST http://127.0.0.1:8000/api/applications/`
   - Header: `Authorization: Bearer <CANDIDATE_ACCESS_TOKEN>`
   ```json
   {
     "job": 1,
     "cover_letter": "I have 4 years of Django backend experience and would love to contribute to TechCorp."
   }
   ```
   *The system automatically attaches the candidate's profile resume!*

---

### Step C: Review & Update Application Status (Employer)
1. **View Applications for the Job**:
   - `GET http://127.0.0.1:8000/api/jobs/1/applications/`
   - Header: `Authorization: Bearer <EMPLOYER_ACCESS_TOKEN>`
   - The employer receives candidate details, contact info, resume download link, and cover letter.

2. **Move Candidate to Interview Stage**:
   - `PATCH http://127.0.0.1:8000/api/applications/1/status/`
   - Header: `Authorization: Bearer <EMPLOYER_ACCESS_TOKEN>`
   ```json
   {
     "status": "INTERVIEW",
     "employer_notes": "Impressive background in Django and unit testing. Sent invite for technical interview."
   }
   ```

---

## 🔒 Production Architecture & Security Best Practices

1. **PostgreSQL Configuration**:
   Set `DB_ENGINE=postgresql` in your environment variables and provide:
   ```env
   DB_ENGINE=postgresql
   DB_NAME=jobnest_production
   DB_USER=jobnest_user
   DB_PASSWORD=your_strong_password
   DB_HOST=db.example.com
   DB_PORT=5432
   ```

2. **Secure Private File Storage (Resumes)**:
   In production, uploaded candidate resumes should not be placed in public static buckets. Instead:
   - Use **Amazon S3** or **Google Cloud Storage** with private bucket policies.
   - Serve resumes through **time-limited pre-signed URLs** (e.g., using `boto3` or `django-storages`).
   - Restrict download access exclusively to verified recruiters who own the corresponding job posting.

3. **HTTPS & Security Headers**:
   - Set `DEBUG=False` in `.env`.
   - Configure `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, and `CSRF_COOKIE_SECURE = True`.
   - Restrict `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` to trusted domains.
