from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import AdminLoginSerializer, UserSignupSerializer


def _set_auth_cookies(response, access_token, refresh_token):
	response.set_cookie(
		key="access_token",
		value=access_token,
		max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
		httponly=True,
		secure=settings.JWT_COOKIE_SECURE,
		samesite=settings.JWT_COOKIE_SAMESITE,
		path="/",
	)
	response.set_cookie(
		key="refresh_token",
		value=refresh_token,
		max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
		httponly=True,
		secure=settings.JWT_COOKIE_SECURE,
		samesite=settings.JWT_COOKIE_SAMESITE,
		path="/",
	)


def _clear_auth_cookies(response):
	response.delete_cookie("access_token", path="/", samesite=settings.JWT_COOKIE_SAMESITE)
	response.delete_cookie("refresh_token", path="/", samesite=settings.JWT_COOKIE_SAMESITE)


class SignupView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		serializer = UserSignupSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		return Response(
			{
				"id": user.id,
				"username": user.username,
				"email": user.email,
				"is_superuser": user.is_superuser,
				"is_staff": user.is_staff,
			},
			status=status.HTTP_201_CREATED,
		)


class ProfileView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, version=None):
		user = request.user
		return Response(
			{
				"id": user.id,
				"username": user.username,
				"email": user.email,
				"first_name": user.first_name,
				"last_name": user.last_name,
				"is_superuser": user.is_superuser,
				"is_staff": user.is_staff,
			}
		)


class AdminLoginView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		serializer = AdminLoginSerializer(data=request.data, context={"request": request})
		serializer.is_valid(raise_exception=True)

		user = serializer.validated_data["user"]
		refresh = RefreshToken.for_user(user)
		access = refresh.access_token

		response = Response(
			{
				"detail": "Admin login successful.",
				"user": {
					"id": user.id,
					"username": user.username,
					"email": user.email,
					"is_superuser": user.is_superuser,
					"refresh": str(refresh),
					"access": str(access),
				},
			},
			status=status.HTTP_200_OK,
		)
		_set_auth_cookies(response, str(access), str(refresh))

		return response


class UserLoginView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		username = request.data.get("username")
		password = request.data.get("password")

		if not username or not password:
			return Response({"detail": "username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

		user = authenticate(request=request, username=username, password=password)
		if not user:
			return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

		refresh = RefreshToken.for_user(user)
		access = refresh.access_token

		response = Response(
			{
				"detail": "Login successful.",
				"user": {
					"id": user.id,
					"username": user.username,
					"email": user.email,
					"is_superuser": user.is_superuser,
					"is_staff": user.is_staff,
					"refresh": str(refresh),
					"access": str(access),
				},
			},
			status=status.HTTP_200_OK,
		)
		_set_auth_cookies(response, str(access), str(refresh))
		return response


class AdminTokenRefreshView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		refresh_token = request.COOKIES.get("refresh_token")
		if not refresh_token:
			return Response({"detail": "Refresh token missing."}, status=status.HTTP_401_UNAUTHORIZED)

		try:
			refresh = RefreshToken(refresh_token)
			new_access = str(refresh.access_token)
		except TokenError:
			return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

		response = Response({"detail": "Token refreshed.",
                       "access_token": new_access,
                       },
                      status=status.HTTP_200_OK)
		
		return response


class AdminLogoutView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		refresh_token = request.COOKIES.get("refresh_token")
		if refresh_token:
			try:
				refresh = RefreshToken(refresh_token)
				refresh.blacklist()
			except AttributeError:
				# Blacklist app may not be enabled; logout should still clear client auth state.
				pass
			except TokenError:
				return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
		response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
		_clear_auth_cookies(response)
		return response


class AdminMeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, version=None):
		user = request.user
		if not user.is_superuser:
			return Response({"detail": "Admin access only."}, status=status.HTTP_403_FORBIDDEN)

		return Response(
			{
				"id": user.id,
				"username": user.username,
				"email": user.email,
				"first_name": user.first_name,
				"last_name": user.last_name,
				"is_superuser": user.is_superuser,
			},
			status=status.HTTP_200_OK,
		)


class UserLogoutView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		refresh_token = request.data.get("refresh_token") or request.COOKIES.get("refresh_token")
		if refresh_token:
			try:
				refresh = RefreshToken(refresh_token)
				refresh.blacklist()
			except AttributeError:
				# Blacklist app may not be enabled; logout should still clear client auth state.
				pass
			except TokenError:
				return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

		response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
		_clear_auth_cookies(response)
		return response

class UserRefreshTokenView(APIView):
	permission_classes = [AllowAny]

	def post(self, request, version=None):
		refresh_token = request.COOKIES.get("refresh_token") or request.data.get("refresh_token")
		if not refresh_token:
			return Response({"detail": "Refresh token missing."}, status=status.HTTP_401_UNAUTHORIZED)

		try:
			refresh = RefreshToken(refresh_token)
			new_access = str(refresh.access_token)
		except TokenError:
			return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

		response = Response({"detail": "Token refreshed."}, status=status.HTTP_200_OK)
		response.set_cookie(
			key="access_token",
			value=new_access,
			max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
			httponly=True,
			secure=settings.JWT_COOKIE_SECURE,
			samesite=settings.JWT_COOKIE_SAMESITE,
			path="/",
		)
		return response