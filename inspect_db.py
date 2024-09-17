from app import app, db, FormResult

with app.app_context():
    inspector = db.inspect(db.engine)
    columns = inspector.get_columns('form_result')
    for column in columns:
        print(column['name'], column['type'])
