import logging
import pandas as pd

from extract import RemotiveExtractor
from transform import TransformarDados
from load import EnviarBanco


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("vagas_remotas_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("===========INICIANDO PIPELINE E MODELAGEM DOS DADOS=============")

        # Extração
        try:
            logger.info("Extraindo dados...\n")
            extrator = RemotiveExtractor()
            dados = extrator.extrair_dados()
            logger.info("Dados extraídos com sucesso!\n")
            extrator.salvar_dados(dados)
            logger.info("Dados brutos salvos na pasta.")
        except Exception as e:
            logger.critical(f"Extração interrompida: {e}")
            raise  

        try:
            logger.info("Iniciando conexão com o banco de dados...")
            carregador = EnviarBanco()
            logger.info("Conexão criada")
        except Exception as e:
            logger.critical(f"Erro ao tentar realizar conexão com o banco de dados: {e}")
            raise

        # Transformação
        try:
            logger.info("Iniciando a transformação dos dados de origem...")
            transformador = TransformarDados(dados=dados, engine=carregador.engine)
            transformador.trat_dados_origem()
            transformador.explodir_skills()  
            logger.info("Dados transformados e padronizados!\n")
        except Exception as e:
            logger.error(f"Erro ao tentar transformar os dados: {e}")
            raise

        # Criação das dimensões
        try:
            logger.info("Criando tabelas de dimensão...")
            dim_empresa = transformador.criar_dim_empresa()
            dim_skill = transformador.criar_dim_skill()
            dim_local = transformador.criar_dim_localizacao()
            dim_categoria = transformador.criar_dim_categoria()
            logger.info("Tabelas criadas com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas de dimensão: {e}")
            raise

        # Carga das dimensões
        try:
            logger.info("Encaminhando as tabelas dimensionais para o banco de dados...")
            tabelas_dim = {
                "dim_categoria": dim_categoria,
                "dim_empresa": dim_empresa,
                "dim_skill": dim_skill,
                "dim_local": dim_local,
            }
            carregador.carregar_dimensoes(tabelas_dim)
            logger.info("Tabelas de dimensão enviadas para o banco de dados.")
        except Exception as e:
            logger.error(f"Erro ao enviar as tabelas para o banco de dados: {e}")
            raise

        # Fato + bridge
        try:
            logger.info("Consultando tabelas de dimensão...")
            dimensoes = transformador.buscar_dimensoes()

            logger.info("Criando tabela de fatos...")
            fato_vagas = transformador.criar_fato(dimensoes)

            logger.info("Enviando tabela de fatos para o banco de dados...")
            carregador.carregar_fato_vagas(fato_vagas, "fato_vaga")

            logger.info("Criando tabela de ponte entre skills e vagas...")
            skill_banco = pd.read_sql("SELECT * FROM dim_skill", carregador.engine)
            dim_vaga_skill = transformador.criar_bridge_skills(skill_banco)

            logger.info("Enviando tabela de ponte para o banco de dados...")
            carregador.carregar_bridge_skill(dim_vaga_skill, "dim_vaga_skill")

            logger.info("Tabela criada e enviada para o banco.")
        except Exception as e:
            logger.error(f"Erro ao executar: {e}")
            raise

        logger.info("==================PIPELINE FINALIZADO==================")

    except Exception as e:
        logger.critical(f"Erro ao finalizar o pipeline: {e}")


if __name__ == "__main__":
    main()