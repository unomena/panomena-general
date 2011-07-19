from django import forms
from django.db.models import Q
from django.forms import widgets
from django.core.validators import email_re
from django.utils.translation import ugettext_lazy as _


class CommaSeparatedInput(widgets.Textarea):
    """Comma separated input widget."""
    input_type = 'text'
    
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        elif isinstance(value, (list, tuple)):
            value = (', '.join([user.username for user in value]))
        return super(CommaSeparatedInput, self).render(name, value, attrs)


class CommaSeparatedEmailField(forms.Field):
    """Comma seperated email form field."""

    widget = CommaSeparatedInput
    
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


class CommaSeparatedLookupField(forms.Field):
    """Field for looking up an array of objects using values of
    specified model fields, determined by a method that analises
    each provided value.
    
    """

    default_error_messages = {
        'unidentified': _(u"The '%s' value could not be indentified."),
    }

    widget = CommaSeparatedInput

    def __init__(self, model, identify, *args, **kwargs):
        self.model = model
        self.identify = identify
        super(CommaSeparatedLookupField, self).__init__(*args, **kwargs)

    def clean(self, value):
        error_messages = self.error_messages
        value = super(CommaSeparatedLookupField, self).clean(value)
        # return empty list for empty field
        if not value: return []
        # build the query
        query = Q()
        values = [v.strip() for v in value.split(',')]
        # use the identify method if available
        for value in values:
            result = self.identify(value)
            if result is None:
                raise forms.ValidationError(
                    error_messages['unidentified'] % value)
            fields, value = result
            for field in fields:
                query = query | Q(**{field: value})
        # return the results
        return self.model.objects.filter(query).all()

