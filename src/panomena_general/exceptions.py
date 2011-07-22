

class RequestContextRequiredException(Exception):
    """Exception that should be raised when a RequestContext is required."""

    def __init__(self, value=None):
        if value:
            value = "RequestContext required for '%s' to operate." % value
        else:
            value = "RequestContext required."
        super(RequestContextRequiredException, self).__init__(value)


class ProfileRequiredException(Exception):
    """Exception raised when no profile was found for a user object."""

    def __init__(self, value=None):
        if value:
            value = "Profile object related to user required for '%s' " \
                "to function correctly." % value
        else:
            value = "Profile object related to user required."
        super(ProfileRequiredException, self).__init__(value)


class InvalidContentTypeException(Exception):
    """Exception raised when an invalid content type string is
    encountered.
    
    """

    def __init__(self):
        value = "Profile object related to user required."
        super(InvalidContentTypeException, self).__init__(value)
