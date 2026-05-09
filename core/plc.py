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

    Signal flow:
      1. User clicks "Send HIGH" in the app.
      2. App writes signal_coil HIGH  →  PLC sees it and starts its
         response sequence (e.g. physically positions the camera or
         simply latches the trigger).
      3. PLC writes trigger_coil HIGH  →  poll thread detects it,
         clears it, and fires on_trigger().
      4. App captures the current frame and runs solder inspection.
      5. App writes pass_coil or ng_coil based on the result.

    Default Modbus coil addresses (Delta DVP M-registers):
      signal_coil  M0 — App writes HIGH when user presses "Send HIGH"
      trigger_coil M1 — PLC writes HIGH to command a capture
      pass_coil    M2 — App writes HIGH after PASS
      ng_coil      M3 — App writes HIGH after NG
    """

    def __init__(self):
        self.client = None
        self.host = "192.168.1.1"
        self.port = 502

        # Modbus coil addresses (user-configurable via UI)
        self.signal_coil  = 0   # M0 — user-driven HIGH signal to PLC
        self.trigger_coil = 1   # M1 — PLC writes HIGH to request capture
        self.pass_coil    = 2   # M2 — App writes after PASS
        self.ng_coil      = 3   # M3 — App writes after NG

        self.is_connected = False

        self._poll_thread = None
        self._stop_poll = threading.Event()

        # Debounce gate — prevents a re-read trigger coil from double-firing
        # during the Modbus acknowledgement round-trip.  Armed (set) = ready.
        self._trigger_debounce = threading.Event()
        self._trigger_debounce.set()

        # Callbacks
        self.on_trigger    = None   # () — called when PLC trigger fires
        self.on_connect    = None   # () — called on successful connect
        self.on_disconnect = None   # () — called on disconnect/error

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
        self._trigger_debounce.set()  # release gate so poll thread can exit cleanly
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

    # ── User Signal ─────────────────────────────────────────

    def send_signal_high(self):
        """Write signal_coil HIGH — called when user presses 'Send HIGH'.

        The PLC should react to this rising edge by executing whatever
        preparation logic it needs and then asserting trigger_coil to
        request a solder-inspection capture from the app.
        """
        if not self.is_connected or not self.client:
            return
        try:
            self.client.write_coil(self.signal_coil, True)
            print(f"[PLC] Signal coil M{self.signal_coil} → HIGH (user triggered)")
        except Exception as e:
            print(f"[PLC] send_signal_high error: {e}")
            self._handle_comm_error()

    def send_signal_low(self):
        """Write signal_coil LOW — reset after PLC has acknowledged."""
        if not self.is_connected or not self.client:
            return
        try:
            self.client.write_coil(self.signal_coil, False)
            print(f"[PLC] Signal coil M{self.signal_coil} → LOW")
        except Exception as e:
            print(f"[PLC] send_signal_low error: {e}")
            self._handle_comm_error()

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
                    if self._trigger_debounce.is_set():
                        # Disarm gate immediately — prevents re-read double-fire
                        self._trigger_debounce.clear()
                        # Acknowledge: clear trigger coil then reset signal coil
                        self.client.write_coil(self.trigger_coil, False)
                        self.send_signal_low()
                        print("[PLC] Trigger coil fired — requesting capture")
                        if self.on_trigger:
                            self.on_trigger()
                        # Re-arm after 500 ms debounce window
                        threading.Timer(0.5, self._trigger_debounce.set).start()
                    else:
                        # Duplicate trigger within debounce window — just clear coil
                        print("[PLC] Duplicate trigger ignored (debounce active)")
                        try:
                            self.client.write_coil(self.trigger_coil, False)
                        except Exception:
                            pass
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
