import os
import sys
import re
import asyncio
from datetime import date

base_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(base_dir, "Images")

from ble import BleNotifier
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt,QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QComboBox,
    QTextEdit,
    QGroupBox,
    QScrollArea,
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QStackedWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QGraphicsOpacityEffect
)

from qasync import QEventLoop, asyncSlot

from repo import Repo
from exporter import export_measurement_to_excel

_RX = re.compile(r"([+-]?\d+(?:[.,]\d+)?)\s*(?:u[mM]|µm)\b")
RE_OPERADOR = re.compile(r"^Z\d{3}[A-Z0-9]{4}$")
RE_SERIE = re.compile(r"^\d{10}$")
RE_PROJETO = re.compile(r"^[A-Z]{3}\d{4}$")

IMAGE_PATHS = {
    "Topo":     os.path.join(images_dir, "Topo.png"),
    "Frente1":  os.path.join(images_dir, "Frente 1.png"),
    "Frente2":  os.path.join(images_dir, "Frente 2.png"),
    "Lateral1": os.path.join(images_dir, "Lateral 1.png"),
    "Lateral2": os.path.join(images_dir, "Lateral 2.png"),
    "Fundo":    os.path.join(images_dir, "Fundo.png"),
}


POSTOS = [
    ("FUNDO", "Pintura - Fundo"),
    ("ACAB", "Pintura - Acabamento"),
    ("JAT", "Jateamento"),
]

# Pontos de Jateamento por dia da semana (0=segunda ... 4=sexta, 5=sábado, 6=domingo)
# Sexta (4) e fim de semana usam todos os 46 pontos
JAT_SCHEDULE = {
    0: [1, 7, 16, 25, 33, 41],   # Segunda
    1: [3, 8, 17, 26, 34, 43],   # Terça
    2: [5, 9, 18, 27, 35, 45],   # Quarta
    3: [2, 10, 19, 28, 36, 42],  # Quinta
}
JAT_ALL = list(range(1, 47))  # Sexta + fim de semana: todos os 46


