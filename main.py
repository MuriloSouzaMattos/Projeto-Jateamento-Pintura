import sys
import asyncio
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QMessageBox, QGroupBox, QScrollArea, QComboBox
)
from PySide6.QtGui import QPixmap

from qasync import QEventLoop, asyncSlot

from ble import BleNotifier


_RX = re.compile(r"([+-]?\d+(?:[.,]\d+)?)\s*(?:u[mM]|µm)\b")
RE_SERIE = re.compile(r"^\d{10}$")
RE_PROJETO = re.compile(r"^[A-Z]{3}\d{4}$")
RE_OPERADOR = re.compile(r"^Z\d{3}[A-Z0-9]{4}$")


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Medição de Camada - BLE")

        # BLE inputs (se quiser esconder depois, pode)
        self.address = QLineEdit("24:5D:FC:00:B3:2E")
        self.uuid = QLineEdit("06d1e5e7-79ad-4a71-8faa-373789f7d93c")

        # Cabeçalho
        self.projeto = QLineEdit()
        self.serie = QLineEdit()
        self.operador = QLineEdit()
        self.posto = QComboBox()
        self.posto.addItems(["Pintura - Fundo", "Pintura - Acabamento", "Jateamento"])
        self.posto.setCurrentIndex(-1)  # começa vazio
        self.posto.setPlaceholderText("Selecione...")

        # Botões
        self.btn_start = QPushButton("Conectar / Iniciar")
        self.btn_stop = QPushButton("Parar / Desconectar")
        self.btn_clear = QPushButton("Limpar medições")
        self.btn_stop.setEnabled(False)
        self.btn_export = QPushButton("Exportar para Excel")

        self.btn_start.setStyleSheet("""
        QPushButton {
            background-color: #2e7d32;   /* verde */
            color: white;
            font-weight: bold;
            padding: 6px 10px;
        }
        QPushButton:disabled {
            background-color: #9e9e9e;   /* cinza quando desabilitado */
            color: #eeeeee;
        }
        """)

        self.btn_stop.setStyleSheet("""
        QPushButton {
            background-color: #c62828;   /* vermelho */
            color: white;
            font-weight: bold;
            padding: 6px 10px;
        }
        QPushButton:disabled {
            background-color: #9e9e9e;
            color: #eeeeee;
        }
        """)


        # Log (opcional)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        # ====== MEDIÇÕES (1 coluna, 46 linhas) ======
        self.measure_edits: list[QLineEdit] = []
        self.next_index = 0  # 0..45

        measures_box = QGroupBox("Medições (1 a 46)")
        measures_grid = QGridLayout()

        for i in range(46):
            lbl = QLabel(f"{i+1:02d}:")
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setAlignment(Qt.AlignCenter)

            self.measure_edits.append(edit)

            measures_grid.addWidget(lbl, i, 0)
            measures_grid.addWidget(edit, i, 1)

        measures_box.setLayout(measures_grid)

        self.scroll_measures = QScrollArea()
        self.scroll_measures.setWidgetResizable(True)
        self.scroll_measures.setWidget(measures_box)

        # ====== IMAGEM (lado direito) ======
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        # caminhos das imagens (ajuste para os seus arquivos)
        self.img_1_6 = r"C:\Users\z0052dfz\Projeto-Jateamento-Pintura\Images\Topo.png"
        self.img_7_15 = r"C:\Users\z0052dfz\Projeto-Jateamento-Pintura\Images\Frente 1.png"
        self.img_16_24 = r"C:\Users\z0052dfz\Projeto-Jateamento-Pintura\Images\Frente 2.png"
        self.img_25_32 = r"C:\Users\z0052dfz\Projeto-Jateamento-Pintura\Images\Lateral 1.png"
        self.img_33_40 = r"C:\Users\z0052dfz\Projeto-Jateamento-Pintura\Images\Lateral 2.png"
        self.img_41_46 = r"C:\Users\z0052dfz\Projeto-Jateamento-Pintura\Images\Fundo.png"

        self._current_img_path = None  # para não recarregar a mesma imagem toda hora

        # mostra a imagem inicial (para medição 1)
        self.update_image_for_measure(1)

        image_box = QGroupBox("Referência")
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.image_label)
        image_box.setLayout(image_layout)

        # Medições + imagem lado a lado
        measures_and_image = QHBoxLayout()
        measures_and_image.addWidget(self.scroll_measures , 2)
        measures_and_image.addWidget(image_box, 1)

        # ====== Layout cabeçalho ======
        header_box = QGroupBox("Dados")
        header_grid = QGridLayout()
        
        header_grid.addWidget(QLabel("Posto:"), 0, 0)
        header_grid.addWidget(self.posto, 0, 1)

        header_grid.addWidget(QLabel("Projeto:"), 1, 0)
        header_grid.addWidget(self.projeto, 1, 1)

        header_grid.addWidget(QLabel("Número de Série:"), 2, 0)
        header_grid.addWidget(self.serie, 2, 1)

        header_grid.addWidget(QLabel("Operador:"), 3, 0)
        header_grid.addWidget(self.operador, 3, 1)

        header_box.setLayout(header_grid)

        # ====== Layout BLE (pode remover depois) ======
        ble_box = QGroupBox("Conexão BLE")
        ble_grid = QGridLayout()
        ble_grid.addWidget(QLabel("MAC:"), 0, 0)
        ble_grid.addWidget(self.address, 0, 1)
        ble_grid.addWidget(QLabel("UUID notify:"), 1, 0)
        ble_grid.addWidget(self.uuid, 1, 1)
        ble_box.setLayout(ble_grid)

        # ====== Botões ======
        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_stop)
        buttons.addWidget(self.btn_clear)
        buttons.addWidget(self.btn_export)

        # ====== Layout principal ======
        layout = QVBoxLayout()
        layout.addWidget(header_box)
        layout.addWidget(ble_box)
        layout.addLayout(buttons)
        layout.addLayout(measures_and_image)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log)
        self.setLayout(layout)

        # BLE controller
        self.ble: BleNotifier | None = None

        # Sinais
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_clear.clicked.connect(self.clear_measurements)
        self.btn_export.clicked.connect(self.export_to_excel)

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
        if 41 <= measure_number <= 46:
            return self.img_41_46
        return self.img_41_46  # fallback

    def update_image_for_measure(self, measure_number: int) -> None:
        path = self.image_path_for_measure(measure_number)
        if path == self._current_img_path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.image_label.setText(f"Imagem não encontrada: {path}")
            self._current_img_path = None
            return

        self.image_label.setPixmap(pixmap.scaledToWidth(320, Qt.SmoothTransformation))
        self._current_img_path = path

    def append_log(self, text: str) -> None:
        self.log.append(text)

    def clear_measurements(self) -> None:
        for e in self.measure_edits:
            e.clear()
        self.next_index = 0
        self.append_log("Medições limpas. Próxima medição vai para o campo 01.")
        self.update_image_for_measure(1)

    def _extract_value_um(self, data: bytes) -> str | None:
        text = data.decode("utf-8", errors="ignore").strip()
        m = _RX.search(text)
        if not m:
            return None
        valor = m.group(1).replace(",", ".")
        return f"{valor} um"


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
                "Verifique os campos:
    "
                "- Projeto: 3 letras maiúsculas + 4 números (ex: ABC1234)
    "
                "- Número de Série: 10 dígitos (ex: 0123456789)
    "
                "- Operador: Z + 3 dígitos + 4 alfanuméricos maiúsculos (ex: Z123AB4C)",
            )
        return ok

    def on_notify(self, sender: int, data: bytes) -> None:
        value = self._extract_value_um(data)
        if value is None:
            self.append_log(f"Payload não reconhecido: {data!r}")
            return

        if self.next_index >= 46:
            self.append_log("Já existem 46 medições preenchidas. Limpe para continuar.")
            return

        # preenche o campo atual
        edit_atual = self.measure_edits[self.next_index]
        edit_atual.setText(value)

        # faz o scroll descer até o campo preenchido
        self.scroll_measures.ensureWidgetVisible(edit_atual)

        self.next_index += 1

        # atualiza imagem para a PRÓXIMA medição (1..46)
        proxima_medicao = min(self.next_index + 1, 46)
        self.update_image_for_measure(proxima_medicao)

        # opcional: colocar foco no próximo campo e já rolar pra ele
        if self.next_index < 46:
            prox = self.measure_edits[self.next_index]
            prox.setFocus()
            self.scroll_measures.ensureWidgetVisible(prox)

    def export_to_excel(self) -> None:
        projeto = self.projeto.text().strip()
        serie = self.serie.text().strip()
        operador = self.operador.text().strip()
        posto = self.posto.currentText().strip()
        if not posto:
            QMessageBox.warning(self, "Erro", "Selecione o Posto antes de exportar.")
            return

        medidas = [e.text().strip() for e in self.measure_edits]

        if not projeto or not serie or not operador:
            QMessageBox.warning(
                self,
                "Erro",
                "Preencha Projeto, Número de Série e Operador antes de exportar.",
            )
            return

        if not any(medidas):
            QMessageBox.warning(self, "Erro", "Não há medições para exportar.")
            return

        row = {
            "Data/Hora": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "Projeto": projeto,
            "Número de Série": serie,
            "Operador": operador,
            "Posto": posto,
        }
        for i in range(46):
            row[f"M{i+1:02d}"] = medidas[i] if i < len(medidas) else ""

        df = pd.DataFrame([row])

        default_name = f"medicoes_{serie}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        export_dir = Path(r"C:\Users\z0052dfz\OneDrive - Siemens Energy\BACKUP\Arquivos aleatórios\Jato")
        export_dir.mkdir(parents=True, exist_ok=True)

        default_name = f"medicoes_{serie}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Excel",
            str(export_dir / default_name),
            "Excel (*.xlsx)",
        )
        if not path:
            return

        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            df.to_excel(path, index=False, sheet_name="Medições")
            QMessageBox.information(self, "OK", f"Arquivo salvo em: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar Excel: {e}")

    @asyncSlot()
    async def start(self) -> None:
        mac = self.address.text().strip()
        uuid = self.uuid.text().strip()

        if not mac or not uuid:
            QMessageBox.warning(self, "Erro", "Preencha MAC e UUID.")
            return

        self.btn_start.setEnabled(False)
        self.append_log(f"Conectando em {mac} ...")

        try:
            self.ble = BleNotifier(mac, uuid)
            await self.ble.connect()
            await self.ble.start(self.on_notify)

            self.append_log("Conectado e notificações ativas.")
            self.btn_stop.setEnabled(True)

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


def main() -> None:
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    w.resize(750, 800)
    w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()