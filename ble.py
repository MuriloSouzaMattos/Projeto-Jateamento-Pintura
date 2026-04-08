from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from bleak import BleakClient


NotifyCallback = Callable[[int, bytes], None]


@dataclass
class BleNotifier:
    address: str
    characteristic_uuid: str

    client: Optional[BleakClient] = None
    _cb: Optional[NotifyCallback] = None

    async def connect(self) -> None:
        self.client = BleakClient(self.address)
        await self.client.connect()

    async def start(self, callback: NotifyCallback) -> None:
        if not self.client:
            raise RuntimeError("Client não conectado. Chame connect() antes de start().")
        self._cb = callback
        await self.client.start_notify(self.characteristic_uuid, self._on_notify)

    async def stop(self) -> None:
        if not self.client:
            return
        try:
            await self.client.stop_notify(self.characteristic_uuid)
        finally:
            await self.client.disconnect()
            self.client = None

    def _on_notify(self, sender: int, data: bytearray) -> None:
        if self._cb:
            self._cb(sender, bytes(data))