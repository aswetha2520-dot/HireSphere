from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, CandidateProfile, EmployerProfile
from .validators import validate_resume_file, validate_image_file


class UserSerializer(serializers.ModelSerializer):
    """
    Public representation of the User model.
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
        ]
        read_only_fields = [
            'id',
            'email',
            'role',
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating personal details without modifying role or privileges.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new Candidate or Employer.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='At least 8 characters long.'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Must match password exactly.'
    )
    role = serializers.ChoiceField(
        choices=[User.Role.CANDIDATE, User.Role.EMPLOYER],
        default=User.Role.CANDIDATE,
        help_text='Account role: CANDIDATE or EMPLOYER. (ADMIN registration is restricted).'
    )
    # Optional profile initializers
    company_name = serializers.CharField(required=False, write_only=True, allow_blank=True)
    full_name = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'password',
            'password_confirm',
            'company_name',
            'full_name',
        ]
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_email(self, value):
        normalized_email = value.lower().strip()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized_email

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # Validate password strength against Django configured validators
        user_temp = User(
            email=attrs.get('email'),
            first_name=attrs.get('first_name', ''),
            last_name=attrs.get('last_name', '')
        )
        validate_password(attrs.get('password'), user=user_temp)

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        company_name = validated_data.pop('company_name', '').strip()
        full_name = validated_data.pop('full_name', '').strip()

        password = validated_data.pop('password')
        role = validated_data.get('role', User.Role.CANDIDATE)

        # Force email normalization
        validated_data['email'] = validated_data['email'].lower().strip()

        user = User.objects.create_user(password=password, **validated_data)

        # Update initialized profile with custom initial fields if supplied
        if role == User.Role.EMPLOYER and company_name:
            EmployerProfile.objects.filter(user=user).update(company_name=company_name)
        elif role == User.Role.CANDIDATE and full_name:
            CandidateProfile.objects.filter(user=user).update(full_name=full_name)

        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for authenticating users and issuing JWT tokens.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        user = authenticate(username=email, password=password)
        if not user:
            # Check if user exists to provide helpful error without security breach
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Please contact support.")

        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError({"new_password_confirm": "New passwords do not match."})

        user = self.context['request'].user
        validate_password(attrs.get('new_password'), user=user)

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """
    Serializer to blacklist refresh tokens upon logout.
    """
    refresh = serializers.CharField(required=True, help_text="The refresh token to invalidate.")

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception as e:
            raise serializers.ValidationError({"refresh": f"Invalid or expired token: {str(e)}"})


class CandidateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating Candidate Profiles.
    """
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = CandidateProfile
        fields = [
            'id',
            'user_id',
            'email',
            'full_name',
            'phone_number',
            'location',
            'skills',
            'education',
            'experience',
            'resume',
            'profile_picture',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'email', 'created_at', 'updated_at']

    def validate_resume(self, value):
        if value:
            validate_resume_file(value)
        return value

    def validate_profile_picture(self, value):
        if value:
            validate_image_file(value)
        return value


class EmployerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating Employer Profiles.
    """
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = EmployerProfile
        fields = [
            'id',
            'user_id',
            'email',
            'company_name',
            'company_description',
            'website',
            'company_location',
            'company_logo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'email', 'created_at', 'updated_at']

    def validate_company_logo(self, value):
        if value:
            validate_image_file(value)
        return value
