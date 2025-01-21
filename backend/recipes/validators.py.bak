import re

from django.core.exceptions import ValidationError


def validate_username(username):
    """Проверка имени пользователя."""
    if username.lower() == 'me':
        raise ValidationError(
            "Нельзя использовать 'me' в качестве имени пользователя.")

    if not re.match(r'^[\w.@+-]+$', username):
        raise ValidationError("Не допустимое имя пользователя.")
