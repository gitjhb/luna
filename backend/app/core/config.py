# Re-export from app.config for backward compatibility
from app.config import settings, Settings

__all__ = ['settings', 'Settings']
