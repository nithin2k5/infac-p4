"""Delta PLC Modbus TCP connection manager."""

import threading
import time

# Support pymodbus 2.x and 3.x
try:
    from pymodbus.client import ModbusTcpClient
    PYMODBUS_AVAILABLE = True
except ImportError:
    try:
        from pymodbus.client.sync import ModbusTcpClient
        PYMODBUS_AVAILABLE = True
    except ImportError:
        PYMODBUS_AVAILABLE = False


class PLCManager:
    """Delta PLC communication via Modbus TCP.

    Delta DVP/AS coil layout (configurable):
      trigger_coil — PLC sets this to 1 to request an inspection
      pass_coil    — App sets this to 1 after a PASS result
      ng_coil      — App sets this to 1 after an NG result

    Default coil numbers map to M0/M1/M2 on Delta DVP series.
    Users can override via the UI.
    """

    def __init__(self):
        self.client = None
        self.host = "192.168.1.1"
        self.port = 502

        # Modbus coil addresses (user-configurable via UI)
        self.trigger_coil = 0   # M0 — PLC writes 1 here to trigger capture
        self.pass_coil    = 1   # M1 — App writes 1 here after PASS
        self.ng_coil      = 2   # M2 — App writes 1 here after NG

        self.is_connected = False

        self._poll_thread = None
        self._stop_poll = threading.Event()

        # Callbacks
        self.on_trigger = None       # () — called when PLC trigger fires
        self.on_connect = None       # () — called on successful connect
        self.on_disconnect = None    # () — called on disconnect/error

    @staticmethod
    def available():
        return PYMODBUS_AVAILABLE

    # ── Connection ──────────────────────────────────────────

    def connect(self, host: str, port: int = 502) -> bool:
        if not PYMODBUS_AVAILABLE:
            return False
        self.host = host
        self.port = port
        try:
            self.client = ModbusTcpClient(host, port=port, timeout=3)
            ok = self.client.connect()
            self.is_connected = ok
            if ok and self.on_connect:
                self.on_connect()
            return ok
        except Exception as e:
            print(f"[PLC] connect error: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        self._stop_poll.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2)
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.is_connected = False
        if self.on_disconnect:
            self.on_disconnect()

    # ── Write results ────────────────────────────────────────

    def write_result(self, is_pass: bool):
        """Write PASS/NG coils after an inspection."""
        if not self.is_connected or not self.client:
            return
        try:
            if is_pass:
                self.client.write_coil(self.pass_coil, True)
                self.client.write_coil(self.ng_coil, False)
            else:
                self.client.write_coil(self.pass_coil, False)
                self.client.write_coil(self.ng_coil, True)
        except Exception as e:
            print(f"[PLC] write_result error: {e}")
            self._handle_comm_error()

    def clear_result(self):
        """Clear both result coils (call before next inspection)."""
        if not self.is_connected or not self.client:
            return
        try:
            self.client.write_coil(self.pass_coil, False)
            self.client.write_coil(self.ng_coil, False)
        except Exception as e:
            print(f"[PLC] clear_result error: {e}")
            self._handle_comm_error()

    # ── Trigger polling ──────────────────────────────────────

    def start_trigger_poll(self):
        """Start background thread that polls the trigger coil at 10 Hz."""
        if not self.is_connected:
            return
        self._stop_poll.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop_trigger_poll(self):
        self._stop_poll.set()

    def _poll_loop(self):
        while not self._stop_poll.is_set():
            try:
                result = self.client.read_coils(self.trigger_coil, count=1)
                if result and not result.isError() and result.bits[0]:
                    # Acknowledge by clearing the trigger coil
                    self.client.write_coil(self.trigger_coil, False)
                    if self.on_trigger:
                        self.on_trigger()
            except Exception as e:
                print(f"[PLC] poll error: {e}")
                self._handle_comm_error()
                break
            time.sleep(0.1)

    # ── Internal ─────────────────────────────────────────────

    def _handle_comm_error(self):
        self.is_connected = False
        if self.on_disconnect:
            self.on_disconnect()
