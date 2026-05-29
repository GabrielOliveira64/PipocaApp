import os
import sys
from utils import resource_path
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QScrollArea, QGridLayout, QPushButton, QMessageBox, QAction, 
                            QMenuBar, QMenu, QFileDialog, QInputDialog, QFrame, QDialog,
                            QDesktopWidget, QSizePolicy, QApplication)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPalette, QColor, QCursor
from PyQt5.QtCore import Qt, QSize, QEvent, pyqtSignal, QPoint, QTimer
import webbrowser
from core.movie_manager import MovieManager
from PyQt5.QtWidgets import (QCheckBox, QLineEdit, QToolButton, QSizePolicy, 
                            QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLabel,
                            QScrollArea, QGroupBox)
from PyQt5.QtSvg import QSvgWidget
from ui.movie_card import MovieCard
from ui.add_movie_dialog import AddMovieDialog
from ui.delete_movie_dialog import DeleteMovieDialog
from ui.splash_screen import SplashScreen
from ui.sidebar import Sidebar
import json

def get_version():
    try:
        version_path = os.path.join("./", "version.json")
        if os.path.exists(version_path):
            with open(version_path, 'r') as f:
                version_data = json.load(f)
                return version_data.get("version", "Desconhecida")
        return "Desconhecida"
    except Exception:
        return "Desconhecida"

