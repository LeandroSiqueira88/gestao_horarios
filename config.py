import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '123456'
    MYSQL_DB = 'gestao_horarios'

class Config:
    SECRET_KEY = 'sua_chave_secreta'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '123456'  # Altere para sua senha do MySQL
    MYSQL_DB = 'gestao_horarios'
