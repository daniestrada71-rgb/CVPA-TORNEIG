from functools import wraps
from flask import session, redirect, url_for, current_app

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("main.admin_login"))
        return f(*args, **kwargs)
    return wrapper
