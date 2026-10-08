class Session:
    current_user = None

    @classmethod
    def start(cls, user): cls.current_user = user
    @classmethod
    def end(cls): cls.current_user = None
    @classmethod
    def is_authenticated(cls): return cls.current_user is not None
    @classmethod
    def is_admin(cls): return bool(cls.current_user and cls.current_user.get("rol") == "ADMINISTRADOR")
    @classmethod
    def can(cls, permission):
        from app.services.auth_service import AuthService
        return AuthService.can(cls.current_user, permission)
