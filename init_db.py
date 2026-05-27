from app import create_app, db
from app.models.user import User

def init_db():
    flask_app = create_app()
    with flask_app.app_context():
        # Import models inside context to ensure they are registered with SQLAlchemy
        import app.models 
        
        db.create_all()
        
        # Check if admin already exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                name='Administrador AVA',
                email='admin@ava.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Banco de dados inicializado e usuário admin criado (admin@ava.com / admin123).")
        else:
            print("Banco de dados já contém usuários.")

if __name__ == '__main__':
    init_db()
