import os
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFileDialog, QListWidget, QListWidgetItem,
                             QMessageBox, QProgressDialog, QApplication, QCheckBox)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from core.movie_fetcher import MovieFetcher
import re
import subprocess
from difflib import SequenceMatcher


# ──────────────────────────────────────────────────────────────────────────────
# Threads
# ──────────────────────────────────────────────────────────────────────────────

class BatchScanThread(QThread):
    progress_updated = pyqtSignal(int, int)
    movie_found = pyqtSignal(str, str)
    scan_completed = pyqtSignal(list)

    def __init__(self, root_folder, movie_manager):
        super().__init__()
        self.root_folder = root_folder
        self.movie_manager = movie_manager

    def run(self):
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        total_files = 0
        processed_files = 0
        video_files = []

        for root, dirs, files in os.walk(self.root_folder):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    total_files += 1

        for root, dirs, files in os.walk(self.root_folder):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    file_path = os.path.join(root, file)
                    processed_files += 1
                    self.progress_updated.emit(processed_files, total_files)
                    if self.is_movie_file(file_path):
                        clean_title = self.clean_movie_title(file)
                        video_files.append((clean_title, file_path))
                        self.movie_found.emit(clean_title, file_path)

        self.scan_completed.emit(video_files)

    def is_movie_file(self, file_path):
        try:
            try:
                subprocess.run(['ffprobe', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError:
                return True
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                return True
            return float(result.stdout.strip()) > 3600
        except Exception:
            return True

    def clean_movie_title(self, filename):
        name = os.path.splitext(filename)[0]
        name = name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        patterns = [
            r'\b\d{4}\b',
            r'\b(1080p|720p|480p|4K|UHD|HD|FHD)\b',
            r'\b(BluRay|BRRip|WEBRip|HDTV|DVDRip|WEB-DL|HDRIP|WEB |DL|REPACK|-|JefePsb|CAMPRip|SF|Acesse|ORIGINAL|Dublagem|BKS|by|GmV|Pirate|Filmes|The|LAPUMiaAFiLMES|COM|By|jmsmarcelo|COMANDO LA|LA|LapumiaFilmes|TorrentDosFilmes|SE|NET|)\b',
            r'\b(x264|x265|HEVC|XviD|h264|h265)\b',
            r'\b(AAC|AC3|DTS|MP3|FLAC|DDP5.1|DDP|DD5.1|ÁUDIO|AUDIO|EAC3|6CH|CH|TDF|DL)\b',
            r'\b(DUAL|DUBLADO|LEGENDADO|DUB|PT-BR|PT|BR|EN|ENG|PTBR)\b',
            r'\b(5.1|7.1|2.0)\b',
            r'\bwww\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            r'\b(EXTENDED|DIRECTORS.CUT|UNRATED|CAMPRip|Sem Cortes|JefePsb|REPACK|D4V1|D4VI|199991|REMASTERED|REMUX |SF|BLUDV|BY|LUAHARP|LuaHarper|JefPsB|LAPUMiA|CAMPRip|THEPIRATEFILMES|RICKSZ|COMANDOTORRENTS|WOLVERDONFILMES|NACIONAL|VERSAO|ESTENDIDA|STARCKFILMES|remasterizado|CAMPRip|VERSÃO|ToTTI9|jeffpsb|portugues|WWW|-)\b',
            r'\[.*?\]|\(.*?\)',
        ]
        for pattern in patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', name).strip()


class AutomaticMovieAddThread(QThread):
    progress_updated = pyqtSignal(int, int)
    movie_processed = pyqtSignal(str, bool, str)
    processing_completed = pyqtSignal()

    def __init__(self, movie_files, movie_manager, movie_fetcher):
        super().__init__()
        self.movie_files = movie_files
        self.movie_manager = movie_manager
        self.movie_fetcher = movie_fetcher
        self.catalog = self._load_catalog()

    def _load_catalog(self):
        catalog_path = os.path.join("data", "catalog.json")
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"movies": []}

    def run(self):
        total = len(self.movie_files)
        for index, (clean_title, file_path) in enumerate(self.movie_files):
            try:
                self.progress_updated.emit(index + 1, total)
                if self._movie_exists(file_path):
                    self.movie_processed.emit(clean_title, False, "Filme já existe no catálogo")
                    continue
                results = self.movie_fetcher.search_movie(clean_title)
                if not results:
                    alt = self._alternative_term(clean_title)
                    if alt:
                        results = self.movie_fetcher.search_movie(alt)
                if not results:
                    self.movie_processed.emit(clean_title, False, "Nenhum resultado encontrado")
                    continue
                best = self._best_match(clean_title, results)
                if not best:
                    self.movie_processed.emit(clean_title, False, "Nenhum resultado compatível")
                    continue
                details = self.movie_fetcher.get_movie_details(best['id'])
                if not details:
                    self.movie_processed.emit(clean_title, False, "Falha ao obter detalhes")
                    continue
                local_poster = None
                if details.get("poster_path"):
                    local_poster = self.movie_fetcher.download_poster(details["poster_path"], details["id"])
                info = self.movie_fetcher.extract_movie_info(details)
                info["local_poster_path"] = local_poster
                new_movie = self.movie_manager.add_movie(info, file_path)
                if new_movie:
                    self.movie_processed.emit(clean_title, True, new_movie['title'])
                else:
                    self.movie_processed.emit(clean_title, False, "Falha ao adicionar ao catálogo")
            except Exception as e:
                self.movie_processed.emit(clean_title, False, str(e))
        self.processing_completed.emit()

    def _movie_exists(self, file_path):
        return any(m.get("file_path") == file_path for m in self.catalog.get("movies", []))

    def _best_match(self, search_title, results):
        best, best_score = None, 0
        for movie in results:
            ratio = SequenceMatcher(None, search_title.lower(), movie.get("title", "").lower()).ratio()
            year_bonus = 0.2 if movie.get("release_date", "").split("-")[0] in search_title else 0
            score = ratio + year_bonus
            if score > best_score:
                best_score, best = score, movie
        return best if best_score >= 0.5 else None

    def _alternative_term(self, title):
        alt = re.sub(r'[:;]-.*$', '', title).strip()
        common = ['o','a','os','as','e','de','do','da','dos','das','em','no','na','nos','nas']
        words = alt.split()
        if len(words) > 2:
            filtered = [w for w in words if w.lower() not in common]
            if filtered:
                alt = ' '.join(filtered)
        return alt if alt != title else None


class TMDBSearchThread(QThread):
    search_completed = pyqtSignal(list)

    def __init__(self, fetcher, title):
        super().__init__()
        self.fetcher = fetcher
        self.title = title

    def run(self):
        self.search_completed.emit(self.fetcher.search_movie(self.title))


class MovieDetailsFetchThread(QThread):
    fetch_completed = pyqtSignal(dict)

    def __init__(self, fetcher, movie_id):
        super().__init__()
        self.fetcher = fetcher
        self.movie_id = movie_id

    def run(self):
        details = self.fetcher.get_movie_details(self.movie_id)
        if details:
            local_poster = None
            if details.get("poster_path"):
                local_poster = self.fetcher.download_poster(details["poster_path"], details["id"])
            info = self.fetcher.extract_movie_info(details)
            info["local_poster_path"] = local_poster
            self.fetch_completed.emit(info)
        else:
            self.fetch_completed.emit({})


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo principal
# ──────────────────────────────────────────────────────────────────────────────

class AddMovieDialog(QDialog):
    """
    Diálogo para adicionar ou editar um filme.

    Parâmetros
    ----------
    edit_movie : dict, opcional
        Se fornecido, o diálogo entra em modo edição:
        - Título muda para "Editar Filme"
        - A seção de seleção de arquivo fica oculta
        - O campo de busca é pré-preenchido com o título atual
        - A validação de duplicatas é ignorada
        - O botão de confirmar chama update_movie em vez de add_movie
    """

    def __init__(self, movie_manager, parent=None, edit_movie=None):
        super().__init__(parent)
        self.movie_manager = movie_manager
        self.movie_fetcher = MovieFetcher()
        self.edit_movie = edit_movie                      # None = modo adicionar
        self.edit_mode = edit_movie is not None
        self.selected_file_path = edit_movie.get("file_path", "") if edit_movie else ""
        self.selected_movie_info = None
        self.found_movies = []
        self.catalog = self._load_catalog()
        self.init_ui()

        # Pré-preenche o campo de busca com o título atual
        if self.edit_mode:
            self.search_edit.setText(edit_movie.get("title", ""))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_catalog(self):
        catalog_path = os.path.join("data", "catalog.json")
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"movies": []}

    def _movie_exists(self, file_path):
        return any(m.get("file_path") == file_path for m in self.catalog.get("movies", []))

    def _alternative_term(self, title):
        alt = re.sub(r'[:;]-.*$', '', title).strip()
        common = ['o','a','os','as','e','de','do','da','dos','das','em','no','na','nos','nas']
        words = alt.split()
        if len(words) > 2:
            filtered = [w for w in words if w.lower() not in common]
            if filtered:
                alt = ' '.join(filtered)
        return alt if alt != title else None

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def init_ui(self):
        title_text = "Editar Filme" if self.edit_mode else "Adicionar Filme"
        self.setWindowTitle(title_text)
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # ── Seção 1: arquivo (oculta em modo edição) ─────────────────
        self.file_section_widget = self._build_file_section()
        layout.addWidget(self.file_section_widget)
        if self.edit_mode:
            self.file_section_widget.hide()

        # Separador
        sep1 = QLabel()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background-color: #333;")
        layout.addWidget(sep1)
        if self.edit_mode:
            sep1.hide()

        # ── Seção 2: busca ───────────────────────────────────────────
        layout.addLayout(self._build_search_section())

        # Separador
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #333;")
        layout.addWidget(sep2)

        # ── Log ──────────────────────────────────────────────────────
        log_layout = QVBoxLayout()
        log_label = QLabel("Log de Processamento")
        log_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        log_layout.addWidget(log_label)
        self.log_list = QListWidget()
        self.log_list.setMaximumHeight(100)
        log_layout.addWidget(self.log_list)
        layout.addLayout(log_layout)

        # ── Botões ───────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        confirm_label = "Atualizar Filme" if self.edit_mode else "Adicionar Filme"
        self.add_button = QPushButton(confirm_label)
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self.confirm_movie)
        btn_layout.addWidget(self.add_button)
        layout.addLayout(btn_layout)

        self._apply_style()

    def _build_file_section(self):
        widget = QDialog()  # Usamos QDialog como container apenas para agrupar
        # Na prática queremos um QWidget simples
        from PyQt5.QtWidgets import QWidget as _W
        w = _W()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Passo 1: Selecione o arquivo de vídeo ou uma pasta com filmes")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        v.addWidget(label)

        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Selecione o arquivo de vídeo ou pasta...")
        file_row.addWidget(self.file_path_edit)

        browse_btn = QPushButton("Procurar Arquivo")
        browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(browse_btn)

        browse_folder_btn = QPushButton("Procurar Pasta")
        browse_folder_btn.clicked.connect(self.browse_folder)
        file_row.addWidget(browse_folder_btn)
        v.addLayout(file_row)

        auto_row = QHBoxLayout()
        self.auto_process_checkbox = QCheckBox("Processar filmes automaticamente")
        self.auto_process_checkbox.setChecked(True)
        auto_row.addWidget(self.auto_process_checkbox)
        auto_row.addStretch()
        v.addLayout(auto_row)

        skip_row = QHBoxLayout()
        self.skip_duplicates_checkbox = QCheckBox("Pular filmes já existentes no catálogo")
        self.skip_duplicates_checkbox.setChecked(True)
        skip_row.addWidget(self.skip_duplicates_checkbox)
        skip_row.addStretch()
        v.addLayout(skip_row)

        return w

    def _build_search_section(self):
        search_section = QVBoxLayout()

        step_label = "Buscar novas informações do filme:" if self.edit_mode else "Passo 2: Buscar informações do filme"
        search_label = QLabel(step_label)
        search_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        search_section.addWidget(search_label)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Digite o título do filme...")
        search_row.addWidget(self.search_edit)
        search_btn = QPushButton("Buscar")
        search_btn.clicked.connect(self.search_movie)
        search_row.addWidget(search_btn)
        search_section.addLayout(search_row)

        results_layout = QHBoxLayout()

        self.results_list = QListWidget()
        self.results_list.setStyleSheet("font-size: 14px;")
        self.results_list.itemClicked.connect(self.select_movie)
        results_layout.addWidget(self.results_list, 2)

        details_layout = QVBoxLayout()
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setFixedSize(200, 300)
        self.poster_label.setStyleSheet("background-color: #333;")
        details_layout.addWidget(self.poster_label)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignCenter)
        details_layout.addWidget(self.title_label)

        self.year_label = QLabel()
        self.year_label.setAlignment(Qt.AlignCenter)
        details_layout.addWidget(self.year_label)

        self.overview_label = QLabel()
        self.overview_label.setWordWrap(True)
        self.overview_label.setAlignment(Qt.AlignTop)
        details_layout.addWidget(self.overview_label)
        details_layout.addStretch()

        results_layout.addLayout(details_layout, 1)
        search_section.addLayout(results_layout)
        return search_section

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #141414; color: white; }
            QWidget { background-color: #141414; color: white; }
            QLabel { color: white; }
            QLineEdit {
                background-color: #333; color: white;
                border: 1px solid #555; padding: 5px; border-radius: 3px;
            }
            QPushButton {
                background-color: #E50914; color: white;
                border: none; padding: 8px 16px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #F40D12; }
            QPushButton:disabled { background-color: #5E5E5E; }
            QListWidget {
                background-color: #222; color: white;
                border: 1px solid #555; border-radius: 3px;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #E50914; }
            QCheckBox { color: white; }
            QCheckBox::indicator {
                width: 15px; height: 15px;
                border: 1px solid #555; background-color: #333; border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #E50914; border: 1px solid #E50914;
            }
        """)

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------
    def add_log_message(self, message, success=True):
        item = QListWidgetItem(message)
        item.setForeground(Qt.green if success else Qt.red)
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    # ------------------------------------------------------------------
    # Seleção de arquivo / pasta (modo adicionar)
    # ------------------------------------------------------------------
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Arquivo de Vídeo", "",
            "Arquivos de Vídeo (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm);;Todos (*.*)"
        )
        if not file_path:
            return
        if not self.movie_manager.is_video_file(file_path):
            QMessageBox.warning(self, "Arquivo Inválido", "O arquivo não parece ser um vídeo válido.")
            return
        self.selected_file_path = file_path
        self.file_path_edit.setText(file_path)

        if self.skip_duplicates_checkbox.isChecked() and self._movie_exists(file_path):
            QMessageBox.information(self, "Filme já existe", "Este filme já existe no catálogo.")
            return

        filename = os.path.basename(file_path)
        scan_thread = BatchScanThread("", self.movie_manager)
        clean_title = scan_thread.clean_movie_title(filename)
        self.search_edit.setText(clean_title.strip())
        self.search_movie()

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta com Filmes", "")
        if folder_path:
            self.file_path_edit.setText(folder_path)
            self._scan_folder(folder_path)

    def _scan_folder(self, folder_path):
        self.scan_progress = QProgressDialog("Escaneando pasta por filmes...", "Cancelar", 0, 0, self)
        self.scan_progress.setWindowTitle("Escaneando")
        self.scan_progress.setWindowModality(Qt.WindowModal)
        self.scan_progress.setMinimumDuration(0)
        self.scan_progress.show()
        QApplication.processEvents()

        self.log_list.clear()
        self.add_log_message("Iniciando escaneamento da pasta...")

        self.scan_thread = BatchScanThread(folder_path, self.movie_manager)
        self.scan_thread.progress_updated.connect(self._on_scan_progress)
        self.scan_thread.movie_found.connect(lambda t, p: self.add_log_message(f"Encontrado: {t}"))
        self.scan_thread.scan_completed.connect(self._on_scan_completed)
        self.scan_thread.start()

    def _on_scan_progress(self, current, total):
        if self.scan_progress.wasCanceled():
            self.scan_thread.terminate()
            return
        self.scan_progress.setMaximum(total)
        self.scan_progress.setValue(current)
        self.scan_progress.setLabelText(f"Escaneando... ({current}/{total})")

    def _on_scan_completed(self, found_movies):
        self.found_movies = []
        if self.skip_duplicates_checkbox.isChecked():
            for title, fp in found_movies:
                if not self._movie_exists(fp):
                    self.found_movies.append((title, fp))
                else:
                    self.add_log_message(f"Pulando duplicado: {title}", success=False)
        else:
            self.found_movies = found_movies

        self.scan_progress.close()

        if not self.found_movies:
            QMessageBox.information(self, "Escaneamento Concluído", "Nenhum filme novo encontrado.")
            return

        QMessageBox.information(self, "Escaneamento Concluído",
                                f"Foram encontrados {len(self.found_movies)} novos filmes.")
        self.add_log_message(f"Escaneamento concluído: {len(self.found_movies)} filmes")

        if self.auto_process_checkbox.isChecked():
            self._process_found_movies()

    def _process_found_movies(self):
        if not self.found_movies:
            return
        self.processing_progress = QProgressDialog(
            "Processando filmes...", "Cancelar", 0, len(self.found_movies), self)
        self.processing_progress.setWindowTitle("Adicionando Filmes")
        self.processing_progress.setWindowModality(Qt.WindowModal)
        self.processing_progress.setMinimumDuration(0)
        self.processing_progress.show()
        QApplication.processEvents()

        self.auto_add_thread = AutomaticMovieAddThread(
            self.found_movies, self.movie_manager, self.movie_fetcher)
        self.auto_add_thread.progress_updated.connect(self._on_processing_progress)
        self.auto_add_thread.movie_processed.connect(
            lambda t, ok, msg: self.add_log_message(f"{'OK' if ok else 'Falha'}: {t} - {msg}", ok))
        self.auto_add_thread.processing_completed.connect(self._on_processing_completed)
        self.auto_add_thread.start()

    def _on_processing_progress(self, current, total):
        if self.processing_progress.wasCanceled():
            self.auto_add_thread.terminate()
            return
        self.processing_progress.setValue(current)
        self.processing_progress.setLabelText(f"Processando... ({current}/{total})")

    def _on_processing_completed(self):
        self.processing_progress.close()
        QMessageBox.information(self, "Concluído",
                                "Filmes processados e adicionados ao catálogo.")
        self.add_log_message("Processamento concluído")
        self.accept()

    # ------------------------------------------------------------------
    # Busca na API
    # ------------------------------------------------------------------
    def search_movie(self):
        search_term = self.search_edit.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Campo Vazio", "Digite um título para buscar.")
            return

        progress = QProgressDialog("Buscando filmes...", "Cancelar", 0, 0, self)
        progress.setWindowTitle("Aguarde")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()

        self.search_thread = TMDBSearchThread(self.movie_fetcher, search_term)
        self.search_thread.search_completed.connect(self._on_search_results)
        self.search_thread.finished.connect(progress.close)
        self.search_thread.start()

    def _on_search_results(self, results):
        self.results_list.clear()
        if not results:
            alt = self._alternative_term(self.search_edit.text().strip())
            if alt:
                progress = QProgressDialog(f"Tentando: {alt}", "Cancelar", 0, 0, self)
                progress.setWindowTitle("Aguarde")
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
                QApplication.processEvents()
                self.alt_search_thread = TMDBSearchThread(self.movie_fetcher, alt)
                self.alt_search_thread.search_completed.connect(self._on_alt_search_results)
                self.alt_search_thread.finished.connect(progress.close)
                self.alt_search_thread.start()
            else:
                self.results_list.addItem("Nenhum resultado encontrado.")
            return

        for movie in results:
            title = movie.get("title", "Sem título")
            year = ""
            rd = movie.get("release_date", "")
            if rd:
                try:
                    year = f" ({rd.split('-')[0]})"
                except Exception:
                    pass
            item = QListWidgetItem(f"{title}{year}")
            item.setData(Qt.UserRole, movie)
            self.results_list.addItem(item)

        if len(results) == 1:
            item = self.results_list.item(0)
            self.results_list.setCurrentItem(item)
            self.select_movie(item)

    def _on_alt_search_results(self, results):
        if not results:
            self.results_list.addItem("Nenhum resultado encontrado.")
            return
        for movie in results:
            title = movie.get("title", "Sem título")
            rd = movie.get("release_date", "")
            year = f" ({rd.split('-')[0]})" if rd else ""
            item = QListWidgetItem(f"{title}{year} [busca alternativa]")
            item.setData(Qt.UserRole, movie)
            self.results_list.addItem(item)

    def select_movie(self, item):
        movie_data = item.data(Qt.UserRole)
        if not movie_data:
            return

        progress = QProgressDialog("Obtendo detalhes do filme...", "Cancelar", 0, 0, self)
        progress.setWindowTitle("Aguarde")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()

        self.details_thread = MovieDetailsFetchThread(self.movie_fetcher, movie_data["id"])
        self.details_thread.fetch_completed.connect(self._show_movie_details)
        self.details_thread.finished.connect(progress.close)
        self.details_thread.start()

    def _show_movie_details(self, movie_info):
        if not movie_info:
            QMessageBox.warning(self, "Erro", "Não foi possível obter detalhes do filme.")
            return

        self.selected_movie_info = movie_info

        poster_path = movie_info.get("local_poster_path")
        if poster_path and os.path.exists(poster_path):
            pixmap = QPixmap(poster_path).scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.poster_label.setPixmap(pixmap)
        else:
            self.poster_label.setText("Sem Poster")
            self.poster_label.setAlignment(Qt.AlignCenter)

        self.title_label.setText(movie_info.get("title", ""))
        rd = movie_info.get("release_date", "")
        self.year_label.setText(rd.split("-")[0] if rd else "")
        self.overview_label.setText(movie_info.get("overview", "Sinopse não disponível."))

        # Habilita o botão:
        # - modo edição: sempre (o arquivo já está definido)
        # - modo adicionar: só se um arquivo foi selecionado
        self.add_button.setEnabled(bool(self.selected_file_path))

    # ------------------------------------------------------------------
    # Confirmar (adicionar ou atualizar)
    # ------------------------------------------------------------------
    def confirm_movie(self):
        if not self.selected_file_path or not self.selected_movie_info:
            QMessageBox.warning(self, "Informações Incompletas",
                                "Selecione um arquivo e um filme para continuar.")
            return

        if self.edit_mode:
            # Modo edição: atualiza apenas capa e informações, mantém file_path e id
            updated_info = {
                "tmdb_id": self.selected_movie_info.get("id"),
                "title": self.selected_movie_info.get("title"),
                "original_title": self.selected_movie_info.get("original_title"),
                "release_date": self.selected_movie_info.get("release_date"),
                "overview": self.selected_movie_info.get("overview"),
                "local_poster_path": self.selected_movie_info.get("local_poster_path"),
                "genres": self.selected_movie_info.get("genres", []),
                "runtime": self.selected_movie_info.get("runtime"),
                "vote_average": self.selected_movie_info.get("vote_average"),
            }
            result = self.movie_manager.update_movie(self.edit_movie["id"], updated_info)
            if result:
                QMessageBox.information(self, "Sucesso",
                                        f"Filme '{result['title']}' atualizado com sucesso!")
                self.accept()
            else:
                QMessageBox.critical(self, "Erro", "Não foi possível atualizar o filme.")
        else:
            # Modo adicionar normal
            if self.skip_duplicates_checkbox.isChecked() and self._movie_exists(self.selected_file_path):
                QMessageBox.information(self, "Filme já existe", "Este filme já existe no catálogo.")
                return
            new_movie = self.movie_manager.add_movie(self.selected_movie_info, self.selected_file_path)
            if new_movie:
                QMessageBox.information(self, "Sucesso",
                                        f"Filme '{new_movie['title']}' adicionado com sucesso!")
                self.add_log_message(f"Adicionado: {new_movie['title']}")
                self.accept()
            else:
                QMessageBox.critical(self, "Erro", "Não foi possível adicionar o filme.")
