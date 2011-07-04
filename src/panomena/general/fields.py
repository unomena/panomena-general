from django import forms
from django.forms import widgets
from django.core.validators import email_re
from django.utils.translation import ugettext_lazy as _


class CommaSeparatedEmailInput(widgets.Textarea):
    """Comma separated email input widget."""
    input_type = 'text'
    
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        elif isinstance(value, (list, tuple)):
            value = (', '.join([user.username for user in value]))
        return super(CommaSeparatedEmailInput, self).render(name, value, attrs)


class CommaSeparatedEmailField(forms.Field):
    """Comman seperated email form field."""

    widget = CommaSeparatedEmailInput
    
    def clean(self, value):
        value = super(CommaSeparatedEmailField, self).clean(value)
        # return blank for empty field
        if not value: return ''
        # return value if already a list
        if isinstance(value, (list, tuple)):
            return value
        # separate addresses and validate each one
        invalid = []
        emails = set([v.strip() for v in value.split(',')])
        for email in emails:
            match = email_re.match(email)
            if match is None:
                invalid.append(email)
        # raise validation error if any address has failed
        if len(invalid) > 0:
            raise forms.ValidationError(
                _("The following addresses are incorrect: %s" \
                % ', '.join(invalid)))
        return emails

