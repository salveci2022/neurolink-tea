"""
NeuroLink TEA — Decoradores de autorização
"""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user


def perfil_requerido(*perfis):
    """Permite acesso apenas para os perfis listados (+ ADMIN sempre passa)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from app.models import UserPerfil
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.perfil == UserPerfil.ADMIN:
                return f(*args, **kwargs)
            if current_user.perfil not in perfis:
                flash('Você não tem permissão para acessar esta área.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def tenant_ativo(f):
    """Bloqueia acesso se o tenant estiver suspenso ou com plano expirado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        tenant = current_user.tenant
        if not tenant.ativo:
            flash('Sua organização está suspensa. Entre em contato com o suporte.', 'danger')
            return redirect(url_for('auth.logout'))
        if not tenant.plano_ativo():
            flash('Seu plano expirou. Entre em contato com o suporte.', 'warning')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated


def logout_required(f):
    """Redireciona usuários já logados para o dashboard."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            from app.routes.auth import _redirecionar_por_perfil
            return _redirecionar_por_perfil(current_user.perfil)
        return f(*args, **kwargs)
    return decorated


def mesmo_tenant(model_class, param='id'):
    """Garante que o objeto acessado pertence ao mesmo tenant do usuário."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from app.models import UserPerfil
            obj_id = kwargs.get(param)
            obj = model_class.query.get_or_404(obj_id)
            if current_user.perfil != UserPerfil.ADMIN:
                if hasattr(obj, 'tenant_id') and obj.tenant_id != current_user.tenant_id:
                    abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