class OverviewPage(QWidget):
    def __init__(self, repo: Repo, go_newedit, go_batch, go_history, set_ble_config=None) -> None:
        super().__init__()
        self.repo = repo
        self.go_newedit = go_newedit
        self.go_batch = go_batch
        self.go_history = go_history
        self._set_ble_config_cb = set_ble_config  # callback do AppWindow

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["", "ID", "Data/Hora", "Operador", "Projeto", "Número de Série", "Posto"])
        self.table.setColumnWidth(0, 30)
        self.table.setColumnHidden(1, True)
        self.table.horizontalHeader().setStretchLastSection(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)   # ajusta ao conteúdo
        header.setStretchLastSection(True)                          # última ocupa o resto

        # (opcional) limita a largura máxima para não ficar enorme
        for col in range(self.table.columnCount()):
            header.setMaximumSectionSize(260)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # Botões
        self.btn_new = QPushButton("Cadastrar Medição")
        self.btn_batch = QPushButton("Exportar")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Excluir")
        self.btn_delete.setProperty("danger", True)
        self.btn_history = QPushButton("Histórico")
        self.btn_refresh = QPushButton("Atualizar")

        self.ble_mac = QLineEdit("24:5D:FC:00:B3:2E")
        self.ble_uuid = QLineEdit("06d1e5e7-79ad-4a71-8faa-373789f7d93c")

        self.btn_save_ble = QPushButton("Salvar BLE")
        self.btn_save_ble.clicked.connect(self._save_ble)

        ble_box = QGroupBox("Configuração BLE")
        g = QGridLayout(ble_box)
        g.addWidget(QLabel("MAC:"), 0, 0)
        g.addWidget(self.ble_mac, 0, 1)
        g.addWidget(QLabel("UUID:"), 1, 0)
        g.addWidget(self.ble_uuid, 1, 1)
        g.addWidget(self.btn_save_ble, 0, 2, 2, 1)

        # Estilos/tamanhos
        self.btn_new.setProperty("primary", True)
        self.btn_batch.setProperty("export", True)



        # Sinais
        self.btn_new.clicked.connect(self._on_new)
        self.btn_batch.clicked.connect(self._on_batch)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_history.clicked.connect(self.go_history)
        self.btn_refresh.clicked.connect(self.refresh)

        # Header
        logo = QLabel()
        pix = QPixmap(os.path.join(images_dir, "Siemens_Energy.png"))
        logo.setPixmap(pix.scaledToHeight(28, Qt.SmoothTransformation))

        title = QLabel("Medições Pendentes")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        title_box = QHBoxLayout()
        title_box.addWidget(logo)
        title_box.addSpacing(8)
        title_box.addWidget(title)
        title_box.addStretch()

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addLayout(title_box)
        top.addStretch()
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_batch)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_delete)
        top.addWidget(self.btn_history)
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(ble_box)
        self.setLayout(layout)

        self.refresh()

    def refresh(self) -> None:
        items = self.repo.list_pending_all()
        self.table.setRowCount(0)

        def ro(text: str) -> QTableWidgetItem:
            it = QTableWidgetItem(text)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            return it

        for m in items:
            r = self.table.rowCount()
            self.table.insertRow(r)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked)
            self.table.setItem(r, 0, chk)

            self.table.setItem(r, 1, ro(str(m.id)))
            self.table.setItem(r, 2, ro(m.created_at))
            self.table.setItem(r, 3, ro(m.operador))
            self.table.setItem(r, 4, ro(m.projeto or ""))
            self.table.setItem(r, 5, ro(m.serie or ""))
            self.table.setItem(r, 6, ro(m.posto))

    def _selected_ids(self) -> list[int]:
        ids: list[int] = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)  # checkbox
            if item and item.checkState() == Qt.Checked:
                ids.append(int(self.table.item(r, 1).text()))  # ID (coluna escondida)
        return ids

    def _on_new(self) -> None:
        self.go_newedit()

    def _on_batch(self) -> None:
        ids = self._selected_ids()
        if len(ids) == 0:
            QMessageBox.warning(self, "Erro", "Selecione pelo menos 1 medição para exportar.")
            return
        self.go_batch(ids)
    
    def delete_measurement(self, id_: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM measurements WHERE id=?", [id_])

    def _on_delete(self) -> None:
        table = self.table

        # procura 1a linha com checkbox marcado
        id_ = None
        for r in range(table.rowCount()):
            chk = table.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                id_ = int(table.item(r, 1).text())
                break

        if id_ is None:
            QMessageBox.information(self, "Info", "Marque uma medição para excluir.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar exclusão",
            f"Excluir a medição (ID {id_})?",
        )
        if resp != QMessageBox.Yes:
            return

        self.repo.delete_measurement(id_)
        self.refresh()

    def _save_ble(self) -> None:
        mac = self.ble_mac.text().strip()
        uuid = self.ble_uuid.text().strip()

        if not mac or not uuid:
            QMessageBox.warning(self, "Erro", "Preencha MAC e UUID.")
            return

        # chama o callback que o AppWindow passou
        if self._set_ble_config_cb is not None:
            self._set_ble_config_cb(mac, uuid)

        QMessageBox.information(self, "OK", "Configuração BLE salva.")
    
    def _on_edit(self) -> None:
        ids = self._selected_ids()
        if len(ids) != 1:
            QMessageBox.warning(self, "Erro", "Selecione exatamente 1 medição para editar.")
            return

        m_id = ids[0]
        m = self.repo.get_by_ids([m_id])[0]

        if not m:
            QMessageBox.warning(self, "Erro", "Medição não encontrada.")
            return

        self.go_newedit(edit_id=m_id, measurement=m)

class NewEditPage(QWidget):
    
    def __init__(self, repo: Repo, go_overview) -> None:
        super().__init__()
        self.repo = repo
        self.go_overview = go_overview
        self._posto = "FUNDO"
        self.setWindowTitle("Medição de Camada - BLE")
        self._edit_id = None
        # Lista de índices (0-based) ativos na medição atual.
        # None = todos os 46. Preenchido ao selecionar posto Jateamento.
        self._active_measures: list[int] | None = None

        # BLE inputs (se quiser esconder depois, pode)
        self.address = QLineEdit("24:5D:FC:00:B3:2E")
        self.uuid = QLineEdit("06d1e5e7-79ad-4a71-8faa-373789f7d93c")

        # Cabeçalho
        self.posto = QComboBox()
        self.posto.addItems(["Pintura - Fundo", "Pintura - Acabamento", "Jateamento"])
        self.posto.setCurrentIndex(-1)
        self.posto.setPlaceholderText("Selecione...")
        self.posto.currentTextChanged.connect(self._on_posto_changed)
        self.projeto = QLineEdit()
        self.serie = QLineEdit()
        self.operador = QLineEdit()
        self._warned_operator_empty = False

        # Botões
        self.btn_back = QPushButton("Voltar")
        topbar = QHBoxLayout()
        topbar.addWidget(self.btn_back)
        topbar.addStretch()
        self.btn_start = QPushButton("Conectar / Iniciar")
        self.btn_stop = QPushButton("Parar / Desconectar")
        self.btn_stop.setEnabled(False)
        self.btn_export = QPushButton("Salvar")
        self.btn_clear_one = QPushButton("Limpar medição selecionada")
        self.btn_clear_all = QPushButton("Limpar medições")

        self.btn_start.setProperty("primary", True)

        self.btn_stop.setProperty("danger", True)


        # Log (opcional)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        # ====== MEDIÇÕES (1 coluna, 46 linhas) ======
        self.measure_edits: list[QLineEdit] = []
        self.next_index = 0  # 0..45
        self.override_index: int | None = None

        measures_box = QGroupBox("Medições (1 a 46)")
        measures_grid = QGridLayout()

        for i in range(46):
            lbl = QLabel(f"{i+1:02d}:")
            edit = QLineEdit()
            edit.setReadOnly(False)
            edit.setAlignment(Qt.AlignCenter)
            edit.setMinimumHeight(32)  # evita corte de texto durante digitação
            edit.selectionChanged.connect(lambda i=i: self.set_override_index(i))

            self.measure_edits.append(edit)

            measures_grid.addWidget(lbl, i, 0)
            measures_grid.addWidget(edit, i, 1)

        measures_box.setLayout(measures_grid)

        self.scroll_measures = QScrollArea()
        self.scroll_measures.setWidgetResizable(True)
        self.scroll_measures.setWidget(measures_box)

        # ====== IMAGEM (lado direito) ======

        # caminhos das imagens
        self.img_1_6   = os.path.join(images_dir, "Topo.png")
        self.img_7_15  = os.path.join(images_dir, "Frente 1.png")
        self.img_16_24 = os.path.join(images_dir, "Frente 2.png")
        self.img_25_32 = os.path.join(images_dir, "Lateral 1.png")
        self.img_33_40 = os.path.join(images_dir, "Lateral 2.png")
        self.img_41_46 = os.path.join(images_dir, "Fundo.png")

        self._current_img_path = None
        self._original_pixmap = QPixmap()

        # label da imagem
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        self.arrow_positions = {

            "Topo": {
                1: (214, 446),
                2: (258, 391),
                3: (268, 490),
                4: (311, 446),
                5: (323, 545),
                6: (386, 505),
            },

            "Frente1": {
                7:  (201, 355),
                8:  (239, 391),
                9:  (304, 416),
                10: (222, 498),
                11: (254, 538),
                12: (304, 572),
                13: (220, 625),
                14: (258, 665),
                15: (304, 703),
            },

            "Frente2": {
                16: (220, 351),
                17: (258, 388),
                18: (319, 410),
                19: (239, 492),
                20: (270, 532),
                21: (319, 568),
                22: (235, 627),
                23: (270, 661),
                24: (323, 698),
            },

            "Lateral1": {
                25: (282, 187),
                26: (335, 145),
                27: (269, 354),
                28: (326, 320),
                29: (269, 446),
                30: (333, 412),
                31: (270, 627),
                32: (332, 591),
            },

            "Lateral2": {
                33: (240, 185),
                34: (290, 152),
                35: (236, 356),
                36: (291, 320),
                37: (234, 444),
                38: (291, 406),
                39: (236, 624),
                40: (286, 593),
            },

            "Fundo": {
                41: (223, 416),
                42: (280, 349),
                43: (269, 480),
                44: (322, 419),
                45: (312, 547),
                46: (368, 480),
            }
        }

        # seta (overlay simples)
        self.arrow_label = QLabel(self.image_label)
        self.arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.arrow_label.setStyleSheet("background: transparent;")

        arrow_pix = QPixmap(os.path.join(images_dir, "seta verde.png"))
        if not arrow_pix.isNull():
            self.arrow_label.setPixmap(
                arrow_pix.scaledToWidth(45, Qt.SmoothTransformation)
            )

        self.offset_correction_x = -20    # ajuste horizontal
        self.offset_correction_y = -44    # ajuste vertical

        # Efeito de opacidade
        self.arrow_opacity = QGraphicsOpacityEffect(self.arrow_label)
        self.arrow_label.setGraphicsEffect(self.arrow_opacity)
        self.arrow_opacity.setOpacity(1.0)

        # Animação de fade in/out
        self.arrow_anim = QPropertyAnimation(self.arrow_opacity, b"opacity")
        self.arrow_anim.setDuration(900)         # 0.9s para piscar
        self.arrow_anim.setStartValue(1.0)       # totalmente visível
        self.arrow_anim.setEndValue(0.2)         # quase transparente
        self.arrow_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.arrow_anim.setLoopCount(-1)         # repete para sempre
        self.arrow_anim.start()


        # container do groupbox
        image_box = QGroupBox("Referência")
        image_layout = QVBoxLayout(image_box)
        image_layout.addWidget(self.image_label)

        self.update_image_for_measure(1)
        self.move_arrow_to_measure(1)

        # Medições + imagem lado a lado
        measures_and_image = QHBoxLayout()
        measures_and_image.addWidget(self.scroll_measures, 2)
        measures_and_image.addWidget(image_box, 1)

        # ====== Layout cabeçalho ======
        header_box = QGroupBox("Dados")
        header_grid = QGridLayout()

        header_grid.addWidget(QLabel("Posto:"), 0, 0)
        header_grid.addWidget(self.posto, 0, 1)

        header_grid.addWidget(QLabel("Operador:"), 1, 0)
        header_grid.addWidget(self.operador, 1, 1)

        header_grid.addWidget(QLabel("Projeto:"), 2, 0)
        header_grid.addWidget(self.projeto, 2, 1)

        header_grid.addWidget(QLabel("Número de Série:"), 3, 0)
        header_grid.addWidget(self.serie, 3, 1)

        header_box.setLayout(header_grid)


        # ====== Botões ======
        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_stop)
        buttons.addWidget(self.btn_clear_one)
        buttons.addWidget(self.btn_clear_all)
        buttons.addWidget(self.btn_export)

        # ====== Conteúdo rolável (para notebook) ======
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.addWidget(header_box)
        central_layout.addLayout(buttons)
        central_layout.addLayout(measures_and_image)
        central_layout.addWidget(QLabel("Log:"))
        central_layout.addWidget(self.log)
        central_layout.addStretch()

        scroll_page = QScrollArea()
        scroll_page.setWidgetResizable(True)
        scroll_page.setWidget(central_widget)
        self.scroll_page = scroll_page

        # ====== Layout principal ======
        layout = QVBoxLayout()
        layout.addLayout(topbar)      # topbar fixo
        layout.addWidget(scroll_page) # restante rolável
        self.setLayout(layout)

        # BLE controller
        self.ble: BleNotifier | None = None

        # Sinais
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_back.clicked.connect(self.go_back)
        self.btn_clear_one.clicked.connect(self.clear_selected_measurement)
        self.btn_export.clicked.connect(self.save_pending)
        self.btn_clear_all.clicked.connect(self.clear_measurements)
    
    def update_image_for_measure(self, measure_number: int) -> None:
        path = self.image_path_for_measure(measure_number)
        if path != self._current_img_path:
            self._current_img_path = path
            self._original_pixmap = QPixmap(path)

        if self._original_pixmap.isNull():
            self.image_label.setText(f"Imagem não encontrada: {path}")
            return

        self._apply_scaled_pixmap()

    def image_path_for_measure(self, measure_number: int) -> str:
        if 1 <= measure_number <= 6:
            return self.img_1_6
        if 7 <= measure_number <= 15:
            return self.img_7_15
        if 16 <= measure_number <= 24:
            return self.img_16_24
        if 25 <= measure_number <= 32:
            return self.img_25_32
        if 33 <= measure_number <= 40:
            return self.img_33_40
        return self.img_41_46

    def _apply_scaled_pixmap(self) -> None:
        if self._original_pixmap.isNull():
            return
        if self.image_label.width() <= 10 or self.image_label.height() <= 10:
            return

        scaled = self._original_pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_scaled_pixmap()
        current = self.override_index if self.override_index is not None else self.next_index
        self.move_arrow_to_measure(current + 1)

    def set_arrow_pos(self, x: int, y: int) -> None:
        # x,y são pixels
        pix = self.arrow_label.pixmap()
        if pix:
            w = pix.width()
            h = pix.height()
            offset_x = w // 2
            offset_y = h  # ponta inferior da seta

            self.arrow_label.move(x - offset_x, y - offset_y)
            self.arrow_label.show()
            self.arrow_anim.stop()
            self.arrow_anim.start()

    
    def move_arrow_to_measure(self, measure_number):
        for image_name, measures in self.arrow_positions.items():
            if measure_number in measures:
                x_orig, y_orig = measures[measure_number]

                orig_w = self._original_pixmap.width() if not self._original_pixmap.isNull() else 0
                orig_h = self._original_pixmap.height() if not self._original_pixmap.isNull() else 0
                label_w = self.image_label.width()
                label_h = self.image_label.height()

                if orig_w > 0 and orig_h > 0 and label_w > 10 and label_h > 10:
                    scale = min(label_w / orig_w, label_h / orig_h)
                    scaled_w = int(orig_w * scale)
                    scaled_h = int(orig_h * scale)
                    offset_x = (label_w - scaled_w) // 2
                    offset_y = (label_h - scaled_h) // 2
                    x = offset_x + int(x_orig * scale)
                    y = offset_y + int(y_orig * scale)

                    x += self.offset_correction_x
                    y += self.offset_correction_y

                    self.append_log(
                        f"[DEBUG] m={measure_number} orig={orig_w}x{orig_h} "
                        f"label={label_w}x{label_h} scale={scale:.3f} "
                        f"scaled={scaled_w}x{scaled_h} offset=({offset_x},{offset_y}) "
                        f"seta=({x},{y})"
                    )
                else:
                    x, y = x_orig, y_orig

                self.arrow_label.move(x, y)
                self.arrow_label.show()
                self.arrow_anim.stop()
                self.arrow_anim.start()

                break

    def append_log(self, text: str) -> None:
        self.log.append(text)

    def _extract_value_um(self, data: bytes) -> str | None:
        text = data.decode("utf-8", errors="ignore").strip()
        m = _RX.search(text)
        if not m:
            return None
        valor = m.group(1).replace(",", ".")
        return f"{valor} um"

    def set_override_index(self, index: int) -> None:
        self.override_index = index

        # destaca o campo selecionado
        for j, e in enumerate(self.measure_edits):
            e.setStyleSheet("" if j != index else "border: 2px solid #0ea5e9; background-color: #1e3a5f;")

        self.update_image_for_measure(index + 1)
        self.move_arrow_to_measure(index + 1)

    def get_posto_code(self) -> str | None:
        txt = self.posto.currentText().strip()
        if txt == "Pintura - Fundo":
            return "FUNDO"
        if txt == "Pintura - Acabamento":
            return "ACAB"
        if txt == "Jateamento":
            return "JAT"
        return None
    
    def posto_code_to_text(self, code: str) -> str:
        if code == "FUNDO":
            return "Pintura - Fundo"
        if code == "ACAB":
            return "Pintura - Acabamento"
        if code == "JAT":
            return "Jateamento"
        return ""

    def clear_selected_measurement(self) -> None:
        if self.override_index is None:
            QMessageBox.information(self, "Info", "Clique primeiro na medição que deseja limpar.")
            return

        idx = self.override_index
        self.measure_edits[idx].clear()

        # opcional: remover destaque e “consumir” a seleção
        self.override_index = None
        for e in self.measure_edits:
            e.setStyleSheet("")

        self.append_log(f"Medição {idx+1:02d} limpa.")

    def clear_measurements(self) -> None:
        for e in self.measure_edits:
            e.clear()
            e.setStyleSheet("")

        self.next_index = 0
        self.override_index = None

        first = self._active_measures[0] if self._active_measures else 1
        self.update_image_for_measure(first)
        self.move_arrow_to_measure(first)  # BUG FIX: seta vai para o 1º ponto ativo
        self.append_log("Medições limpas. Próxima medição vai para o campo 01.")

        # opcional: volta scroll para o topo
        self.scroll_measures.verticalScrollBar().setValue(0)

    def finish_measurement(self) -> None:
        # salva a medição atual
        self.save_pending_silent()

        resp = QMessageBox.question(
            self,
            "Continuar?",
            "46 medições concluídas. Deseja continuar medindo (nova medição)?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if resp == QMessageBox.Yes:
            # mantém Operador e Projeto (se existir), limpa só as medições
            operador = self.operador.text()
            projeto = self.projeto.text() if hasattr(self, "projeto") else ""

            self.clear_measurements()   # já reseta seta para 1º ponto ativo
            self.serie.clear()

            self.operador.setText(operador)
            if hasattr(self, "projeto"):
                self.projeto.setText(projeto)

            first = self._active_measures[0] if self._active_measures else 1
            if self.measure_edits:
                self.measure_edits[first - 1].setFocus()
            return

        # Não: volta para overview
        self.reset_form()
        self.go_overview()

    def validate_fields_for_save(self) -> bool:
        operador = self.operador.text().strip()
        projeto = self.projeto.text().strip()
        serie = self.serie.text().strip()

        posto_code = self.get_posto_code()
        if not posto_code:
            QMessageBox.warning(self, "Erro", "Selecione o Posto.")
            return False

        if not RE_OPERADOR.fullmatch(operador):
            QMessageBox.warning(self, "Erro", "Operador inválido. Exemplo: Z123AB4C")
            return False

        # Projeto e Série: se você quer obrigatórios, valide sempre.
        # Se forem opcionais, valide só quando preenchidos:
        if projeto and not RE_PROJETO.fullmatch(projeto):
            QMessageBox.warning(self, "Erro", "Projeto inválido. Exemplo: ABC1234")
            return False

        if serie and not RE_SERIE.fullmatch(serie):
            QMessageBox.warning(self, "Erro", "Número de Série inválido. Deve ter 10 dígitos.")
            return False

        return True

    def save_pending(self) -> None:
        operador = self.operador.text().strip()
        if not self.validate_fields_for_save():
            return
        
        if not operador:
            QMessageBox.warning(self, "Erro", "Preencha Operador.")
            return

        posto_code = self.get_posto_code()
        if not posto_code:
            QMessageBox.warning(self, "Erro", "Selecione o Posto antes de salvar.")
            return

        projeto = self.projeto.text().strip() or None
        serie = self.serie.text().strip() or None

        values = [e.text().strip() for e in self.measure_edits]
        if len(values) != 46:
            QMessageBox.warning(self, "Erro", "Esperado 46 medições.")
            return

        if self._edit_id is None:
            # Criar nova
            self.repo.create_pending(
                posto=posto_code,
                operador=operador,
                values=values,
                projeto=projeto,
                serie=serie,
            )
        else:
            # Atualizar existente
            self.repo.update_measurement(
                id=self._edit_id,
                posto=posto_code,
                operador=operador,
                projeto=projeto,
                serie=serie,
                values=values,
            )
            QMessageBox.information(self, "OK", "Medição atualizada.")
            self._edit_id = None

        QMessageBox.information(self, "OK", "Medição salva.")
        self.clear_measurements()
        # aqui você decide o que limpar/manter:
        self.serie.clear()
        self.go_overview()

    def save_pending_silent(self) -> None:
        operador = self.operador.text().strip()

        if not self.validate_fields_for_save():
            return
        
        if not operador:
            QMessageBox.warning(self, "Erro", "Preencha Operador.")
            return

        posto_code = self.get_posto_code()
        if not posto_code:
            QMessageBox.warning(self, "Erro", "Selecione o Posto antes de salvar.")
            return

        values = [e.text().strip() for e in self.measure_edits]
        if len(values) != 46 or not any(values):
            QMessageBox.warning(self, "Erro", "Não há medições para salvar.")
            return

        projeto = self.projeto.text().strip() or None
        serie = self.serie.text().strip() or None

        if self._edit_id is None:
            # Criar nova
            self.repo.create_pending(
                posto=posto_code,
                operador=operador,
                values=values,
                projeto=projeto,
                serie=serie,
            )
        else:
            # Atualizar existente
            self.repo.update_measurement(
                id=self._edit_id,
                posto=posto_code,
                operador=operador,
                projeto=projeto,
                serie=serie,
                values=values,
            )
            QMessageBox.information(self, "OK", "Medição atualizada.")
            self._edit_id = None

    def go_back(self) -> None:
        has_any = (
            any(e.text().strip() for e in self.measure_edits)
            or self.operador.text().strip()
            or self.projeto.text().strip()
            or self.serie.text().strip()
        )
        if has_any:
            resp = QMessageBox.question(self, "Confirmar", "Sair sem salvar? Os dados serão perdidos.")
            if resp != QMessageBox.Yes:
                return

        self.reset_form()
        self.go_overview()

    def reset_form(self) -> None:
        self._edit_id = None
        self._active_measures = None  # volta para 46 pontos
        # limpa medições (46 campos + índices + imagem)
        self.clear_measurements()

        # limpa cabeçalho
        self.operador.clear()
        self.projeto.clear()
        self.serie.clear()
        self.posto.setCurrentIndex(-1)

        # opcional: limpa log
        self.log.clear()

        # limpa seleção de override e bordas (por segurança)
        self.override_index = None
        for e in self.measure_edits:
            e.setStyleSheet("")
        self.update_image_for_measure(1)
        self.move_arrow_to_measure(1)  # BUG FIX: reseta seta para posição 1

    @asyncSlot()
    async def start(self) -> None:
        mac = self.address.text().strip()
        uuid = self.uuid.text().strip()
        if not mac or not uuid:
            QMessageBox.warning(self, "Erro", "Preencha MAC e UUID.")
            return

        self.btn_start.setEnabled(False)
        try:
            self.ble = BleNotifier(mac, uuid)
            await self.ble.connect()
            await self.ble.start(self.on_notify)
            self.btn_stop.setEnabled(True)
            self.append_log("Conectado e notificações ativas.")
        except Exception as e:
            self.append_log(f"Falha: {e}")
            self.ble = None
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    @asyncSlot()
    async def stop(self) -> None:
        self.btn_stop.setEnabled(False)
        try:
            if self.ble:
                await self.ble.stop()
                self.append_log("Desconectado.")
        finally:
            self.ble = None
            self.btn_start.setEnabled(True)

    def validate_header_fields(self) -> bool:
        projeto = self.projeto.text().strip()
        serie = self.serie.text().strip()
        operador = self.operador.text().strip()

        ok = True

        def mark(widget, valid: bool):
            widget.setStyleSheet("" if valid else "border: 2px solid #c62828;")

        v_projeto = bool(RE_PROJETO.fullmatch(projeto))
        v_serie = bool(RE_SERIE.fullmatch(serie))
        v_operador = bool(RE_OPERADOR.fullmatch(operador))

        mark(self.projeto, v_projeto)
        mark(self.serie, v_serie)
        mark(self.operador, v_operador)

        if not v_projeto:
            ok = False
        if not v_serie:
            ok = False
        if not v_operador:
            ok = False

        if not ok:
            QMessageBox.warning(
                self,
                "Campos inválidos",
                """Verifique os campos:
        - Projeto: 3 letras maiúsculas + 4 números (ex: SEF0500)
        - Número de Série: 10 dígitos (ex: 1015150001)
        - Operador: Z + 3 dígitos + 4 alfanuméricos maiúsculos (ex: Z0052DFZ)""",
            )
        return ok

    def on_notify(self, sender: int, data: bytes) -> None:
        if not self.operador.text().strip():
            if not self._warned_operator_empty:
                QMessageBox.warning(self, "Operador obrigatório", "Preencha o campo Operador antes de iniciar as medições.")
                self._warned_operator_empty = True
            return
        else:
            self._warned_operator_empty = False

        posto_code = self.get_posto_code()
        if not posto_code:
            if not getattr(self, "_warned_posto_empty", False):
                QMessageBox.warning(self, "Posto obrigatório", "Selecione o Posto antes de iniciar as medições.")
                self._warned_posto_empty = True
            return
        else:
            self._warned_posto_empty = False
        
        value = self._extract_value_um(data)
        if value is None:
            self.append_log(f"Payload não reconhecido: {data!r}")
            return

        was_override = self.override_index is not None

        # Sequência ativa: todos os 46 ou subconjunto de Jateamento
        seq = self._active_measures if self._active_measures else list(range(1, 47))
        total = len(seq)

        # Decide onde escrever: correção (override) ou sequência (next_index)
        if was_override:
            idx = self.override_index          # idx já é 0-based (posição no measure_edits)
            self.override_index = None
            for e in self.measure_edits:
                e.setStyleSheet("")
        else:
            if self.next_index >= total:
                self.append_log("Todas as medições ativas preenchidas. Limpe para continuar.")
                return
            # seq contém números 1-based; measure_edits é 0-based
            idx = seq[self.next_index] - 1
            self.next_index += 1

        # preenche o campo escolhido
        edit_atual = self.measure_edits[idx]
        edit_atual.setText(value)

        # scroll até o campo preenchido
        self.scroll_measures.ensureWidgetVisible(edit_atual)
        self.scroll_page.ensureWidgetVisible(edit_atual)

        # Se acabamos de preencher a última medição ativa, finaliza
        if (not was_override) and self.next_index >= total:
            self.finish_measurement()
            return

        # Próxima medição na sequência ativa
        if not was_override and self.next_index < total:
            proxima = seq[self.next_index]   # número 1-based
            self.update_image_for_measure(proxima)
            self.move_arrow_to_measure(proxima)
            prox = self.measure_edits[proxima - 1]
            prox.setFocus()
            self.scroll_measures.ensureWidgetVisible(prox)
            self.scroll_page.ensureWidgetVisible(prox)


    def get_jat_measures(self) -> list[int]:
        """Retorna a lista de pontos de Jateamento para o dia de hoje."""
        weekday = date.today().weekday()  # 0=segunda ... 6=domingo
        measures = JAT_SCHEDULE.get(weekday, JAT_ALL)
        day_names = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta"}
        name = day_names.get(weekday, "Sexta/Fim de semana")
        self.append_log(f"Jateamento — {name}: pontos {measures}")
        return measures

    def _on_posto_changed(self, text: str) -> None:
        """Chamado ao mudar o posto. Configura a sequência ativa de medições."""
        if text == "Jateamento":
            self._active_measures = self.get_jat_measures()
            # Mostra só os campos ativos; esconde os outros
            for i, edit in enumerate(self.measure_edits):
                visible = (i + 1) in self._active_measures
                edit.setVisible(visible)
                # o label da linha fica junto (está em posição i no grid)
                lbl = self.scroll_measures.widget().layout().itemAtPosition(i, 0)
                if lbl and lbl.widget():
                    lbl.widget().setVisible(visible)
            # Atualiza título do groupbox
            self.scroll_measures.widget().setTitle(
                f"Medições — Jateamento ({len(self._active_measures)} pontos)"
            )
            first = self._active_measures[0]
            self.update_image_for_measure(first)
            self.move_arrow_to_measure(first)
        else:
            self._active_measures = None
            # Restaura todos os campos visíveis
            for i, edit in enumerate(self.measure_edits):
                edit.setVisible(True)
                lbl = self.scroll_measures.widget().layout().itemAtPosition(i, 0)
                if lbl and lbl.widget():
                    lbl.widget().setVisible(True)
            self.scroll_measures.widget().setTitle("Medições (1 a 46)")
            self.update_image_for_measure(1)
            self.move_arrow_to_measure(1)
        self.next_index = 0
        self.override_index = None

    def set_posto(self, posto: str) -> None:
        self._posto = posto
        self.lbl_posto.setText(posto)
        self.update_image_for_measure(1)  # opcional, mas recomendado

    def set_ble_config(self, mac: str, uuid: str) -> None:
        self.address.setText(mac)
        self.uuid.setText(uuid)

    def load_for_edit(self, edit_id, m):
        self._edit_id = edit_id

        # Preenche o cabeçalho
        self.posto.setCurrentText(self.posto_code_to_text(m.posto))
        self.operador.setText(m.operador)
        if hasattr(self, "projeto"):
            self.projeto.setText(m.projeto or "")
        self.serie.setText(m.serie or "")

        # Preencher as 46 medições
        for i, value in enumerate(m.values):
            if i < len(self.measure_edits):
                self.measure_edits[i].setText(value)

        self.next_index = 46  # evita continuar preenchendo

class BatchExportPage(QWidget):
    def __init__(self, repo: Repo, go_overview, go_history) -> None:
        super().__init__()
        self.repo = repo
        self.go_overview = go_overview
        self.go_history = go_history

        self._posto = "FUNDO"
        self._ids: list[int] = []

        self.title = QLabel("Lote - Atribuir e Exportar")
        self.project_global = QLineEdit()
        self.project_global.setPlaceholderText("Projeto para aplicar a todos (opcional)")

        self.btn_apply_project = QPushButton("Aplicar Projeto a todos")
        self.btn_export = QPushButton("Exportar arquivos")
        self.btn_back = QPushButton("Voltar")

        self.btn_apply_project.clicked.connect(self._apply_project_all)
        self.btn_export.clicked.connect(self._export)
        self.btn_back.clicked.connect(self.go_overview)

        self.btn_export.setProperty("export", True)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Projeto", "Número de Série"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setStretchLastSection(True)

        header = self.table.horizontalHeader()

        # ID (col 0) está oculto
        header.setSectionResizeMode(0, QHeaderView.Fixed)

        # Projeto e Série ocupam a largura igualmente
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        top = QGridLayout()
        top.addWidget(self.title, 0, 0, 1, 3)
        top.addWidget(QLabel("Projeto (aplicar a todos):"), 1, 0)
        top.addWidget(self.project_global, 1, 1)
        top.addWidget(self.btn_apply_project, 1, 2)

        btns = QHBoxLayout()
        btns.addWidget(self.btn_back)
        btns.addStretch()
        btns.addWidget(self.btn_export)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addLayout(btns)
        self.setLayout(layout)

    def load(self, ids: list[int]) -> None:
        self._ids = ids
        self.title.setText(f"Lote - {len(ids)} medições")

        measurements = self.repo.get_by_ids(ids)

        self.table.setRowCount(0)
        for m in measurements:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(m.id)))
            self.table.setItem(r, 1, QTableWidgetItem(m.projeto or ""))
            self.table.setItem(r, 2, QTableWidgetItem(m.serie or ""))

    def _apply_project_all(self) -> None:
        proj = self.project_global.text().strip()
        if not proj:
            return
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 1)
            if item is None:
                item = QTableWidgetItem("")
                self.table.setItem(r, 2, item)
            item.setText(proj)

    def _export(self) -> None:
        # validações
        for r in range(self.table.rowCount()):
            proj = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()
            serie = (self.table.item(r, 2).text() if self.table.item(r, 2) else "").strip()

            if not RE_SERIE.fullmatch(serie):
                QMessageBox.warning(self, "Erro", f"Linha {r+1}: Número de Série inválida (10 dígitos).")
                return
            if not RE_PROJETO.fullmatch(proj):
                QMessageBox.warning(self, "Erro", f"Linha {r+1}: Projeto inválido (SEF0500).")
                return

        # exporta 5
        measurements = self.repo.get_by_ids(self._ids)
        for r, m in enumerate(measurements):
            proj = self.table.item(r, 1).text().strip()
            serie = self.table.item(r, 2).text().strip()

            # atualiza assignment
            self.repo.update_assignment(m.id, proj, serie)

            # exporta excel (com sufixo automático)
            export_measurement_to_excel(
                serie=serie,
                projeto=proj,
                operador=m.operador,
                posto=m.posto,
                created_at=m.created_at,
                values=m.values,
            )

            # marca como exportado (vai pro histórico)
            self.repo.mark_exported(m.id)

        QMessageBox.information(self, "OK", "Arquivos exportados e enviados ao histórico.")
        self.go_history()

