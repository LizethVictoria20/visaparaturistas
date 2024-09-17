import sqlite3

def get_db_connection():
    conn = sqlite3.connect('form_results.db')  # Usa el nombre de tu base de datos
    conn.row_factory = sqlite3.Row
    return conn

def delete_record_by_id(record_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM results WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0  # Retorna True si se eliminó un registro
