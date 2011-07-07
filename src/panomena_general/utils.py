import re
import json
import random
import functools

from django import template
from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect


def generate_filename(extention=None):
    """Generates a random filename."""
    elements = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456890'
    name = ''.join([random.choice(elements) for n in range(8)])
    if extention: return '%s.%s' % (name, extention)
    else: return name


def is_ajax_request(request):
    """Determines if a request was an AJAX request."""
    return request.META.get('HTTP_X_REQUESTED_WITH', '') == 'XMLHttpRequest'


def json_response(data):
    """Build a response object for json data."""
    return HttpResponse(
        json.dumps(data),
        mimetype='application/json'
    )


def ajax_redirect(request, url):
    """Redirects via a json response if ajax was used in the request."""
    ajax = is_ajax_request(request)
    if ajax: response = json_redirect(url)
    else: response = redirect(url)
    return response


class SettingsFetcher(object):
    """Retrieves settings from project settings throwing uniform errors
    for the application.
        
    """

    def __init__(self, app_name):
        self.app_name = app_name

    def __getattr__(self, name):
        setting = getattr(settings, name, None)
        if setting is None:
            raise ImproperlyConfigured('The %s setting is required for the %s ' \
                'application to function.' % (name, self.app_name))
        else:
            return setting
            

def get_setting(name, component_name, message=None):
    """Retrieve a setting from application settings and return a message 
    of failure if not defined.
    
    """
    setting = getattr(settings, name, None)
    if setting is None:
        if message: raise ImproperlyConfigured(message)
        raise ImproperlyConfigured('The %s setting is required for the %s ' \
            'application to function.' % (name, component_name))
    return setting


def class_from_string(path):
    """Returns a class from a path string to the class."""
    path = path.split('.')
    imp = __import__('.'.join(path[:-1]), globals(), locals(), path[-1:])
    return getattr(imp, path[-1])


def json_redirect(url):
    """Creates an http response containing json with a redirect url."""
    response = {'redirect': url}
    return HttpResponse(
        json.dumps(response),
        mimetype='application/json'
    )


def parse_kw_args(tagname, bits, args_spec=None, restrict=False):
    """ keywords arguments parser for template tags

    returns a list of (argname, value) tuples
    (NB: keeps ordering and is easily turned into a dict).

    Params:
    * tagname : the name of calling tag (for error messages)
    * bits : sequence of tokens to parse as kw args
    * args_spec : (optional) dict of argname=>validator for kwargs, cf below
    * restrict : if True, only argnames in args_specs will be accepted

    If restrict=False and args_spec is None (default), this will just try
    to parse a sequence of key=val strings into a 

    About args_spec validators :
    * A validator can be either a callable, a regular expression or None.

    * If it's a callable, the callable must take the value as argument and
    return a (possibly different) value, which will become the final value
    for the argument. Any exception raised by the validator will be
    considered a rejection.

    * If it's a regexp, the value will be matched against it. A failure
    will be considered as a rejection.

    * Using None as validator only makes sense with the restrict flag set
    to True. This is useful when the only validation is on the argument
    name being expected.
    """
    
    args = []

    if restrict:
        if args_spec is None:
            raise ValueError("you must pass an args_spec dict if you want to restrict allowed args")        
        allowed = list(args_spec.keys())
        do_validate = True
    else:
        do_validate = args_spec is not None
        
    for bit in bits:
        try:
            name, val = bit.split('=')
        except ValueError:
            raise template.TemplateSyntaxError(
                "keyword arguments to '%s' tag must have 'key=value' form (got : '%s')" \
                % (tagname, bit)
                )
        
        name = str(name)        
        if do_validate:
            if restrict:
                if name in allowed:
                    # we only want each name once
                    del allowed[allowed.index(name)]
                else:
                    raise template.TemplateSyntaxError(
                        "keyword arguments to '%s' tag must be one of % (got : '%s')" \
                        % (tagname, ",".join(allowed), name)
                        )

                validate = args_spec[name]
            else: 
                validate = args_spec.get(name, None)
                
            if validate is not None:
                if callable(validate):
                    try:
                        val = validate(val)
                    except Exception, e:
                        raise template.TemplateSyntaxError(
                            "invalid optional argument '%s' for '%s' tag: '%s' (%s)" \
                            % (tagname, name, val, e)
                            )
                else:
                    # assume re
                    if re.match(validate, val) is None:
                        raise template.TemplateSyntaxError(
                            "invalid optional argument '%s' for '%s' tag: '%s' (doesn't match '%s')" \
                            % (tagname, name, val, validate)
                        )
                    
        # should be ok if we managed to get here        
        args.append((name, val))
    
    return args


def formfield_extractor(model, extra_config):
    """Extracts form fields from a model and applies extra config as
    specified for each field.
    
    """
    fields = {}
    for field in model._meta.fields:
        config = extra_config.get(field.name, {})
        fields[field.name] = functools.partial(field.formfield, **config)
    return fields
