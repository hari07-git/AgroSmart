from flask import Flask

from .config import Config
from .db import db


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="../static")
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)

    with app.app_context():
        from . import models  # noqa: F401
        from .schema import ensure_schema

        db.create_all()
        ensure_schema()

    from .i18n import SUPPORTED_LANGS, get_lang, t

    from .routes import bp as main_bp
    from .routes_auth import bp as auth_bp
    from .routes_services import bp as services_bp
    from .routes_api import bp as api_bp
    from .routes_admin import bp as admin_bp
    from .routes_admin_auth import bp as admin_auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_auth_bp)

    from flask import render_template

    @app.errorhandler(401)
    def _err_401(_err):
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def _err_403(_err):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def _err_404(_err):
        return render_template("errors/404.html"), 404

    @app.context_processor
    def _inject_i18n():
        from flask import session
        from .models import User

        user_id = session.get("user_id")
        is_admin = False
        if user_id:
            user = db.session.get(User, int(user_id))
            is_admin = bool(user and user.is_admin)

        return {"t": t, "lang": get_lang(), "supported_langs": SUPPORTED_LANGS, "is_admin": is_admin}

    return app
