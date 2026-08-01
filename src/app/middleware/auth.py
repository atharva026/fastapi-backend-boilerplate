from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request

from src.app.api import is_public_endpoint, is_auth_endpoint, is_email_endpoint
from src.app.core.security import verify_token
from src.app.core.token_store import TokenStore

class AuthenticationMiddleware:
    """
    ASGI middleware for authentication.
    This middleware checks if the request is authenticated and adds the user information to the request state.
    It also handles public and auth endpoints, allowing them to bypass authentication.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope) # , receive, send) # no receive/send; read-only headers/cookies

        # CORS preflight — pass straight through
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return
        
        # ensure state namespace exists
        if "state" not in scope:
            scope["state"] = {}

        method = request.method
        path = request.url.path

        is_public = is_public_endpoint(method, path)
        is_auth = is_auth_endpoint(method, path)
        is_email_ep = is_email_endpoint(method, path)

        # print(method, path, is_public, is_auth, is_email_ep, sep="\t|\t")
        
        scope["state"]["is_email_endpoint"] = is_email_ep

        # Public / auth endpoints: mark and continue — no token required
        if is_public:
            scope["state"]["is_public"] = True
            scope["state"]["is_auth_endpoint"] = is_auth
            scope["state"]["auth_failed"] = False
            await self.app(scope, receive, send)
            return

        # Private endpoint — attempt authentication
        scope["state"]["is_public"] = False
        scope["state"]["is_auth_endpoint"] = False

        token_store: TokenStore = getattr(request.app.state, "token_store", None)
        token = request.cookies.get("access_token")

        if not token:
            scope["state"]["auth_failed"] = True
            scope["state"]["auth_error"] = "NOT_AUTHENTICATED"
            scope["state"]["auth_error_message"] = "Not authenticated"
            await self.app(scope, receive, send)
            return

        try:
            payload = verify_token(token, token_type="access")
        except Exception as e:                                      # EXCEPTIONS: ExpiredSignatureError, InvalidTokenError
            scope["state"]["auth_failed"] = True
            scope["state"]["auth_error"] = str(e.code)
            scope["state"]["auth_error_message"] = str(e.message)
            await self.app(scope, receive, send)
            return

        user_id = payload.get("sub")
        if not user_id:
            scope["state"]["auth_failed"] = True
            scope["state"]["auth_error"] = "invalid_token"
            scope["state"]["auth_error_message"] = "Invalid token"
            await self.app(scope, receive, send)
            return

        if token_store and await token_store.is_access_token_blocked(payload.get("jti", "")):
            scope["state"]["auth_failed"] = True
            scope["state"]["auth_error"] = "invalid_token"
            scope["state"]["auth_error_message"] = "Invalid token"
            await self.app(scope, receive, send)
            return

        # Success
        scope["state"]["auth_failed"] = False
        scope["state"]["user_id"] = user_id
        scope["state"]["token_payload"] = payload
        await self.app(scope, receive, send)
