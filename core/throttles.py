from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return f"throttle_login_{self.get_ident(request)}"


class RegisterRateThrottle(SimpleRateThrottle):
    scope = "register"

    def get_cache_key(self, request, view):
        return f"throttle_register_{self.get_ident(request)}"


class MarketRefreshThrottle(UserRateThrottle):
    scope = "market_refresh"
