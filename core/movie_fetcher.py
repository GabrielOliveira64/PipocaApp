import os
import json
import requests
import shutil
from urllib.parse import quote


class MovieFetcher:
    """Busca informações essenciais de filmes via API do TMDB."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("TMDB_API_KEY", "d4affd4cdfcd7bc2b5f5f27a2ca99b1e")
        self.base_url = "https://api.themoviedb.org/3"
        self.poster_base_url = "https://image.tmdb.org/t/p/w500"

    # ------------------------------------------------------------------
    # Cache local (info.json + poster.jpg na pasta do filme)
    # ------------------------------------------------------------------

    def get_movie_folder(self, file_path):
        """Retorna a pasta onde o arquivo de vídeo está."""
        return os.path.dirname(os.path.abspath(file_path))

    def get_local_info_path(self, file_path):
        """Retorna o caminho esperado do info.json na pasta do filme."""
        return os.path.join(self.get_movie_folder(file_path), "info.json")

    def get_local_poster_path(self, file_path):
        """Retorna o caminho esperado do poster.jpg na pasta do filme."""
        return os.path.join(self.get_movie_folder(file_path), "poster.jpg")

    def load_local_info(self, file_path):
        """
        Tenta carregar info.json da pasta do filme.
        Retorna o dict com as informações se existir e for válido, ou None.
        """
        info_path = self.get_local_info_path(file_path)
        poster_path = self.get_local_poster_path(file_path)

        if not os.path.exists(info_path):
            return None

        try:
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.load(f)

            # Garante que o campo local_poster_path aponta para o poster
            # na pasta do filme (mesmo que o JSON tenha um caminho antigo)
            if os.path.exists(poster_path):
                info["local_poster_path"] = poster_path
            else:
                info["local_poster_path"] = None

            return info
        except (json.JSONDecodeError, Exception):
            return None

    def save_local_info(self, file_path, movie_info):
        """
        Salva info.json na pasta do filme.
        Não salva local_poster_path no JSON (é um caminho absoluto que
        muda se a pasta for movida — é recalculado no load_local_info).
        """
        folder = self.get_movie_folder(file_path)
        info_path = os.path.join(folder, "info.json")

        # Copia sem o campo local_poster_path para não poluir o JSON
        info_to_save = {k: v for k, v in movie_info.items() if k != "local_poster_path"}

        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Aviso: não foi possível salvar info.json em {folder}: {e}")

    def delete_local_files(self, file_path):
        """
        Apaga info.json e poster.jpg da pasta do filme.
        Chamado ao deletar ou atualizar um filme.
        """
        for name in ("info.json", "poster.jpg"):
            target = os.path.join(self.get_movie_folder(file_path), name)
            if os.path.exists(target):
                try:
                    os.remove(target)
                except Exception as e:
                    print(f"Aviso: não foi possível remover {target}: {e}")

    # ------------------------------------------------------------------
    # API TMDB
    # ------------------------------------------------------------------

    def search_movie(self, title):
        """Busca um filme pelo título."""
        endpoint = f"{self.base_url}/search/movie"
        params = {
            "api_key": self.api_key,
            "query": quote(title),
            "language": "pt-BR"
        }
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return results[:5] if results else []
        return []

    def get_movie_details(self, movie_id):
        """Obtém detalhes do filme — apenas campos essenciais."""
        endpoint = f"{self.base_url}/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR"
        }
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            return response.json()
        return None

    def download_poster(self, poster_path, movie_id, file_path=None):
        """
        Baixa o poster do filme.

        Se file_path for fornecido, salva como poster.jpg na pasta do filme.
        Caso contrário, salva na pasta legada assets/poster_images/ (fallback).
        """
        if not poster_path:
            return None

        poster_url = f"{self.poster_base_url}{poster_path}"

        if file_path:
            local_path = self.get_local_poster_path(file_path)
        else:
            local_path = f"assets/poster_images/{movie_id}.jpg"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

        response = requests.get(poster_url, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)
            return local_path
        return None

    def extract_movie_info(self, movie_data):
        """Extrai apenas as informações essenciais do filme."""
        return {
            "id": movie_data["id"],
            "title": movie_data["title"],
            "original_title": movie_data["original_title"],
            "release_date": movie_data.get("release_date", ""),
            "overview": movie_data.get("overview", ""),
            "poster_path": movie_data.get("poster_path"),
            "genres": [genre["name"] for genre in movie_data.get("genres", [])],
            "runtime": movie_data.get("runtime"),
            "vote_average": movie_data.get("vote_average"),
        }
