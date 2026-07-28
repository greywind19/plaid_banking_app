"""
In-memory store for the Plaid access_token and a cached copy of synced
transactions. Intentionally ephemeral — persistence is a later phase. The
access_token and secret NEVER leave the server.
"""


class TokenStore:
    def __init__(self) -> None:
        self.access_token: str | None = None
        self.item_id: str | None = None
        self.cursor: str | None = None
        self.transactions: list[dict] = []

    def is_linked(self) -> bool:
        return self.access_token is not None

    def set_item(self, access_token: str, item_id: str) -> None:
        self.access_token = access_token
        self.item_id = item_id
        self.cursor = None
        self.transactions = []

    def require_token(self) -> str:
        if not self.access_token:
            raise RuntimeError(
                "No linked account. Call /api/connect first to bootstrap the "
                "Plaid sandbox Item."
            )
        return self.access_token

    def reset(self) -> None:
        self.__init__()


token_store = TokenStore()
