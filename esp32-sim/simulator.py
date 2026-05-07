#!/usr/bin/env python3
"""
Simulador de terminal ESP32 para SorvPel ControleEstoque.
Replica a maquina de estados de esp32/src/menu.cpp — display LCD 20x4.
"""

import os
import time
import curses
import threading
import requests
from datetime import datetime
from enum import Enum

LCD_COLS = 20
LCD_ROWS = 4

SERVER_URL   = os.getenv("SERVER_URL", "http://nginx").rstrip("/")
API_KEY      = os.getenv("API_KEY", "")
DEVICE_ID    = os.getenv("DEVICE_ID", "SIM-TERMINAL-01")
IDLE_TIMEOUT = int(os.getenv("MENU_IDLE_MS", "60000")) / 1000.0

_shifts: list[dict] = []


class State(Enum):
    IDLE             = "IDLE"
    SELECT_OPERATOR  = "SELECT_OPERATOR"
    ENTER_PIN        = "ENTER_PIN"
    SELECT_TYPE      = "SELECT_TYPE"
    SELECT_PRODUCT   = "SELECT_PRODUCT"
    ENTER_QUANTITY   = "ENTER_QUANTITY"
    CONFIRM          = "CONFIRM"
    SEND             = "SEND"
    SUCCESS          = "SUCCESS"
    ERROR            = "ERROR"


def current_shift() -> str:
    hour = datetime.now().hour
    for s in _shifts:
        if not s.get("is_active", True):
            continue
        start, end = s["start_hour"], s["end_hour"]
        if start < end:
            if start <= hour < end:
                return s["name"]
        else:
            if hour >= start or hour < end:
                return s["name"]
    return "SEM TURNO"


# ── State machine ─────────────────────────────────────────────────────────────

