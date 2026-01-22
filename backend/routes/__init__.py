"""
Routes package - All API routers are exported from here
"""
from fastapi import APIRouter

# Import individual routers
from .settings import router as settings_router
from .programs import router as programs_router
from .companies import router as companies_router
from .auth import router as auth_router
from .users import router as users_router
from .attendance import router as attendance_router
from .participant_access import router as participant_access_router
from .tests import router as tests_router
from .feedback import router as feedback_router

# Create combined router for easy registration
def get_all_routers():
    """Return list of all routers with their prefixes already set"""
    return [
        settings_router,        # /settings
        programs_router,        # /programs
        companies_router,       # /companies
        auth_router,           # /auth/*
        users_router,          # /users
        attendance_router,     # /attendance/*
        participant_access_router,  # /participant-access/*
        tests_router,          # /tests/*
        feedback_router,       # /feedback-templates/*, /feedback/*, coordinator/chief-trainer feedback
    ]

__all__ = [
    'settings_router',
    'programs_router', 
    'companies_router',
    'auth_router',
    'users_router',
    'attendance_router',
    'participant_access_router',
    'tests_router',
    'feedback_router',
    'get_all_routers',
]
