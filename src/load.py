from sqlalchemy import create_engine,text
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class EnviarBanco:
    """A classe EnviarBanco gerencia as conexões com o banco de dados e envia todas as tabelas de dimensão e fato para o data warehouse."""
    def __init__(self):
        self.engine = self._conectar()

    def _conectar(self):
        """Realiza a conexão com o banco de dados."""
        host = os.getenv("host")
        database = os.getenv("database")
        user = os.getenv("usuario")
        port = os.getenv("port")
        password = os.getenv("senha_banco")
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        engine = create_engine(url)

        try:
            with engine.connect():
                return engine
        except Exception:
            raise
    

    def _carregar_dimensao(self,df,nome_tabela,conn):
            """Define o script SQL responsável por iterar as linhas de cada dataframe referente às 
            dimensões, e inserir no banco de dados apenas registros novos."""

            coluna = df.columns[0]
            sql = f"""
            INSERT INTO {nome_tabela} ({coluna})
            VALUES (:valor)
            ON CONFLICT ({coluna}) DO NOTHING
            """
            for _, row in df.iterrows():
                conn.execute(
                text(sql),
                {"valor": row[coluna]}
            )

 
    def carregar_dimensoes(self,tabelas_dim: dict):
        """Este método é responsável por carregar todas tabelas de dimensão no banco de dados."""
        with self.engine.begin() as conn:
            for nome_tabela, df in tabelas_dim.items():
                self._carregar_dimensao(df, nome_tabela, conn)



    def carregar_fato_vagas(self,tabela_fato,nome_tabela):
        """Este método é responsável por carregar a tabela de fatos no banco de dados."""
        colunas = tabela_fato.columns.to_list()
        coluna_constraint = "vaga_id"
        colunas_sql = ", ".join(colunas)
        valores_sql = ", ".join([f":{col}" for col in colunas])

        with self.engine.begin() as conn:
            sql = f"""
            INSERT INTO {nome_tabela} ({colunas_sql})
            VALUES ({valores_sql})
            ON CONFLICT ({coluna_constraint}) DO NOTHING
            """
            for _, row in tabela_fato.iterrows():
                conn.execute(
                text(sql),
                row.to_dict()
            )

    
    def carregar_bridge_skill(self,df_bridge,nome_tabela):
        """Este método é responsável por carregar a tabela de ponte no banco de dados."""
        columns = df_bridge.columns.to_list()
        colunas_sql = ", ".join(columns)
        valores_sql = ", ".join([f":{col}" for col in columns])

        with self.engine.begin() as conn:
            sql = f"""
            INSERT INTO {nome_tabela} ({colunas_sql})
            VALUES ({valores_sql})
            """
            for _, row in df_bridge.iterrows():
                conn.execute(
                text(sql),
                row.to_dict()
            )
            
