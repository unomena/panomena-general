

class RequestContextRequiredException(Exception):
    """Exception that should be raised when a RequestContext is required."""

    def __init__(self, name=None):
        if name:
            message = "RequestContext required for '%s' to operate." % name
        else:
            message = "RequestContext required."
        super(RequestContextRequiredException, self).__init__(message)

