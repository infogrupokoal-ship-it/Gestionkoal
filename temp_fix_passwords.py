import os
from werkzeug.security import generate_password_hash
from backend import create_app, db

app = create_app()

with app.app_context():
    print("Contexto de la aplicación creado para actualizar contraseñas.")
    try:
        # Contraseña estándar para los usuarios de prueba
        password = 'password123'
        hashed_password = generate_password_hash(password)
        
        print(f"Generando nuevo hash para la contraseña: {password}")

        # Actualizar usuarios de prueba
        usernames_to_update = ['admin', 'autonomo']
        
        from sqlalchemy import text
        for username in usernames_to_update:
            db.session.execute(
                text("UPDATE users SET password_hash = :password_hash WHERE username = :username"),
                {"password_hash": hashed_password, "username": username}
            )
            print(f"Contraseña para el usuario '{username}' actualizada en la sesión.")
        
        db.session.commit()
        print("\n¡ÉXITO! Las contraseñas para los usuarios de prueba han sido reseteadas a 'password123'.")

    except Exception as e:
        db.session.rollback()
        print(f"\nERROR DURANTE LA ACTUALIZACIÓN DE CONTRASEÑAS: {e}")
