import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MeghaMySQL",
        database="task_manager_db"
    )
    return conn
