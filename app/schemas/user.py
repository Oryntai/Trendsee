from pydantic import BaseModel


class MeOut(BaseModel):
    user_id: int
    token_balance: int
    is_admin: bool
