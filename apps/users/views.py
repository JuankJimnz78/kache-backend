from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.db import IntegrityError

from .models import BusquedaReciente
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserSerializer,
    UserRequestSerializer,
    BusquedaRecienteSerializer,
)

User = get_user_model()


# ══════════════════════════════════════════════════════════════
#  AUTH VIEWS
# ══════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if user is None or not user.is_active:
        return Response(
            {"detail": "Credenciales inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        user = serializer.save()
    except IntegrityError:
        return Response(
            {"detail": "Ese usuario o correo ya está en uso."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        token = RefreshToken(request.data.get("refresh", ""))
        token.blacklist()
    except Exception:
        pass
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([AllowAny])
def token_refresh_view(request):
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"detail": "Refresh token requerido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        token = RefreshToken(refresh_token)
        data = {"access": str(token.access_token)}
        # Con ROTATE_REFRESH_TOKENS=True
        if hasattr(token, "access_token"):
            new_refresh = str(token)
            data["refresh"] = new_refresh
        return Response(data)
    except Exception:
        return Response(
            {"detail": "Token inválido o expirado."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    try:
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        send_mail(
            subject="Restablecer contraseña - ShopApp",
            message=f"Usa estos datos para restablecer tu contraseña:\n\nUID: {uid}\nToken: {token}\n\nSi no solicitaste esto, ignora este correo.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except User.DoesNotExist:
        pass  # No revelar si el email existe
    return Response({"detail": "Si el correo está registrado, recibirás un enlace."})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    user.set_password(serializer.validated_data["new_password"])
    user.save()
    return Response({"detail": "Contraseña restablecida correctamente."})


# ══════════════════════════════════════════════════════════════
#  USER CRUD VIEWS (admin)
# ══════════════════════════════════════════════════════════════

class UserListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer

    def get_queryset(self):
        qs = User.objects.all()
        search = self.request.query_params.get("search")
        is_staff = self.request.query_params.get("is_staff")
        is_active = self.request.query_params.get("is_active")

        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        if is_staff is not None:
            qs = qs.filter(is_staff=is_staff.lower() == "true")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserRequestSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = UserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserRequestSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = UserRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def toggle_active_view(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    user.is_active = not user.is_active
    user.save()
    return Response({
        "message": f"Usuario {'activado' if user.is_active else 'desactivado'}.",
        "is_active": user.is_active,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def user_stats_view(request):
    total = User.objects.count()
    active = User.objects.filter(is_active=True).count()
    inactive = User.objects.filter(is_active=False).count()
    staff = User.objects.filter(is_staff=True).count()
    return Response({
        "total": total,
        "active": active,
        "inactive": inactive,
        "staff": staff,
    })


# ══════════════════════════════════════════════════════════════
#  BÚSQUEDAS RECIENTES
# ══════════════════════════════════════════════════════════════

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def busquedas_recientes_view(request):
    if request.method == "GET":
        busquedas = BusquedaReciente.objects.filter(usuario=request.user)[:20]
        return Response(BusquedaRecienteSerializer(busquedas, many=True).data)

    serializer = BusquedaRecienteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(usuario=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def limpiar_busquedas_view(request):
    BusquedaReciente.objects.filter(usuario=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
