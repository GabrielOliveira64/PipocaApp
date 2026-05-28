import os
import json
import shutil
from datetime import datetime
import mimetypes


class MovieManager:
    """Gerencia o catálogo de filmes."""

    def __init__(self, catalog_path="data/catalog.json"):
        self.catalog_path = catalog_path
        self.catalog = self.load_catalog()

    def validate_movie_files(self):
        """Remove do catálogo filmes cujo arquivo de vídeo não existe mais."""
        movies = self.catalog.get("movies", [])
        valid_movies = []
        removed_movies = []

        for movie in movies:
            file_path = movie.get("file_path")
            if file_path and os.path.exists(file_path) and self.is_video_file(file_path):
                valid_movies.append(movie)
            else:
                removed_movies.append(movie)
                poster = movie.get("local_poster_path")
                if poster and os.path.exists(poster):
                    try:
                        os.remove(poster)
                    except Exception:
                        pass

        if removed_movies:
            self.catalog["movies"] = valid_movies
            self.save_catalog()

        return {
            "valid_count": len(valid_movies),
            "removed_count": len(removed_movies),
            "removed_movies": [m.get("title") for m in removed_movies]
        }

    def load_catalog(self):
        """Carrega o catálogo e valida os arquivos dos filmes."""
        if os.path.exists(self.catalog_path):
            try:
                with open(self.catalog_path, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
                self.catalog = catalog
                result = self.validate_movie_files()
                if result["removed_count"] > 0:
                    print(f"{result['removed_count']} filme(s) removido(s): arquivos não encontrados.")
                return self.catalog
            except json.JSONDecodeError:
                return {"movies": []}
        return {"movies": []}

    def save_catalog(self):
        """Salva o catálogo no arquivo JSON."""
        with open(self.catalog_path, 'w', encoding='utf-8') as f:
            json.dump(self.catalog, f, ensure_ascii=False, indent=2)

    def get_all_movies(self):
        """Retorna todos os filmes do catálogo."""
        return self.catalog.get("movies", [])

    def get_movie_by_id(self, movie_id):
        """Busca um filme pelo ID local."""
        for movie in self.catalog.get("movies", []):
            if movie.get("id") == movie_id:
                return movie
        return None

    def add_movie(self, movie_info, file_path):
        """Adiciona ou atualiza um filme no catálogo."""
        movies = self.catalog.get("movies", [])

        # Atualiza se já existir pelo tmdb_id
        for i, movie in enumerate(movies):
            if movie.get("tmdb_id") == movie_info.get("id"):
                movies[i].update({
                    "tmdb_id": movie_info.get("id"),
                    "title": movie_info.get("title"),
                    "original_title": movie_info.get("original_title"),
                    "release_date": movie_info.get("release_date"),
                    "overview": movie_info.get("overview"),
                    "local_poster_path": movie_info.get("local_poster_path"),
                    "genres": movie_info.get("genres", []),
                    "runtime": movie_info.get("runtime"),
                    "vote_average": movie_info.get("vote_average"),
                    "file_path": file_path,
                    "last_updated": datetime.now().isoformat(),
                })
                self.save_catalog()
                return movies[i]

        # Novo filme
        new_movie = {
            "id": len(movies) + 1,
            "tmdb_id": movie_info.get("id"),
            "title": movie_info.get("title"),
            "original_title": movie_info.get("original_title"),
            "release_date": movie_info.get("release_date"),
            "overview": movie_info.get("overview"),
            "local_poster_path": movie_info.get("local_poster_path"),
            "genres": movie_info.get("genres", []),
            "runtime": movie_info.get("runtime"),
            "vote_average": movie_info.get("vote_average"),
            "file_path": file_path,
            "date_added": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
        movies.append(new_movie)
        self.catalog["movies"] = movies
        self.save_catalog()
        return new_movie

    def update_movie(self, movie_id, updated_info):
        """Atualiza informações de um filme existente."""
        movies = self.catalog.get("movies", [])
        for i, movie in enumerate(movies):
            if movie.get("id") == movie_id:
                movies[i].update(updated_info)
                movies[i]["last_updated"] = datetime.now().isoformat()
                self.save_catalog()
                return movies[i]
        return None

    def delete_movie(self, movie_id):
        """Remove um filme do catálogo e apaga o poster local."""
        movies = self.catalog.get("movies", [])
        for i, movie in enumerate(movies):
            if movie.get("id") == movie_id:
                removed = movies.pop(i)
                self.catalog["movies"] = movies
                self.save_catalog()
                poster = removed.get("local_poster_path")
                if poster and os.path.exists(poster):
                    try:
                        os.remove(poster)
                    except Exception:
                        pass
                return True
        return False

    def is_video_file(self, file_path):
        """Verifica se o arquivo é um vídeo válido."""
        if not os.path.exists(file_path):
            return False
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('video/'):
            return True
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
        return os.path.splitext(file_path)[1].lower() in video_extensions
