from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def role_required(role):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('login'))
            if not current_user.has_role(role):
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        return decorated_view
    return wrapper


def non_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Suponiendo que 'admin' es el nombre del rol de administrador
        if current_user.has_role('admin'):
            flash("Esta sección es solo para usuarios no administradores.", "warning")
            return redirect(url_for('index'))  # O cualquier otra ruta a la que debas redirigir a los admins
        return f(*args, **kwargs)
    return decorated_function