class HistoryPage(QWidget):
    def __init__(self, repo: Repo, go_overview) -> None:
        super().__init__()
        self.repo = repo
        self.go_overview = go_overview

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Exportado em", "Cadastro em", "Posto", "Série", "Operador"])
        self.table.horizontalHeader().setStretchLastSection(True)

        self.btn_back = QPushButton("Voltar")
        self.btn_refresh = QPushButton("Atualizar")

        self.btn_back.clicked.connect(self.go_overview)
        self.btn_refresh.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(self.btn_back)
        top.addStretch()
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    def refresh(self) -> None:
        items = self.repo.list_history(limit=300)
        self.table.setRowCount(0)
        for m in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(m.id)))
            self.table.setItem(r, 1, QTableWidgetItem(m.exported_at or ""))
            self.table.setItem(r, 2, QTableWidgetItem(m.created_at))
            self.table.setItem(r, 3, QTableWidgetItem(m.posto))
            self.table.setItem(r, 4, QTableWidgetItem(m.serie or ""))
            self.table.setItem(r, 5, QTableWidgetItem(m.operador))

class AppWindow(QStackedWidget):
    def __init__(self) -> None:
        super().__init__()
        self.repo = Repo("medicoes.db")
        self.ble_mac = "24:5D:FC:00:B3:2E"
        self.ble_uuid = "06d1e5e7-79ad-4a71-8faa-373789f7d93c"

        self.overview = OverviewPage(
            repo=self.repo,
            go_newedit=self.show_newedit,
            go_batch=self.show_batch,
            go_history=self.show_history,
            set_ble_config=self.set_ble_config
            )
        
        self.newedit = NewEditPage(repo=self.repo, go_overview=self.show_overview)
        self.batch = BatchExportPage(repo=self.repo, go_overview=self.show_overview, go_history=self.show_history)
        self.history = HistoryPage(repo=self.repo, go_overview=self.show_overview)
        

        self.addWidget(self.overview)
        self.addWidget(self.newedit)
        self.addWidget(self.batch)
        self.addWidget(self.history)

        self.setWindowTitle("Medição de Camadas - SIEMENS ENERGY")
        self.setCurrentWidget(self.overview)
        self.resize(900, 600)

    def show_overview(self) -> None:
        self.overview.refresh()
        self.setCurrentWidget(self.overview)

    def show_newedit(self, edit_id=None, measurement=None):
        if edit_id is not None:
            self.newedit.load_for_edit(edit_id, measurement)
        else:
            self.newedit.reset_form()

        self.newedit.set_ble_config(self.ble_mac, self.ble_uuid)
        self.setCurrentWidget(self.newedit)

    def show_batch(self, ids: list[int]) -> None:
        self.batch.load(ids)
        self.setCurrentWidget(self.batch)

    def show_history(self) -> None:
        self.history.refresh()
        self.setCurrentWidget(self.history)

    def set_ble_config(self, mac: str, uuid: str) -> None:
        self.ble_mac = mac
        self.ble_uuid = uuid