class Simulator:
    def __init__(self):
        self.state             = State.IDLE
        self.operators: list[dict] = []
        self.op_idx            = 0
        self.selected_op: dict = {}
        self.selected_prod: dict = {}
        self.is_entry          = True
        self.num_buf           = ""   # quantidade ou PIN
        self.code_buf          = ""   # código de produto
        self.quantity          = 0.0
        self.last_activity     = time.monotonic()
        self.error_msg         = ""
        self.last_movement_id: int | None = None
        self.lcd: list[str]    = [" " * LCD_COLS] * LCD_ROWS
        self.log: list[str]    = []
        self._lock             = threading.Lock()

    def _set_lcd(self, *lines):
        result = []
        for i in range(LCD_ROWS):
            raw = lines[i] if i < len(lines) else ""
            result.append(raw[:LCD_COLS].ljust(LCD_COLS))
        with self._lock:
            self.lcd = result

    def add_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.log.append(f"[{ts}] {msg}")
            if len(self.log) > 200:
                self.log.pop(0)

    def _go(self, new_state: State):
        self.state = new_state
        self.last_activity = time.monotonic()
        self._render()

    def _list_lines(self, items: list[str], selected: int) -> list[str]:
        n = len(items)
        if n == 0:
            return ["", "", ""]
        start = max(0, min(selected - 1, n - 3))
        rows = []
        for slot in range(3):
            idx = start + slot
            if idx >= n:
                rows.append("")
                continue
            prefix = "> " if idx == selected else "  "
            rows.append(f"{prefix}{items[idx][:18]}")
        return rows

    # ── render ────────────────────────────────────────────────────────────────

    def _render(self):
        s = self.state

        if s == State.IDLE:
            self._set_lcd(
                "  SorvPel Estoque   ",
                "--------------------",
                "   Pressione # para ",
                "       iniciar      ",
            )

        elif s == State.SELECT_OPERATOR:
            if not self.operators:
                self._set_lcd(
                    "- Selec. Operador --",
                    "  Sem operadores!   ",
                    "  Cheque servidor.  ",
                    "",
                )
                return
            nomes = [op["name"] for op in self.operators]
            r1, r2, r3 = self._list_lines(nomes, self.op_idx)
            self._set_lcd("- Selec. Operador --", r1, r2, r3)

        elif s == State.ENTER_PIN:
            op_name = self.selected_op.get("name", "?")
            masked  = "*" * len(self.num_buf) if self.num_buf else ""
            self._set_lcd(
                "--- Senha Operador -",
                f"Op: {op_name[:16]}",
                f"PIN: {masked:<15}",
                "#=ok  *=apaga  Esc=vol",
            )

        elif s == State.SELECT_TYPE:
            self._set_lcd(
                "-- Tipo Movimento --",
                "",
                "  [1] Entrada       ",
                "  [2] Saida  *=volta",
            )

        elif s == State.SELECT_PRODUCT:
            tipo = "Entrada" if self.is_entry else "Saida"
            code = self.code_buf or ""
            self._set_lcd(
                f"-{tipo}: Cod Produto-",
                f"Digite: {code:<12}",
                "",
                "#=ok  *=apaga  Esc=vol",
            )

        elif s == State.ENTER_QUANTITY:
            p    = self.selected_prod
            op   = self.selected_op
            tipo = "Entrada" if self.is_entry else "Saida"
            unit = p.get("unit", "")
            qtd  = self.num_buf or "0"
            self._set_lcd(
                f"{tipo}: {p.get('name','?')[:13]}",
                f"Op: {op.get('name','?')[:16]}",
                f"Qtd: {qtd} {unit}"[:LCD_COLS],
                "#=ok  *=apaga  B=vol",
            )

        elif s == State.CONFIRM:
            op   = self.selected_op
            p    = self.selected_prod
            tipo = "ENT" if self.is_entry else "SAI"
            unit = p.get("unit", "")
            self._set_lcd(
                "--- Confirmar Env. -",
                f"{tipo}: {p.get('name','?')[:15]}",
                f"Op:{op.get('name','?')[:10]} {self.num_buf}{unit}"[:LCD_COLS],
                "#=enviar  *=cancelar",
            )

        elif s == State.SEND:
            self._set_lcd("", "    Enviando...     ", "    Aguarde...      ", "")

        elif s == State.SUCCESS:
            mid = f"   id: {self.last_movement_id}" if self.last_movement_id else ""
            self._set_lcd("", "  Registrado! OK    ", mid, "  Pressione #       ")

        elif s == State.ERROR:
            self._set_lcd("", "  Erro:             ", f"  {self.error_msg[:17]}", "  Pressione #       ")

    # ── handle_key ────────────────────────────────────────────────────────────

    def handle_key(self, key: str):
        self.last_activity = time.monotonic()
        s = self.state

        if s == State.IDLE:
            if key in ("#", "A", "B"):
                self.op_idx = 0
                self._go(State.SELECT_OPERATOR)

        elif s == State.SELECT_OPERATOR:
            if key == "#":
                if self.operators:
                    self.selected_op = self.operators[self.op_idx]
                    self.num_buf = ""
                    self._go(State.ENTER_PIN)
            elif key == "*":
                self._go(State.IDLE)
            elif key == "A" and self.op_idx > 0:
                self.op_idx -= 1; self._render()
            elif key == "B" and self.op_idx + 1 < len(self.operators):
                self.op_idx += 1; self._render()

        elif s == State.ENTER_PIN:
            if key.isdigit() and len(self.num_buf) < 8:
                self.num_buf += key; self._render()
            elif key == "*":
                if self.num_buf:
                    self.num_buf = self.num_buf[:-1]; self._render()
                else:
                    self.num_buf = ""
                    self._go(State.SELECT_OPERATOR)
            elif key == "#":
                if self.num_buf:
                    threading.Thread(target=self._verify_pin, daemon=True).start()

        elif s == State.SELECT_TYPE:
            if key == "1":
                self.is_entry = True;  self.code_buf = ""; self._go(State.SELECT_PRODUCT)
            elif key == "2":
                self.is_entry = False; self.code_buf = ""; self._go(State.SELECT_PRODUCT)
            elif key == "*":
                self._go(State.SELECT_OPERATOR)

        elif s == State.SELECT_PRODUCT:
            if key.isdigit() and len(self.code_buf) < 10:
                self.code_buf += key; self._render()
            elif key == "*":
                if self.code_buf:
                    self.code_buf = self.code_buf[:-1]; self._render()
                else:
                    self._go(State.SELECT_TYPE)
            elif key == "#":
                if self.code_buf:
                    threading.Thread(target=self._lookup_product, args=(self.code_buf,), daemon=True).start()

        elif s == State.ENTER_QUANTITY:
            if key.isdigit() and len(self.num_buf) < 6:
                self.num_buf += key; self._render()
            elif key == "*":
                if self.num_buf:
                    self.num_buf = self.num_buf[:-1]; self._render()
                else:
                    self.code_buf = ""; self._go(State.SELECT_PRODUCT)
            elif key == "#":
                if self.num_buf and float(self.num_buf) > 0:
                    self.quantity = float(self.num_buf); self._go(State.CONFIRM)
            elif key == "B":
                self.code_buf = ""; self._go(State.SELECT_PRODUCT)

        elif s == State.CONFIRM:
            if key == "#":
                self._go(State.SEND)
                threading.Thread(target=self._send_movement, daemon=True).start()
            elif key == "*":
                self._go(State.ENTER_QUANTITY)

        elif s in (State.SUCCESS, State.ERROR):
            self.num_buf = ""; self.code_buf = ""
            self._go(State.IDLE)

    # ── handle_scanner ────────────────────────────────────────────────────────

    def handle_scanner(self, code: str):
        code = code.strip()
        self.last_activity = time.monotonic()
        s = self.state

        if s == State.SELECT_OPERATOR:
            for i, op in enumerate(self.operators):
                if op.get("badge_code") == code:
                    self.op_idx = i
                    self.selected_op = op
                    self.add_log(f"Scanner: operador '{op['name']}'")
                    self.num_buf = ""
                    self._go(State.ENTER_PIN)
                    return
            self.add_log(f"Scanner: badge '{code}' nao encontrado")

        elif s == State.SELECT_PRODUCT:
            self.code_buf = code
            threading.Thread(target=self._lookup_product, args=(code,), daemon=True).start()

    def check_idle_timeout(self):
        if self.state not in (State.IDLE, State.SEND):
            if time.monotonic() - self.last_activity >= IDLE_TIMEOUT:
                self.add_log("Timeout: retornando ao IDLE")
                self._go(State.IDLE)

    # ── API calls ─────────────────────────────────────────────────────────────

    def fetch_data(self):
        global _shifts
        self._set_lcd("   Conectando...    ", "  Buscando dados... ", "", "")
        headers = {"X-API-Key": API_KEY}

        try:
            r = requests.get(f"{SERVER_URL}/api/v1/operators", headers=headers, timeout=8)
            r.raise_for_status()
            self.operators = r.json()
            self.add_log(f"GET /api/v1/operators -> {len(self.operators)} registros")
        except Exception as e:
            self.add_log(f"ERRO /api/v1/operators: {e}")

        try:
            r = requests.get(f"{SERVER_URL}/api/v1/shifts", headers=headers, timeout=8)
            r.raise_for_status()
            _shifts = r.json()
            self.add_log(f"GET /api/v1/shifts    -> {len(_shifts)} turnos")
        except Exception as e:
            self.add_log(f"ERRO /api/v1/shifts: {e}")

        self._go(State.IDLE)

    def _verify_pin(self):
        """Valida o PIN do operador via API (chamado em thread separada)."""
        op_id = self.selected_op.get("id")
        pin   = self.num_buf
        self.add_log(f"POST /api/v1/operators/{op_id}/verify-pin")
        try:
            r = requests.post(
                f"{SERVER_URL}/api/v1/operators/{op_id}/verify-pin",
                json={"pin": pin},
                headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
                timeout=8,
            )
            if r.status_code == 200:
                self.add_log(f"PIN OK: operador {self.selected_op.get('name')}")
                self.num_buf = ""
                self._go(State.SELECT_TYPE)
            elif r.status_code == 401:
                self.add_log("PIN incorreto")
                self.error_msg = "PIN incorreto"
                self._set_lcd(
                    "--- Senha Operador -",
                    f"Op: {self.selected_op.get('name','?')[:16]}",
                    "  PIN INCORRETO!    ",
                    "  Esc=voltar        ",
                )
                time.sleep(2)
                self.num_buf = ""
                self._go(State.ENTER_PIN)
            else:
                detail = r.json().get("detail", f"HTTP {r.status_code}")
                self.add_log(f"Erro verify-pin: {detail}")
                self.error_msg = detail[:17]
                self._set_lcd(
                    "--- Senha Operador -",
                    f"Op: {self.selected_op.get('name','?')[:16]}",
                    f"  {self.error_msg}",
                    "  Esc=voltar        ",
                )
                time.sleep(2)
                self.num_buf = ""
                self._go(State.ENTER_PIN)
        except Exception as e:
            self.add_log(f"ERRO verify-pin: {e}")
            self.error_msg = str(e)[:17]
            self.num_buf = ""
            self._go(State.ENTER_PIN)

    def _lookup_product(self, sku: str):
        """Busca produto pelo código SKU via API (chamado em thread separada)."""
        self.add_log(f"GET /api/v1/products/by-sku/{sku}")
        self._set_lcd(
            "-- Buscando Prod. --",
            f"Cod: {sku[:14]}",
            "  Aguarde...        ",
            "",
        )
        try:
            r = requests.get(
                f"{SERVER_URL}/api/v1/products/by-sku/{sku}",
                headers={"X-API-Key": API_KEY},
                timeout=8,
            )
            if r.status_code == 200:
                prod = r.json()
                self.selected_prod = prod
                self.add_log(f"Produto: {prod['name']} (SKU {sku})")
                self.num_buf = ""
                self._go(State.ENTER_QUANTITY)
            elif r.status_code == 404:
                self.add_log(f"SKU '{sku}' nao encontrado")
                self._set_lcd(
                    "-- Cod. Produto ----",
                    f"  '{sku[:14]}'",
                    "  Nao encontrado!   ",
                    "  *=apaga  Esc=vol  ",
                )
                time.sleep(2)
                self._go(State.SELECT_PRODUCT)
            else:
                self.add_log(f"ERRO lookup produto: HTTP {r.status_code}")
                self._go(State.SELECT_PRODUCT)
        except Exception as e:
            self.add_log(f"ERRO lookup produto: {e}")
            self._go(State.SELECT_PRODUCT)

    def _send_movement(self):
        op   = self.selected_op
        prod = self.selected_prod
        payload = {
            "movement_type": "ENTRY" if self.is_entry else "EXIT",
            "operator_id":   op["id"],
            "product_id":    prod["id"],
            "quantity":      self.quantity,
            "shift":         current_shift(),
            "device_id":     DEVICE_ID,
            "recorded_at":   datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.add_log(
            f"POST movements: {payload['movement_type']} "
            f"{prod['name']} x{self.quantity} ({payload['shift']})"
        )
        try:
            headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
            r = requests.post(
                f"{SERVER_URL}/api/v1/movements",
                json=payload, headers=headers, timeout=8,
            )
            if r.status_code == 201:
                data = r.json()
                self.last_movement_id = data.get("id")
                self.add_log(f"OK: movimento id={self.last_movement_id} registrado")
                self._go(State.SUCCESS)
            else:
                self.error_msg = f"HTTP {r.status_code}"
                self.add_log(f"ERRO: {r.status_code} - {r.text[:100]}")
                self._go(State.ERROR)
        except Exception as e:
            self.error_msg = str(e)[:17]
            self.add_log(f"ERRO: {e}")
            self._go(State.ERROR)


# ── Curses UI ─────────────────────────────────────────────────────────────────

_KEY_HINTS = {
    State.IDLE:            "Enter/#=iniciar",
    State.SELECT_OPERATOR: "Seta UP/A=anterior  Seta DN/B=proximo  Enter/#=ok  Esc/*=voltar",
    State.ENTER_PIN:       "0-9=digitar PIN  *=apagar  Enter/#=confirmar  Esc/*=voltar",
    State.SELECT_TYPE:     "1=Entrada  2=Saida  Esc/*=voltar",
    State.SELECT_PRODUCT:  "0-9=digitar codigo SKU  *=apagar  Enter/#=confirmar  Esc=voltar",
    State.ENTER_QUANTITY:  "0-9=digitar  *=apagar ultimo  Enter/#=ok  B=voltar produto",
    State.CONFIRM:         "Enter/#=enviar ao servidor  Esc/*=cancelar",
    State.SEND:            "Aguardando resposta do servidor...",
    State.SUCCESS:         "Qualquer tecla para voltar ao inicio",
    State.ERROR:           "Qualquer tecla para voltar ao inicio",
}


def _safe(win, row, col, text, attr=0):
    try:
        win.addstr(row, col, text, attr)
    except curses.error:
        pass


def run_ui(stdscr, sim: Simulator):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_CYAN,  -1)
        curses.init_pair(3, curses.COLOR_WHITE, -1)
        curses.init_pair(4, curses.COLOR_RED,   -1)
        curses.init_pair(5, curses.COLOR_BLACK, -1)

    C_LCD = curses.color_pair(1) if curses.has_colors() else 0
    C_HDR = (curses.color_pair(2) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD
    C_NRM = curses.color_pair(3) if curses.has_colors() else 0
    C_ERR = (curses.color_pair(4) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD
    C_DIM = curses.color_pair(5) if curses.has_colors() else curses.A_DIM

    LCD_WIN_H = LCD_ROWS + 2
    LCD_WIN_W = LCD_COLS + 4

    scanner_mode = False
    scanner_buf  = ""

    threading.Thread(target=sim.fetch_data, daemon=True).start()

    while True:
        sim.check_idle_timeout()
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        title = f" ESP32 Simulator — LCD {LCD_COLS}x{LCD_ROWS} — SorvPel "
        _safe(stdscr, 0, max(0, (w - len(title)) // 2), title, C_HDR)

        lcd_row = 2
        lcd_col = max(0, (w - LCD_WIN_W) // 2)

        if h > lcd_row + LCD_WIN_H:
            lcd_win = curses.newwin(LCD_WIN_H, LCD_WIN_W, lcd_row, lcd_col)
            lcd_win.attron(C_HDR); lcd_win.box(); lcd_win.attroff(C_HDR)
            _safe(lcd_win, 0, 2, f" LCD {LCD_COLS}x{LCD_ROWS} ", C_HDR)
            with sim._lock:
                lines = list(sim.lcd)
            for r, line in enumerate(lines[:LCD_ROWS]):
                _safe(lcd_win, r + 1, 2, line[:LCD_COLS], C_LCD)
            lcd_win.refresh()

        info_row = lcd_row + LCD_WIN_H + 1
        _safe(stdscr, info_row, 2, f"Estado : {sim.state.value}", C_HDR)
        hint = _KEY_HINTS.get(sim.state, "")
        _safe(stdscr, info_row + 1, 2, f"Teclas : {hint}"[:w-3], C_NRM)

        scan_row = info_row + 2
        if scanner_mode:
            _safe(stdscr, scan_row, 2,
                  f" [SCANNER] Codigo: {scanner_buf}_  (Enter=ok  Esc=cancela)"[:w-3], C_ERR)
        else:
            _safe(stdscr, scan_row, 2,
                  "  S=scanner  R=recarregar dados  Q=sair", C_DIM)

        div = scan_row + 2
        _safe(stdscr, div, 0, "─" * max(0, w - 1), C_HDR)
        _safe(stdscr, div, 2, " Log chamadas API ", C_HDR)

        with sim._lock:
            log_snap = list(sim.log)
        for i, line in enumerate(log_snap[-(h - div - 2):]):
            row = div + 1 + i
            if row >= h - 1:
                break
            _safe(stdscr, row, 2, line[:w-3], C_NRM)

        stdscr.refresh()

        try:
            ch = stdscr.getch()
        except Exception:
            ch = -1

        if ch == -1:
            continue

        if scanner_mode:
            if ch in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                if scanner_buf:
                    sim.handle_scanner(scanner_buf)
                scanner_buf = ""; scanner_mode = False
            elif ch == 27:
                scanner_buf = ""; scanner_mode = False
            elif 32 <= ch < 127:
                scanner_buf += chr(ch)
            continue

        if ch in (ord('q'), ord('Q')):
            break
        elif ch in (ord('s'), ord('S')):
            scanner_mode = True; scanner_buf = ""
        elif ch in (ord('r'), ord('R')):
            sim.add_log("Recarregando operadores e turnos...")
            threading.Thread(target=sim.fetch_data, daemon=True).start()
        elif ch in (ord('\n'), ord('\r'), curses.KEY_ENTER, ord('#')):
            sim.handle_key('#')
        elif ch == 27:
            sim.handle_key('*')
        elif ch == ord('*'):
            sim.handle_key('*')
        elif ch in (curses.KEY_UP, ord('a'), ord('A')):
            sim.handle_key('A')
        elif ch in (curses.KEY_DOWN, ord('b'), ord('B')):
            sim.handle_key('B')
        elif ord('0') <= ch <= ord('9'):
            sim.handle_key(chr(ch))


def main():
    sim = Simulator()
    try:
        curses.wrapper(lambda stdscr: run_ui(stdscr, sim))
    except KeyboardInterrupt:
        pass
    print("Simulador encerrado.")


if __name__ == "__main__":
    main()
