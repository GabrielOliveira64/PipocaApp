import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea,
                             QGraphicsOpacityEffect, QGraphicsBlurEffect,
                             QApplication, QMessageBox)
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect


class MovieInfoOverlay(QWidget):
    """Overlay modal com fundo embaçado, exibido dentro da janela principal."""

    def __init__(self, movie, parent=None):
        super().__init__(parent)
        self.movie = movie
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setObjectName("infoOverlay")

        if parent:
            self.resize(parent.size())

        # Captura o fundo ANTES de se tornar visível e aplica blur
        self._bg_pixmap = self._capture_blurred_background()

        self.init_ui()

    # ------------------------------------------------------------------
    # Fundo embaçado
    # ------------------------------------------------------------------
    def _capture_blurred_background(self):
        """Captura um screenshot do widget pai e aplica blur."""
        parent = self.parent()
        if parent is None:
            return None

        # Renderiza o pai num QPixmap
        size = parent.size()
        raw = QPixmap(size)
        raw.fill(Qt.transparent)
        parent.render(raw)

        # Aplica blur usando QImage + convolução manual (compatível com PyQt5)
        # Usamos um widget temporário oculto com QGraphicsBlurEffect
        blur_widget = QLabel()
        blur_widget.setPixmap(raw)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(18)
        blur_widget.setGraphicsEffect(effect)
        blur_widget.resize(size)

        blurred = QPixmap(size)
        blurred.fill(Qt.transparent)
        painter = QPainter(blurred)
        blur_widget.render(painter)
        painter.end()

        return blurred

    # ------------------------------------------------------------------
    # paintEvent — desenha o fundo embaçado + escurecimento
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        if self._bg_pixmap:
            painter.drawPixmap(0, 0, self._bg_pixmap)
        # Camada escura por cima do blur
        painter.fillRect(self.rect(), Qt.black if not self._bg_pixmap
                         else __import__('PyQt5.QtGui', fromlist=['QColor']).QColor(0, 0, 0, 140))
        painter.end()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#infoOverlay { background: transparent; }")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignCenter)

        # ── Card central ────────────────────────────────────────────
        self.card = QFrame()
        self.card.setObjectName("infoCard")
        self.card.setFixedSize(700, 460)
        self.card.setStyleSheet("""
            QFrame#infoCard {
                background-color: #1a1a1a;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.25);
            }
        """)

        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Poster ──────────────────────────────────────────────────
        poster_container = QFrame()
        poster_container.setFixedWidth(200)
        poster_container.setStyleSheet("""
            QFrame {
                background-color: #111;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        poster_layout = QVBoxLayout(poster_container)
        poster_layout.setContentsMargins(0, 0, 0, 0)
        poster_layout.setAlignment(Qt.AlignCenter)

        poster_label = QLabel()
        poster_label.setFixedSize(200, 460)
        poster_label.setAlignment(Qt.AlignCenter)
        poster_path = self.movie.get("local_poster_path")
        if poster_path and os.path.exists(poster_path):
            pixmap = QPixmap(poster_path).scaled(
                200, 460, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            pixmap = pixmap.copy(
                max(0, (pixmap.width() - 200) // 2),
                max(0, (pixmap.height() - 460) // 2),
                200, 460
            )
            poster_label.setPixmap(pixmap)
        else:
            poster_label.setText("Sem\nImagem")
            poster_label.setStyleSheet("color: #666; font-size: 13px;")

        poster_layout.addWidget(poster_label)
        card_layout.addWidget(poster_container)

        # ── Informações ──────────────────────────────────────────────
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(24, 18, 20, 18)
        info_layout.setSpacing(8)

        # Botão fechar (X)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #aaa;
                border: none;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E50914;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.close_overlay)
        close_row.addWidget(close_btn)
        info_layout.addLayout(close_row)

        # Título
        title = self.movie.get("title", "Sem Título")
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        info_layout.addWidget(title_label)

        # Título original
        original_title = self.movie.get("original_title", "")
        if original_title and original_title != title:
            orig_label = QLabel(f"Título original: {original_title}")
            orig_label.setWordWrap(True)
            orig_label.setStyleSheet("font-size: 13px; color: #aaa;")
            info_layout.addWidget(orig_label)

        # Data · Duração · Avaliação
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        release_date = self.movie.get("release_date", "")
        if release_date:
            date_label = QLabel(f"📅 {release_date.split('-')[0]}")
            date_label.setStyleSheet("font-size: 13px; color: #ccc;")
            meta_layout.addWidget(date_label)

        runtime = self.movie.get("runtime")
        if runtime:
            hours, minutes = divmod(runtime, 60)
            dur_text = f"{hours}h {minutes}min" if hours else f"{minutes}min"
            dur_label = QLabel(f"🕐 {dur_text}")
            dur_label.setStyleSheet("font-size: 13px; color: #ccc;")
            meta_layout.addWidget(dur_label)

        rating = self.movie.get("vote_average")
        if rating:
            rating_label = QLabel(f"⭐ {float(rating):.1f}/10")
            rating_label.setStyleSheet("font-size: 13px; color: #ccc;")
            meta_layout.addWidget(rating_label)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        # Gêneros
        genres = self.movie.get("genres", [])
        if genres:
            genres_label = QLabel("  ".join(
                [f"<span style='background:#2a2a2a;border-radius:4px;"
                 f"padding:2px 8px;color:#ddd;'>{g}</span>" for g in genres]
            ))
            genres_label.setTextFormat(Qt.RichText)
            genres_label.setWordWrap(True)
            genres_label.setStyleSheet("font-size: 12px;")
            info_layout.addWidget(genres_label)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333; max-height: 1px;")
        info_layout.addWidget(sep)

        # Sinopse
        sinopse_title = QLabel("Sinopse")
        sinopse_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        info_layout.addWidget(sinopse_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #1a1a1a; width: 5px; border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #444; border-radius: 2px; min-height: 20px;
            }
        """)

        overview_widget = QWidget()
        overview_widget.setStyleSheet("background: transparent;")
        overview_layout = QVBoxLayout(overview_widget)
        overview_layout.setContentsMargins(0, 0, 6, 0)

        overview_label = QLabel(self.movie.get("overview", "Sinopse não disponível."))
        overview_label.setWordWrap(True)
        overview_label.setAlignment(Qt.AlignJustify)
        overview_label.setStyleSheet("font-size: 13px; color: #ccc;")
        overview_layout.addWidget(overview_label)
        overview_layout.addStretch()

        scroll.setWidget(overview_widget)
        info_layout.addWidget(scroll)

        # ── Botão Assistir ───────────────────────────────────────────
        watch_btn = QPushButton("▶  Assistir")
        watch_btn.setCursor(Qt.PointingHandCursor)
        watch_btn.setFixedHeight(38)
        watch_btn.setStyleSheet("""
            QPushButton {
                background-color: #E50914;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #f40d12;
            }
            QPushButton:pressed {
                background-color: #c0060f;
            }
        """)
        watch_btn.clicked.connect(self.play_movie)
        info_layout.addWidget(watch_btn)

        card_layout.addWidget(info_container)
        outer_layout.addWidget(self.card)

        # Animação fade in
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(180)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.OutCubic)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------
    def play_movie(self):
        """Abre o arquivo de vídeo no player padrão do sistema."""
        file_path = self.movie.get("file_path")
        if file_path and os.path.exists(file_path):
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                os.system(f'open "{file_path}"')
            else:
                os.system(f'xdg-open "{file_path}"')
            self.close_overlay()
        else:
            QMessageBox.warning(self, "Erro", "Arquivo não encontrado!")

    def show_overlay(self):
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()
        self.fade_in.start()

    def close_overlay(self):
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(self.hide)
        fade_out.start()
        self._fade_out_anim = fade_out

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.close_overlay()
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())
