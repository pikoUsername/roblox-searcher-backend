from seleniumrequests import RequestsSessionMixin
from seleniumwire.webdriver import Firefox as _Firefox


class Firefox(RequestsSessionMixin, _Firefox):
    pass