class MainWindow(QMainWindow):
    """Janela principal do aplicativo."""
    
    def __init__(self):
        super().__init__()
        self.movie_manager = MovieManager()
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.load_movies)
        self.menu_open = False
        self.menu_width = 250
        self.selected_genres = []
        self.search_term = ""
        self.init_ui()
        self.load_movies()
        self.showFullScreen()  # Restaurado para comportamento original
    
    def init_ui(self):
        self.setWindowTitle("Pipoca+")
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #141414;
                color: white;
                border: none;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
            }
            QMenuBar::item:selected {
                background-color: #333;
                border-radius: 4px;
            }
            QMenu {
                background-color: #1f1f1f;
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 25px 6px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #E50914;
            }
        """)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(0)  # Inicialmente fechada
        self.sidebar.searchChanged.connect(self.filter_movies)
        self.sidebar.genreFilterChanged.connect(self.filter_movies)
        
        file_menu = menubar.addMenu("Arquivo")
        add_action = QAction("Adicionar Filme", self)
        add_action.triggered.connect(self.add_movie)
        file_menu.addAction(add_action)
        refresh_action = QAction("Atualizar Biblioteca", self)
        refresh_action.triggered.connect(self.load_movies)
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        toggle_fullscreen_action = QAction("Alternar Tela Cheia", self)
        toggle_fullscreen_action.setShortcut("F11")
        toggle_fullscreen_action.triggered.connect(self.toggle_fullscreen)
        file_menu.addAction(toggle_fullscreen_action)
        file_menu.addSeparator()
        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = menubar.addMenu("Visualização")
        sort_menu = QMenu("Ordenar Por", self)
        view_menu.addMenu(sort_menu)
        sort_by_title = QAction("Título", self)
        sort_by_title.triggered.connect(lambda: self.sort_movies("title"))
        sort_menu.addAction(sort_by_title)
        sort_by_date_added = QAction("Data de Adição", self)
        sort_by_date_added.triggered.connect(lambda: self.sort_movies("date_added"))
        sort_menu.addAction(sort_by_date_added)
        sort_by_rating = QAction("Avaliação", self)
        sort_by_rating.triggered.connect(lambda: self.sort_movies("vote_average"))
        sort_menu.addAction(sort_by_rating)
        sort_by_year = QAction("Ano de Lançamento", self)
        sort_by_year.triggered.connect(lambda: self.sort_movies("release_date"))
        sort_menu.addAction(sort_by_year)
        about_menu = menubar.addMenu("Sobre")
        app_info_action = QAction("Informações do App", self)
        app_info_action.triggered.connect(self.show_about_info)
        about_menu.addAction(app_info_action)
        
        self.main_layout.addWidget(self.sidebar)
        self.content_container = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_container.setLayout(content_layout)
        header_layout = QHBoxLayout()
        self.menu_button = QToolButton()
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setFixedSize(36, 36)
        self.menu_button.clicked.connect(self.toggle_menu)
        self.menu_svg = QSvgWidget(resource_path("ui/icons/menu_bars_close.svg"))
        self.menu_svg.setFixedSize(20, 20)
        menu_button_layout = QVBoxLayout(self.menu_button)
        menu_button_layout.setContentsMargins(8, 8, 8, 8)
        menu_button_layout.addWidget(self.menu_svg)
        header_layout.addWidget(self.menu_button)
        title_label = QLabel("Minha Biblioteca")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.add_button = QPushButton("+ Filme ")
        self.add_button.setObjectName("addButton")
        self.add_button.setFixedSize(100, 36)
        self.add_button.clicked.connect(self.add_movie)
        header_layout.addWidget(self.add_button)
        self.delete_button = QPushButton("- Filme")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setFixedSize(100, 36)
        self.delete_button.setStyleSheet("""
            QPushButton#deleteButton {
                background-color: #333;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#deleteButton:hover {
                background-color: #555;
            }
        """)
        self.delete_button.clicked.connect(self.delete_movie)
        header_layout.addWidget(self.delete_button)
        content_layout.addLayout(header_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(scroll_content)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setHorizontalSpacing(4)
        self.grid_layout.setVerticalSpacing(4)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setWidget(scroll_content)
        content_layout.addWidget(scroll_area)
        self.main_layout.addWidget(self.content_container)
        self.shortcut_escape = QAction("Sair da Tela Cheia", self)
        self.shortcut_escape.setShortcut("Esc")
        self.shortcut_escape.triggered.connect(self.exit_fullscreen)
        self.addAction(self.shortcut_escape)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f0f;
            }
            QWidget {
                background-color: #0f0f0f;
                color: white;
            }
            QPushButton#addButton {
                background-color: #E50914;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#addButton:hover {
                background-color: #F40D12;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: #1a1a1a;
            }
            QScrollBar:horizontal {
                background: #1a1a1a;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #444;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: #1a1a1a;
            }
        """)
    
    def delete_movie(self):
        dialog = DeleteMovieDialog(self.movie_manager, self)
        dialog.movie_deleted.connect(self.load_movies)
        dialog.exec_()
    
    def load_movies(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.grid_layout.setSpacing(0)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        movies = self.movie_manager.get_all_movies()
        self.sidebar.populate_genres(movies)
        filtered_movies = self.apply_filters(movies)
        if not filtered_movies:
            empty_message = "Sua biblioteca está vazia. Adicione filmes usando o botão acima."
            if movies and (self.search_term or self.selected_genres):
                empty_message = "Nenhum filme encontrado com os critérios selecionados."
            empty_label = QLabel(empty_message)
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #888; font-size: 16px; padding: 40px;")
            self.grid_layout.addWidget(empty_label, 0, 0)
            return
        available_width = self.content_container.width() - 20
        if self.menu_open:
            available_width -= self.menu_width
        card_width = 200
        card_margin = 0
        cols_with_margin = max(1, int(available_width / (card_width + 2*card_margin)))
        row, col = 0, 0
        unique_movies = {}
        for movie in filtered_movies:
            movie_key = f"{movie.get('id', '')}-{movie.get('file_path', '')}"
            if movie_key in unique_movies:
                continue
            unique_movies[movie_key] = True
            movie_card = MovieCard(movie)
            movie_card.setFixedSize(card_width, movie_card.sizeHint().height())
            self.grid_layout.addWidget(movie_card, row, col)
            col += 1
            if col >= cols_with_margin:
                col = 0
                row += 1
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_layout.addWidget(spacer, row + 1, 0, 1, cols_with_margin)

    def toggle_menu(self):
        if self.menu_open:
            self.menu_open = False
            self.sidebar.setFixedWidth(0)
            self.menu_svg.load(resource_path("ui/icons/menu_bars_close.svg"))
        else:
            self.menu_open = True
            self.sidebar.setFixedWidth(self.menu_width)
            self.menu_svg.load(resource_path("ui/icons/menu_bars_open.svg"))
        QTimer.singleShot(50, self.force_layout_update)
    
    def filter_movies(self):
        was_menu_open = self.menu_open
        QTimer.singleShot(50, lambda: self.safe_force_layout_update(was_menu_open))

    def force_layout_update(self):
        self.grid_layout.setSpacing(0)
        self.grid_layout.setHorizontalSpacing(0)
        self.grid_layout.setVerticalSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.load_movies()
        self.content_container.update()
        QApplication.processEvents()

    def safe_force_layout_update(self, should_keep_menu_open):
        self.grid_layout.setSpacing(0)
        self.grid_layout.setHorizontalSpacing(0)
        self.grid_layout.setVerticalSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.load_movies()
        self.content_container.update()
        QApplication.processEvents()
        if should_keep_menu_open and not self.menu_open:
            self.menu_open = True
            self.sidebar.setFixedWidth(self.menu_width)
            self.menu_svg.load(resource_path("ui/icons/menu_bars_open.svg"))
    
    def apply_filters(self, movies):
        filtered_movies = []
        search_term = self.sidebar.get_search_term()
        selected_genres = self.sidebar.get_selected_genres()
        
        for movie in movies:
            match_search = True
            if search_term:
                title = movie.get("title", "").lower()
                original_title = movie.get("original_title", "").lower()
                overview = movie.get("overview", "").lower()
                match_search = (search_term in title or 
                              search_term in original_title or 
                              search_term in overview)
            
            match_genre = True
            if selected_genres:
                movie_genres = movie.get("genres", [])
                match_genre = any(genre in movie_genres for genre in selected_genres)
            
            if match_search and match_genre:
                filtered_movies.append(movie)
        
        return filtered_movies
    
    def add_movie(self):
        dialog = AddMovieDialog(self.movie_manager, self)
        if dialog.exec_():
            self.load_movies()
    
    def sort_movies(self, sort_key):
        movies = self.movie_manager.get_all_movies()
        if sort_key == "title":
            sorted_movies = sorted(movies, key=lambda x: x.get("title", "").lower())
        elif sort_key == "date_added":
            sorted_movies = sorted(movies, key=lambda x: x.get("date_added", ""), reverse=True)
        elif sort_key == "vote_average":
            sorted_movies = sorted(
                movies, 
                key=lambda x: float(x.get("vote_average", 0)) if x.get("vote_average") not in (None, "") else 0, 
                reverse=True
            )
        elif sort_key == "release_date":
            sorted_movies = sorted(movies, key=lambda x: x.get("release_date", ""), reverse=True)
        else:
            return
        self.movie_manager.catalog["movies"] = sorted_movies
        self.movie_manager.save_catalog()
        self.load_movies()
    
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            
    def show_about_info(self):
        version = get_version()
        QMessageBox.about(self, 
                        "Sobre Pipoca+", 
                        f"<h2>Pipoca+</h2>"
                        f"<p>Versão: {version}</p>"
                        f"<p>Desenvolvido por: GabrielOliveira64</p>"
                        f"<p>Um gerenciador de filmes para sua coleção pessoal.</p>")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.stop()
        self.resize_timer.start(200)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
