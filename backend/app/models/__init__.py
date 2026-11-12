from app.models.user import User, UserProfile  # noqa: F401
from app.models.recipient import Recipient      # noqa: F401
from app.models.catalog import CatalogItem      # noqa: F401
from app.models.feedback import Feedback        # noqa: F401
from app.models.auth_session import AuthSession  # noqa: F401

# --- Santa module (sprint 5) ---
from app.models.santa import (  # noqa: F401
    Room,
    Participant,
    Exclusion,
    Draw,
    Assignment,
    GiftSuggestion,
    Message,
    Notification,
    Invite,
)