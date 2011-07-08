

class RequestContextRequiredException(Exception):
    """Exception that should be raised when a RequestContext is required."""

    def __init__(self, value=None):
        if value:
            value = "RequestContext required for '%s' to operate." % value
        else:
            value = "RequestContext required."
        super(RequestContextRequiredException, self).__init__(value)

