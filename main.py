import sys
import asyncio


from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QLineEdit, QLabel, QMessageBox
)
from qasync import QEventLoop, asyncSlot

from ble import BleNotifier


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Medição de Camada - BLE")

        self.address = QLineEdit("24:5D:FC:00:B3:2E")
        self.uuid = QLineEdit("06d1e5e7-79ad-4a71-8faa-373789f7d93c")

        self.btn_start = QPushButton("Conectar / Iniciar")
        self.btn_stop = QPushButton("Parar / Desconectar")
        self.btn_stop.setEnabled(False)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("MAC do dispositivo:"))
        layout.addWidget(self.address)
        layout.addWidget(QLabel("UUID da característica (notify):"))
        layout.addWidget(self.uuid)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(QLabel("Leituras:"))
        layout.addWidget(self.log)
        self.setLayout(layout)

        self.ble: BleNotifier | None = None

        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)

    def append(self, text: str) -> None:
        self.log.append(text)

    def on_notify(self, sender: int, data: bytes) -> None:
        # Aqui você vai decodificar "data" para chegar no valor da medição
        self.append(f"{sender}: {data!r}")

    @asyncSlot()
    async def start(self) -> None:
        mac = self.address.text().strip()
        uuid = self.uuid.text().strip()

        if not mac or not uuid:
            QMessageBox.warning(self, "Erro", "Preencha MAC e UUID.")
            return

        self.btn_start.setEnabled(False)
        self.append(f"Conectando em {mac} ...")

        try:
            self.ble = BleNotifier(mac, uuid)
            await self.ble.connect()
            await self.ble.start(self.on_notify)

            self.append("Conectado e notificações ativas.")
            self.btn_stop.setEnabled(True)

        except Exception as e:
            self.append(f"Falha: {e}")
            self.ble = None
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    @asyncSlot()
    async def stop(self) -> None:
        self.btn_stop.setEnabled(False)
        try:
            if self.ble:
                await self.ble.stop()
                self.append("Desconectado.")
        finally:
            self.ble = None
            self.btn_start.setEnabled(True)


def main() -> None:
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    w.resize(650, 450)
    w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
