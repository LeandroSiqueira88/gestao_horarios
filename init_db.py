import sqlite3

def criar_banco():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Criando a tabela de professores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            endereco TEXT NOT NULL,
            telefone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            especialidade TEXT NOT NULL,
            observacao TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Banco de dados e tabela criados com sucesso!")

if __name__ == "__main__":
    criar_banco()
