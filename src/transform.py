
import pandas as pd
import numpy as np



class TransformarDados:
    """Esta classe define os métodos e atributos necessários para a etapa de transformação e modelagem dos dados."""
    def __init__(self, dados,engine):
        self.dados = dados
        self.df_origem = None
        self.df_exploded = None
        self.engine = engine




    def trat_dados_origem(self):
        """Este método realiza o tratamento geral da base de dados antes da criação das dimensões e fato, como mundança de tipos e padronização de valores."""
        df = pd.DataFrame(self.dados)
        df_origem = df.copy()
        df_origem.columns

        columns_drop = ['company_logo_url','company_logo','url','description']
        df_origem = df_origem.drop(columns=columns_drop)

        # definindo moeda
        df_origem["currency"] = df_origem["salary"].apply(lambda x: "USD" if isinstance(x, str) and "$" in x else np.nan)

        # tratando inconsistencias no salario 
        df_origem["salary"] = (
            df_origem["salary"]
            .str.replace("OTE", "", regex=False)
            .str.strip()
        )
        
        # separando periodo
        hour = df_origem["salary"].str.contains(r'\b(hour|hr)\b',case=False,na=False)
        df_origem["period"] = np.where(hour,"hour","year")
        
        # separando faixa salarial:
        faixa = df_origem["salary"].str.split(r'\s*-\s*', n=1, expand=True)
        parte_min = faixa[0]
        parte_max = faixa[1]

        def extrai_valor(serie):
            """Faz a extração dos números na string, para determinar os valores minimo e maximo da faixa salarial."""
            # pega número (com , ou . decimal) + 'k' opcional
            num = serie.str.extract(r'(\d+(?:[.,]\d+)?)\s*([kK])?')
            valor = num[0].str.replace(',', '.', regex=False).astype(float)
            valor = np.where(num[1].notna(), valor * 1000, valor)
            return valor

        df_origem["salary_min"] = extrai_valor(parte_min)
        df_origem["salary_max"] = extrai_valor(parte_max)
        
        df_origem["salary_max"] = df_origem["salary_max"].fillna(df_origem["salary_min"])


        # tratando coluna de data:
        df_origem["publication_date"] = pd.to_datetime(df_origem["publication_date"],errors='coerce')

        self.df_origem = df_origem
        return self.df_origem



    # Modelagem dos dados:

    # Tratamento

    def criar_dim_empresa(self):
        """Este método é responsável por criar a tabela de dimensão com o id e nome de cada empresa."""
        dim_empresa = (
            self.df_origem[["company_name"]]
            .drop_duplicates()
            .reset_index(drop=True))
        dim_empresa = dim_empresa.rename(columns={"company_name":"nome_empresa"})
        return dim_empresa

    
    def explodir_skills(self):
        """Este método é responsável por separar a coluna de tags em uma linha por skill (explode)."""
        self.df_exploded = self.df_origem.explode('tags').reset_index(drop=True)
        return self.df_exploded


    def criar_dim_skill(self):
        """Este método é responsável por criar a tabela de dimensão com o id e nome de cada skill."""

        dim_skill = (
        self.df_exploded[["tags"]]
        .drop_duplicates()
        .reset_index(drop=True)

    )
        dim_skill = dim_skill.rename(columns={"tags":"nome_skill"})
        dim_skill["nome_skill"] = dim_skill["nome_skill"].fillna("Não especificado")
        return dim_skill

    def criar_dim_categoria(self):
        """Este método é responsável por criar a tabela de dimensão com o id e nome de cada categoria pertencente à vaga."""
        dim_categoria = (
            self.df_origem[["category"]]
            .drop_duplicates()
            .reset_index(drop=True)

        )
        dim_categoria = dim_categoria.rename(columns={"category":"nome_categoria"})
        return dim_categoria 

    def criar_dim_localizacao(self):
        """Este método é responsável por criar a tabela de dimensão com o id e nome de cada região."""
        dim_local = ( 
            self.df_origem[["candidate_required_location"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        dim_local = dim_local.rename(columns={"candidate_required_location":"localizacao_candidato"})
        return dim_local




    def buscar_dimensoes(self):
        """Este método é responsável por realizarf a busca de todas as tabelas de dimensão do banco e retorná-las em um dicionário."""
        dim_empresa = pd.read_sql("SELECT * FROM dim_empresa", self.engine)
        dim_categoria = pd.read_sql("SELECT * FROM dim_categoria", self.engine)
        dim_skill = pd.read_sql("SELECT * FROM dim_skill", self.engine)
        dim_local = pd.read_sql("SELECT * FROM dim_local", self.engine)

        return {
            "dim_empresa": dim_empresa,
            "dim_categoria": dim_categoria,
            "dim_skill": dim_skill,
            "dim_local": dim_local
        }





    def criar_fato(self,dimensoes):
        """Este método é responsável por criar a tabela de eventos das vagas, contendo os ids das dimensoes( tabela principal)"""
        dim_empresa = dimensoes["dim_empresa"]
        dim_local = dimensoes["dim_local"]
        dim_categoria = dimensoes["dim_categoria"]

        fato_vagas = self.df_origem.merge(
            dim_empresa,
            how='left',
            left_on='company_name',
            right_on='nome_empresa'
        )

        fato_vagas = fato_vagas.merge(
            dim_categoria,
            how='left',
            left_on='category',
            right_on='nome_categoria'
        )
        fato_vagas = fato_vagas.merge(
            dim_local,
            how='left',
            left_on='candidate_required_location',
            right_on='localizacao_candidato'
        )
        columns = ["id","title","job_type","publication_date","salary_min","currency","salary_max","id_empresa","id_categoria","id_local"]
        fato_vagas = fato_vagas[columns]
        fato_vagas = fato_vagas.rename(columns={"id": "vaga_id","id_empresa":"empresa_id","id_categoria":"categoria_id","id_local":"localizacao_id"})

        return fato_vagas


    def criar_bridge_skills(self,df_skill):
        """Este método é responsável por criar a tabela de ponte entre as skills e as vagas, permitindo relacioná-las."""

        df_bridge_skills = (
            self.df_exploded.merge(
            df_skill,
            how='left',
            left_on="tags",
            right_on="nome_skill")
            )
        
        df_bridge_skills = df_bridge_skills[["id","skill_id"]]
        
        df_bridge_skills = df_bridge_skills.dropna()
        df_bridge_skills["skill_id"] = df_bridge_skills["skill_id"].astype(int)
        df_bridge_skills = df_bridge_skills.rename(columns={"id":"vaga_id"})
        return df_bridge_skills

