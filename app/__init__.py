"""
NeuroLink TEA — App Factory
"""
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from config import config
from app.models import db, bcrypt, User

migrate       = Migrate()
login_manager = LoginManager()


def create_app(config_name='default'):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config[config_name])

    # Extensões
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Login config
    login_manager.login_view             = 'auth.login'
    login_manager.login_message          = 'Faca login para acessar.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Criar tabelas automaticamente se nao existirem
    with app.app_context():
        db.create_all()

    # Blueprints
    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.criancas  import criancas_bp
    from app.routes.rotinas   import rotinas_bp
    from app.routes.gps       import gps_bp
    from app.routes.clinica   import clinica_bp
    from app.routes.ia        import ia_bp
    from app.routes.admin     import admin_bp
    from app.routes.api       import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(criancas_bp,  url_prefix='/criancas')
    app.register_blueprint(rotinas_bp,   url_prefix='/rotinas')
    app.register_blueprint(gps_bp,       url_prefix='/gps')
    app.register_blueprint(clinica_bp,   url_prefix='/clinica')
    app.register_blueprint(ia_bp,        url_prefix='/ia')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(api_bp,       url_prefix='/api/v1')

    # Filtros de template
    from app.utils.template_filters import register_filters
    register_filters(app)

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        return dict(current_user=current_user)

    return app
