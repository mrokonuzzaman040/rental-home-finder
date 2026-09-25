import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class UpperLowerSymbolPasswordValidator:
    """Project registration rule: 6+ chars with uppercase, lowercase, and symbol."""

    def validate(self, password, user=None):
        errors = []
        if len(password or "") < 6:
            errors.append(_("Your password must contain at least 6 characters."))
        if not re.search(r"[A-Z]", password or ""):
            errors.append(_("Your password must contain at least one uppercase letter."))
        if not re.search(r"[a-z]", password or ""):
            errors.append(_("Your password must contain at least one lowercase letter."))
        if not re.search(r"[^A-Za-z0-9]", password or ""):
            errors.append(_("Your password must contain at least one symbol."))
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _("Use at least 6 characters with uppercase, lowercase, and a symbol.")
