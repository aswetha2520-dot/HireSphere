from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, CandidateProfile, EmployerProfile
from .serializers import (
    UserRegistrationSerializer,
    LoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    CandidateProfileSerializer,
    EmployerProfileSerializer,
)
from .permissions import IsCandidate, IsEmployer


class RegisterView(APIView):
    """
    Register a new Candidate or Employer user account.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(
        summary="Register user account",
        description="Creates a new Candidate or Employer user account and issues JWT tokens upon success.",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description="User successfully registered with tokens."),
            400: OpenApiResponse(description="Validation error (e.g., email already exists or passwords mismatch).")
        },
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            return Response(
                {
                    "message": "Account registered successfully.",
                    "user": user_data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    }
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Authenticate user and obtain JWT access and refresh tokens.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(
        summary="User login",
        description="Validates credentials and returns JWT access and refresh tokens along with user information.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful with tokens returned."),
            400: OpenApiResponse(description="Invalid email or password.")
        },
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            return Response(
                {
                    "message": "Login successful.",
                    "user": UserSerializer(user).data,
                    "tokens": {
                        "access": serializer.validated_data['access'],
                        "refresh": serializer.validated_data['refresh'],
                    }
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Blacklist the provided refresh token to log out the user.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="User logout",
        description="Blacklists the provided refresh token to prevent further token renewal.",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Token blacklisted successfully. User logged out."),
            400: OpenApiResponse(description="Invalid or missing refresh token.")
        },
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Successfully logged out. Refresh token has been revoked."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """
    Retrieve or update the currently authenticated user's account details.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get current user details",
        description="Returns details of the currently authenticated user.",
        responses={200: UserSerializer},
        tags=["Authentication"]
    )
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update current user details",
        description="Updates basic profile info (first name, last name). Role, email, and admin status cannot be modified here.",
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
        tags=["Authentication"]
    )
    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    Change password for the currently authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Change user password",
        description="Verifies the current password and sets a new password.",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully."),
            400: OpenApiResponse(description="Password validation error or incorrect current password.")
        },
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateProfileView(APIView):
    """
    Retrieve or update the Candidate profile for the current candidate user.
    Supports multipart/form-data for resume and profile photo uploads.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        profile, _ = CandidateProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'full_name': self.request.user.full_name}
        )
        return profile

    @extend_schema(
        summary="Get candidate profile",
        description="Retrieves the detailed profile for the authenticated candidate user.",
        responses={200: CandidateProfileSerializer},
        tags=["Candidate Profile"]
    )
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = CandidateProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update candidate profile",
        description="Updates candidate details, including skills, education, experience, PDF resume, and profile photo.",
        request=CandidateProfileSerializer,
        responses={200: CandidateProfileSerializer},
        tags=["Candidate Profile"]
    )
    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = CandidateProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployerProfileView(APIView):
    """
    Retrieve or update the Employer profile for the current employer user.
    Supports multipart/form-data for company logo upload.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        profile, _ = EmployerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'company_name': f"{self.request.user.first_name}'s Organization" if self.request.user.first_name else "Organization"}
        )
        return profile

    @extend_schema(
        summary="Get employer profile",
        description="Retrieves company profile information for the authenticated employer user.",
        responses={200: EmployerProfileSerializer},
        tags=["Employer Profile"]
    )
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = EmployerProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update employer profile",
        description="Updates company details, website, description, and company logo.",
        request=EmployerProfileSerializer,
        responses={200: EmployerProfileSerializer},
        tags=["Employer Profile"]
    )
    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = EmployerProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
