import urlparse
import urllib

from django import template
from django.template import Library, TemplateSyntaxError
from django.template.loader import render_to_string
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

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


class URLNextNode(template.defaulttags.URLNode):
    """Tag that works like regular url tag but includes 'next' get parameter
    when it picks it up in the request.

    """

    def __init__(self, urlnode):
        super(URLNextNode, self).__init__(
            urlnode.view_name,
            urlnode.args,
            urlnode.kwargs,
            urlnode.asvar
        )

    def render(self, context):
        url = super(URLNextNode, self).render(context)
        # attempt to get the request
        request = context.get('request')
        if request is None:
            raise RequestContextRequiredException('url_next tag')
        # check for and add next url
        next_url = request.GET.get('next')
        if next_url:
            url += '&' if '?' in url else '?'
            url += 'next=%s' % next_url
        # return the modified url
        return url

        
@register.tag
def url_next(parser, token):
    """Parser function for URLNextNode tag node."""
    urlnode = template.defaulttags.url(parser, token)
    return URLNextNode(urlnode)


class SmartURLNode(template.Node):
    """Tag that pcks up the url of an object using a callable."""

    def __init__(self, url_callable, obj, asvar):
        self.url_callable = url_callable
        self.obj = obj
        self.asvar = asvar

    def render(self, context):
        # resolve variables_
        url_callable = self.url_callable.resolve(context)
        obj = self.obj.resolve(context)
        asvar = self.asvar
        # determine the url and return or assign
        url = url_callable(obj)
        if asvar is None:
            return url
        else:
            context[asvar] = url
            return ''


@register.tag
def new_smart_url(parser, token):
    """Parser method for the SmartURLNode tag node."""
    bits = token.split_contents()
    # check for right amount of parameters
    if len(bits) < 3:
        raise TemplateSyntaxError('%r takes at least 2 arguments' % bits[0])
    # determine var name if given
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    # parse the rest of the parameters
    url_callable = parser.compile_filter(bits[1])
    obj = parser.compile_filter(bits[2])
    # build and return the node
    return SmartURLNode(url_callable, obj, asvar)


class ContentTypeNode(template.Node):
    """Tag node for retrieving content type of an object."""

    def __init__(self, obj, asvar):
        self.obj = obj
        self.asvar = asvar

    def render(self, context):
        # resolve the arguments
        obj = self.obj.resolve(context)
        # get the content type
        content_type = ContentType.objects.get_for_model(obj)
        # set variable in context
        context[self.asvar] = content_type
        return ''


@register.tag
def content_type(parser, token):
    """Parser function for building a ContentTypeNode."""
    bits = token.split_contents()
    # check for minimum amount of arguments
    if len(bits) < 4:
        raise TemplateSyntaxError('%r takes at least 1 argument and a ' \
            'variable name to be assigned to' % bits[0])
    # determine var name if given
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    # parse the rest of the arguments
    obj = parser.compile_filter(bits[1])
    # build and return the node
    return ContentTypeNode(obj, asvar)
 

@register.simple_tag
def content_object_url(view, obj):
    """Builds a url for a content object to a specified view."""
    content_type = ContentType.objects.get_for_model(obj)
    content_type = '.'.join([content_type.app_label, content_type.model])
    return reverse(view, kwargs={
        'object_id': obj.id,
        'content_type': content_type,
    })

