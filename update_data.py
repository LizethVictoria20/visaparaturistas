from app import app, db, FormResult
from sqlalchemy.orm import Session

def update_data():
    with app.app_context():
        # Crear una sesión
        session = Session(db.engine)
        # Buscar el registro con el ID 1 usando Session.get()
        record = session.get(FormResult, 1)
        if record:
            # Actualizar el campo apellido
            record.apellidos = "Celis Testing"
            session.commit()
            print(f"Registro actualizado: ID: {record.id}, Apellidos: {record.apellidos}")
        else:
            print("Registro no encontrado")
        session.close()

if __name__ == '__main__':
    update_data()
