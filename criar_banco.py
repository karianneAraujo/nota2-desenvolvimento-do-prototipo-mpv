import sqlite3
from pathlib import Path

# Defina o caminho do banco de dados
DB_PATH = Path(__file__).parent / 'banco_dados.db'

def criar_banco():
    """Cria o banco de dados com as tabelas necessárias."""
    
    conexao = sqlite3.connect(str(DB_PATH))
    cursor = conexao.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL DEFAULT '',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL,
            cartao_sus TEXT NOT NULL,
            data_nascimento TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS producao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            data_atendimento TEXT NOT NULL,
            servico TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            valor REAL NOT NULL DEFAULT 0,
            observacao TEXT,
            FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
        )
    ''')

    cursor.execute('PRAGMA table_info(usuarios)')
    colunas = [row[1] for row in cursor.fetchall()]
    if 'senha' not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN senha TEXT NOT NULL DEFAULT ''")
    if 'is_admin' not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    
    conexao.commit()
    conexao.close()
    
    print(f"Banco de dados criado com sucesso em: {DB_PATH}")

if __name__ == '__main__':
    criar_banco()
