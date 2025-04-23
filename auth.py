from functools import wraps
from flask import session, redirect, url_for, flash

def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Você precisa estar logado!", "danger")
            return redirect(url_for('routes.login'))
        return f(*args, **kwargs)
    return decorated_function

def somente_master(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('usuario_perfil') != 'master':
            flash("Acesso negado!", "danger")
            return redirect(url_for('routes.index'))
        return f(*args, **kwargs)
    return decorated_function

def perfil_autorizado(perfis_permitidos):
    def decorador(f):
        @wraps(f)
        def funcao_decorada(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Você precisa estar logado para acessar esta página.', 'danger')
                return redirect(url_for('routes.login'))
            if session.get('usuario_perfil') not in perfis_permitidos:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('routes.dashboard'))
            return f(*args, **kwargs)
        return funcao_decorada
    return decorador