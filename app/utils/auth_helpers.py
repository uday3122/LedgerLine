
from functools import wraps

from flask import jsonify, g
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity,
)

from app import db
from app.models import User


def current_user_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        # Verify that a valid JWT token is provided.
        verify_jwt_in_request()

        # Get the user ID from the token.
        user_id = get_jwt_identity()

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({
                "error": "Invalid user identity"
            }), 401

        # Always retrieve the latest user details from PostgreSQL.
        user = db.session.get(User, user_id)

        if user is None or not user.is_active:
            return jsonify({
                "error": "User not found or inactive"
            }), 401

        # Make the verified user available to the route.
        g.current_user = user

        return function(*args, **kwargs)

    return wrapper


def roles_required(*allowed_roles):
    def decorator(function):

        @wraps(function)
        @current_user_required
        def wrapper(*args, **kwargs):

            if g.current_user.role not in allowed_roles:
                return jsonify({
                    "error": "You do not have permission to perform this action"
                }), 403

            return function(*args, **kwargs)

        return wrapper

    return decorator
