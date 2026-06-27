from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from .serializers import SendNotificationSerializer

User = get_user_model()


@api_view(["POST"])
@permission_classes([IsAdminUser])
def send_notification_view(request):
    """
    Envía un correo electrónico vía Gmail SMTP.

    - Con user_id: envía solo a ese usuario.
    - Sin user_id: envía a todos los usuarios activos no-staff.

    Respuesta: { "detail": "...", "sent": N, "failed": M }
    """
    serializer = SendNotificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    subject = serializer.validated_data["subject"]
    message = serializer.validated_data["message"]
    user_id = serializer.validated_data.get("user_id")

    if user_id:
        try:
            user = User.objects.get(pk=user_id)
            recipients = [user.email]
        except User.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado.", "sent": 0, "failed": 0},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        recipients = list(
            User.objects.filter(is_active=True, is_staff=False)
            .exclude(email="")
            .values_list("email", flat=True)
        )

    if not recipients:
        return Response({
            "detail": "No hay destinatarios.",
            "sent": 0,
            "failed": 0,
        })

    sent = 0
    failed = 0

    for email in recipients:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            sent += 1
        except Exception:
            failed += 1

    return Response({
        "detail": f"Enviado a {sent} usuario(s)" + (f", {failed} fallido(s)" if failed else ""),
        "sent": sent,
        "failed": failed,
    })
