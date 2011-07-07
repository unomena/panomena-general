import urlparse
import urllib

from django import template
from django.template import Library, TemplateSyntaxError
from django.template.loader import render_to_string
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse

from panomena_general.exceptions import RequestContextRequiredException


register = Library()


class PagingNode(template.Node):
    """Tag node for rendering a pagination control using the template
    indicated and supplying only the list of objects, request key and
    the size of the pages.

    """

    def __init__(self, objects, key, size):
        self.objects = objects
        self.key = key
        self.size = size

    def render(self, context):
        # resolve variables
        objects = self.objects.resolve(context)
        key = self.key.resolve(context)
        size = self.size.resolve(context)
        # get the request
        request = context.get('request')
        if request is None:
            raise RequestContextRequiredException('paging tag')
        # get the page number
        try: page = int(request.GET.get(key, '1'))
        except ValueError: page = 1
        # create the paginator
        paginator = Paginator(objects, size)
        # set the page
        try:
            page = paginator.page(page)
        except (EmptyPage, InvalidPage):
            page = paginator.page(paginator.num_pages)
        context[key] = page
        # return nothing to render
        return ''


@register.tag
def paging(parser, token):
    """Parser for the PagingNode tag node."""
    bits = token.split_contents()
    if len(bits) < 4:
        raise TemplateSyntaxError('%r takes at least 3 arguments' % bits[0])
    objects = parser.compile_filter(bits[1])
    key = parser.compile_filter(bits[2])
    size = parser.compile_filter(bits[3])
    return PagingNode(objects, key, size)


class PagingRenderNode(template.Node):
    """Tag node for rendering paging controls."""

    def __init__(self, page, key, label, template, url):
        self.page = page
        self.label = label
        self.key = key
        self.template = template
        self.url = url

    def render(self, context):
        # resolve variables
        page = self.page.resolve(context)
        key = self.key.resolve(context)
        label = self.label.resolve(context)
        template = self.template.resolve(context)
        url = self.url.resolve(context)
        # get the request
        request = context.get('request')
        if request is None:
            raise RequestContextRequiredException('paging tag')
        # determine the url
        if not url:
            url = context['request'].get_full_path()
        # parse the url and query string
        url = urlparse.urlparse(url)
        qs = dict(urlparse.parse_qsl(url.query))
        # remove the key from the query string
        qs.pop(key, None)
        url = url._replace(query=urllib.urlencode(qs))
        url = urlparse.urlunparse(url)
        # add the neccecary to the url
        url += '?' if len(qs) == 0 else '&' 
        # render the template if supplied
        return render_to_string(template, {
            'page': page,
            'label': label,
            'key': key,
            'url': url
        })


@register.tag
def paging_render(parser, token):
    """Parser for the PagingRenderNode tag node."""
    bits = token.split_contents()
    if len(bits) < 5:
        raise TemplateSyntaxError('%r takes at least 4 arguments' % bits[0])
    page = parser.compile_filter(bits[1])
    key = parser.compile_filter(bits[2])
    label = parser.compile_filter(bits[3])
    template = parser.compile_filter(bits[4])
    url = parser.compile_filter(bits[5] if len(bits) > 5 else '')
    return PagingRenderNode(page, key, label, template, url)


class IfHereNode(template.Node):
    """Tag node for rendering content if the current path starts
    with the url to the specified view.
    
    """
    def __init__(self, view, args, nodelist):
        self.view = view
        self.args = args
        self.nodelist = nodelist

    def render(self, context):
        args = [arg.resolve(context) for arg in self.args]
        path = context['request'].path
        if path.startswith(reverse(self.view, args=args)):
            return self.nodelist.render(context)
        else:
            return ''


@register.tag
def ifhere(parser, token):
    """Tag function for IfHereNode."""
    bits = token.split_contents()
    tag_name = bits[0]
    if len(bits) < 2:
        raise TemplateSyntaxError, "%s requires at least a single argument" % tag_name
    view_name = bits[1]
    args = [parser.compile_filter(bit) for bit in bits[2:]]
    nodelist = parser.parse(('endifhere',))
    parser.delete_first_token()
    return IfHereNode(view_name, args, nodelist)


@register.simple_tag
def verbose_name_plural(obj):
    """Returns the plural verbose name of the object."""
    # change to leaf class for model base objects
    if hasattr(obj, 'as_leaf_class'):
        obj = obj.as_leaf_class()
    # return the name
    return obj._meta.verbose_name_plural.title()

