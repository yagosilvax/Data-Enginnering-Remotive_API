import requests
import json


class RemotiveExtractor:
    """Esta classe extrai os dados brutos da API do Remotive Jobs e retorna o arquivo JSON na pasta 'raw'. """

    def __init__(self,url="https://remotive.com/api/remote-jobs",output_path="raw/remotive_data.json"):
        self.url = url
        self.output_path = output_path

    def extrair_dados(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            json_file = response.json()
            dados = json_file["jobs"]
            return dados
        except Exception:
            raise

    def salvar_dados(self,dados):
        with open(self.output_path,'w') as file:
            json.dump(dados,file,indent=4)



