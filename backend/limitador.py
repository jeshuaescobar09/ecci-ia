"""Limitador sencillo: cuenta eventos por clave (por ejemplo, la IP) en una ventana de tiempo."""
import time
from collections import defaultdict, deque


class Limitador:
    def __init__(self, limite, ventana_segundos):
        self.limite = limite
        self.ventana = ventana_segundos
        self._eventos = defaultdict(deque)

    def excedido(self, clave):
        cola = self._eventos.get(clave)
        if not cola:
            return False
        ahora = time.monotonic()
        while cola and ahora - cola[0] > self.ventana:
            cola.popleft()
        if not cola:
            del self._eventos[clave]
            return False
        return len(cola) >= self.limite

    def registrar(self, clave):
        self._eventos[clave].append(time.monotonic())

    def reiniciar(self):
        self._eventos.clear()
