import sqlite3
from pathlib import Path

# Defina o caminho do banco de dados
DB_PATH = Path(__file__).parent / 'banco_dados.db'

def criar_banco():
    """Cria o banco de dados com as tabelas necessárias."""
    
    conexao = sqlite3.connect(str(DB_PATH))
    cursor = conexao.cursor()
    
    # Exemplo de tabela - ajuste conforme necessário
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conexao.commit()
    conexao.close()
    
    print(f"✓ Banco de dados criado com sucesso em: {DB_PATH}")

if __name__ == '__main__':
    criar_banco()
