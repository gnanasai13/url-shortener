import secrets
import string
SHORT_CODE_ALPHABET = string.ascii_letters + string.digits
def generate_short_code(length: int = 8) -> str:
    return "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(length))