def main() -> None:
    app = QApplication(sys.argv)
    
    app.setStyleSheet("""
    /* ── BASE ─────────────────────────────────────────────────────── */
    * {
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 10pt;
        color: #e2e8f0;
    }

    QWidget {
        background-color: #0f172a;
    }

    QStackedWidget {
        background-color: #0f172a;
    }

    /* ── TOPBAR / TOOLBAR AREA ─────────────────────────────────────── */
    QWidget#topbar {
        background-color: #1e293b;
        border-bottom: 1px solid #334155;
    }

    /* ── GROUP BOX ─────────────────────────────────────────────────── */
    QGroupBox {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 18px;
        padding: 12px 10px 10px 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        top: 2px;
        padding: 0 6px;
        color: #94a3b8;
        font-size: 8.5pt;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    /* ── INPUTS ────────────────────────────────────────────────────── */
    QLineEdit, QComboBox, QTextEdit {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 5px 10px;
        min-height: 28px;
        color: #e2e8f0;
        selection-background-color: #0ea5e9;
        selection-color: #ffffff;
    }
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
        border: 1px solid #0ea5e9;
        background-color: #1e293b;
    }
    QLineEdit:disabled, QComboBox:disabled {
        background-color: #1e293b;
        color: #475569;
        border-color: #1e293b;
    }
    QLineEdit[readOnly="true"] {
        background-color: #1e293b;
        color: #94a3b8;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox::down-arrow {
        width: 10px;
        height: 10px;
        border-left:  2px solid #64748b;
        border-bottom: 2px solid #64748b;
        margin-right: 6px;
        /* simple CSS chevron via rotation trick */
    }
    QComboBox QAbstractItemView {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        selection-background-color: #0ea5e9;
        selection-color: #ffffff;
        outline: none;
    }

    /* ── LABELS ────────────────────────────────────────────────────── */
    QLabel {
        background: transparent;
        color: #cbd5e1;
    }

    /* ── BUTTONS — default ─────────────────────────────────────────── */
    QPushButton {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 7px 16px;
        font-weight: 600;
        font-size: 9.5pt;
        color: #cbd5e1;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: #334155;
        border-color: #475569;
        color: #f1f5f9;
    }
    QPushButton:pressed {
        background-color: #0f172a;
        border-color: #0ea5e9;
    }
    QPushButton:disabled {
        background-color: #1e293b;
        color: #334155;
        border-color: #1e293b;
    }

    /* ── BUTTON — primary (Cadastrar / Conectar) ───────────────────── */
    QPushButton[primary="true"] {
        background-color: #0ea5e9;
        border: 1px solid #0ea5e9;
        color: #ffffff;
    }
    QPushButton[primary="true"]:hover  { background-color: #38bdf8; border-color: #38bdf8; }
    QPushButton[primary="true"]:pressed { background-color: #0284c7; }
    QPushButton[primary="true"]:disabled {
        background-color: #0c4a6e;
        border-color: #0c4a6e;
        color: #475569;
    }

    /* ── BUTTON — export / green ───────────────────────────────────── */
    QPushButton[export="true"] {
        background-color: #059669;
        border: 1px solid #059669;
        color: #ffffff;
    }
    QPushButton[export="true"]:hover  { background-color: #10b981; border-color: #10b981; }
    QPushButton[export="true"]:pressed { background-color: #047857; }

    /* ── BUTTON — danger (Excluir / Parar) ────────────────────────── */
    QPushButton[danger="true"] {
        background-color: #dc2626;
        border: 1px solid #dc2626;
        color: #ffffff;
    }
    QPushButton[danger="true"]:hover  { background-color: #ef4444; border-color: #ef4444; }
    QPushButton[danger="true"]:pressed { background-color: #b91c1c; }
    QPushButton[danger="true"]:disabled {
        background-color: #1e293b;
        border-color: #1e293b;
        color: #475569;
    }

    /* ── TABLE ─────────────────────────────────────────────────────── */
    QTableWidget {
        background-color: #1e293b;
        alternate-background-color: #162032;
        border: 1px solid #334155;
        border-radius: 8px;
        gridline-color: #334155;
        outline: none;
    }
    QTableWidget::item {
        padding: 8px 10px;
        border: none;
        color: #cbd5e1;
    }
    QTableWidget::item:selected {
        background-color: #0c4a6e;
        color: #f0f9ff;
    }
    QTableWidget::item:hover {
        background-color: #1e3a5f;
    }
    QHeaderView::section {
        background-color: #0f172a;
        color: #64748b;
        font-size: 8.5pt;
        font-weight: 700;
        letter-spacing: 0.4px;
        padding: 9px 10px;
        border: none;
        border-bottom: 2px solid #334155;
        border-right: 1px solid #1e293b;
        text-transform: uppercase;
    }
    QHeaderView::section:last { border-right: none; }
    QTableCornerButton::section {
        background-color: #0f172a;
        border: none;
    }

    /* ── SCROLLBAR ─────────────────────────────────────────────────── */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #334155;
        border-radius: 4px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover  { background: #475569; }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical      { height: 0; }

    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #334155;
        border-radius: 4px;
        min-width: 24px;
    }
    QScrollBar::handle:horizontal:hover { background: #475569; }
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal     { width: 0; }

    QScrollArea {
        background-color: transparent;
        border: none;
    }

    /* ── CHECKBOX ──────────────────────────────────────────────────── */
    QCheckBox {
        spacing: 6px;
        color: #94a3b8;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #475569;
        border-radius: 4px;
        background: #0f172a;
    }
    QCheckBox::indicator:checked {
        background: #0ea5e9;
        border-color: #0ea5e9;
    }
    QCheckBox::indicator:hover {
        border-color: #0ea5e9;
    }

    /* ── MESSAGE BOX ───────────────────────────────────────────────── */
    QMessageBox {
        background-color: #1e293b;
    }
    QMessageBox QLabel {
        color: #e2e8f0;
        font-size: 10pt;
    }
    """)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = AppWindow()
    w.showMaximized()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
    