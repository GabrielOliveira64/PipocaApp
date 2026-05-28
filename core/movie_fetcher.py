import os
import requests
import shutil
from urllib.parse import quote


class MovieFetcher:
    """Busca informações essenciais de filmes via API do TMDB."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("TMDB_API_KEY", "d4affd4cdfcd7bc2b5f5f27a2ca99b1e")
        self.base_url = "https://api.themoviedb.org/3"
        self.poster_base_url = "https://image.tmdb.org/t/p/w500"

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
        """Obtém detalhes do filme — apenas campos essenciais, sem créditos ou imagens extras."""
        endpoint = f"{self.base_url}/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR"
            # Sem append_to_response: não busca credits, videos nem images
        }
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            return response.json()
        return None

    def download_poster(self, poster_path, movie_id):
        """Baixa o poster do filme e salva localmente."""
        if not poster_path:
            return None

        poster_url = f"{self.poster_base_url}{poster_path}"
        local_path = f"assets/poster_images/{movie_id}.jpg"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        response = requests.get(poster_url, stream=True)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
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
