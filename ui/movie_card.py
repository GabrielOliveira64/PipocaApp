import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QFrame, QApplication)
from PyQt5.QtGui import QPixmap, QCursor, QPainter, QPainterPath
from PyQt5.QtCore import Qt, pyqtSignal
from ui.movie_info_page import MovieInfoOverlay


class RoundedLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.radius = 8

    def paintEvent(self, event):
        if not self.pixmap():
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, self.pixmap())


class MovieCard(QWidget):
    """Widget para exibir um cartão de filme com efeito hover."""

    edit_requested = pyqtSignal(dict)  # Sinal emitido ao clicar em editar

    def __init__(self, movie, parent=None):
        super().__init__(parent)
        self.movie = movie
        self.setMouseTracking(True)
        self.hovered = False
        self._overlay = None
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # Container principal
        self.container = QFrame()
        self.container.setObjectName("movieCard")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # Poster
        self.poster_frame = QFrame()
        self.poster_frame.setObjectName("posterFrame")
        self.poster_layout = QVBoxLayout(self.poster_frame)
        self.poster_layout.setContentsMargins(0, 0, 0, 0)
        self.poster_layout.setSpacing(0)

        self.poster_label = RoundedLabel()
        poster_path = self.movie.get("local_poster_path")
        if poster_path and os.path.exists(poster_path):
            pixmap = QPixmap(poster_path)
            pixmap = pixmap.scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.poster_label.setPixmap(pixmap)
        else:
            self.poster_label.setText("")
            self.poster_label.setStyleSheet("background-color: #333;")
            self.poster_label.setFixedSize(200, 300)

        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_layout.addWidget(self.poster_label)
        self.container_layout.addWidget(self.poster_frame)

        # ── Overlay (aparece no hover) ───────────────────────────────
        self.overlay = QWidget(self.poster_frame)
        self.overlay.setObjectName("overlay")
        self.overlay.setFixedSize(200, 300)
        self.overlay.setStyleSheet("""
            QWidget#overlay {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 8px;
            }
        """)

        self.overlay_layout = QVBoxLayout(self.overlay)
        self.overlay_layout.setContentsMargins(0, 0, 0, 0)
        self.overlay_layout.setSpacing(0)

        # Botão editar — canto superior direito
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 8, 8, 0)
        top_row.addStretch()

        self.edit_btn = QPushButton("✏")
        self.edit_btn.setObjectName("editButton")
        self.edit_btn.setFixedSize(30, 30)
        self.edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.edit_btn.setToolTip("Editar informações do filme")
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        top_row.addWidget(self.edit_btn)

        self.overlay_layout.addLayout(top_row)

        # Botões Play + Info — centro
        self.overlay_layout.addStretch()

        button_container = QHBoxLayout()
        button_container.setSpacing(10)
        button_container.setContentsMargins(0, 0, 0, 0)
        button_container.setAlignment(Qt.AlignCenter)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("playButton")
        self.play_btn.setFixedSize(50, 50)
        self.play_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.play_btn.clicked.connect(self.play_movie)
        button_container.addWidget(self.play_btn)

        self.info_btn = QPushButton("i")
        self.info_btn.setObjectName("infoButton")
        self.info_btn.setFixedSize(50, 50)
        self.info_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.info_btn.clicked.connect(self.show_info)
        button_container.addWidget(self.info_btn)

        self.overlay_layout.addLayout(button_container)
        self.overlay_layout.addStretch()

        self.overlay.hide()

        self.layout.addWidget(self.container)

        self.setStyleSheet("""
            QFrame#movieCard {
                background-color: transparent;
                border: none;
            }
            QFrame#posterFrame {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
            QLabel {
                border-radius: 8px;
            }
            QPushButton#playButton {
                background-color: #E50914;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 25px;
            }
            QPushButton#playButton:hover {
                background-color: #F40D12;
            }
            QPushButton#infoButton {
                background-color: #333;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid white;
                border-radius: 25px;
            }
            QPushButton#infoButton:hover {
                background-color: #555;
            }
            QPushButton#editButton {
                background-color: rgba(30, 30, 30, 0.85);
                color: #ddd;
                font-size: 13px;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 15px;
            }
            QPushButton#editButton:hover {
                background-color: #E50914;
                color: white;
                border: 1px solid #E50914;
            }
        """)
        self.setFixedWidth(200)
        self.setFixedHeight(304)

    # ── Hover ────────────────────────────────────────────────────────
    def enterEvent(self, event):
        self.hovered = True
        self.overlay.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.overlay.hide()
        super().leaveEvent(event)

    # ── Ações ────────────────────────────────────────────────────────
    def play_movie(self):
        file_path = self.movie.get("file_path")
        if file_path and os.path.exists(file_path):
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                os.system(f'open "{file_path}"')
            else:
                os.system(f'xdg-open "{file_path}"')
        else:
            QMessageBox.warning(self, "Erro", "Arquivo não encontrado!")

    def show_info(self):
        """Abre o overlay de informações dentro da janela principal."""
        main_window = self.window()
        central = main_window.centralWidget() if main_window else self

        if self._overlay is not None:
            self._overlay.hide()
            self._overlay.deleteLater()

        self._overlay = MovieInfoOverlay(self.movie, parent=central)
        self._overlay.show_overlay()

    def open_edit_dialog(self):
        """Abre o diálogo de edição pré-preenchido com os dados do filme."""
        from ui.add_movie_dialog import AddMovieDialog

        main_window = self.window()
        dialog = AddMovieDialog(
            movie_manager=self._get_movie_manager(),
            parent=main_window,
            edit_movie=self.movie      # <- passa o filme para modo edição
        )
        if dialog.exec_():
            # Atualiza os dados locais do card e recarrega o poster
            updated = self._get_movie_manager().get_movie_by_id(self.movie["id"])
            if updated:
                self.movie = updated
                poster_path = updated.get("local_poster_path")
                if poster_path and os.path.exists(poster_path):
                    pixmap = QPixmap(poster_path).scaled(
                        200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    self.poster_label.setPixmap(pixmap)

    def _get_movie_manager(self):
        """Retorna a instância de MovieManager da janela principal."""
        from core.movie_manager import MovieManager
        main_window = self.window()
        if hasattr(main_window, "movie_manager"):
            return main_window.movie_manager
        return MovieManager()
