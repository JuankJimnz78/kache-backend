from rest_framework.permissions import BasePermission


class EsAdmin(BasePermission):
    """
    Solo usuarios con rol ADMIN (o superusuarios de Django) pueden pasar.
    Se usa para operaciones estructurales: comercios, sucursales, categorías.
    """

    message = "Solo un administrador puede realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.is_superuser or getattr(user, "rol", None) == "ADMIN"


class EsAdminUOperador(BasePermission):
    """
    Usuarios con rol ADMIN u OPERADOR pueden pasar.
    Se usa para operaciones de carga diaria: productos y precios.
    """

    message = "Necesitas rol de administrador u operador para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return (
            user.is_superuser
            or getattr(user, "rol", None) in ("ADMIN", "OPERADOR")
        )
