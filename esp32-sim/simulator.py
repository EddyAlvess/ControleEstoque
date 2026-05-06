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


class State(Enum):
    IDLE            = "IDLE"
    SELECT_OPERATOR = "SELECT_OPERATOR"
    SELECT_TYPE     = "SELECT_TYPE"
    SELECT_PRODUCT  = "SELECT_PRODUCT"
    ENTER_QUANTITY  = "ENTER_QUANTITY"
    CONFIRM         = "CONFIRM"
    SEND            = "SEND"
    SUCCESS         = "SUCCESS"
    ERROR           = "ERROR"


def current_shift() -> str:
    h = datetime.now().hour
    if 6 <= h < 14:
        return "MORNING"
    if 14 <= h < 22:
        return "AFTERNOON"
    return "NIGHT"


# ── State machine ─────────────────────────────────────────────────────────────

class Simulator:
    def __init__(self):
        self.state          = State.IDLE
        self.operators: list[dict] = []
        self.products:  list[dict] = []
        self.op_idx         = 0
        self.prod_idx       = 0
        self.is_entry       = True
        self.num_buf        = ""
        self.quantity       = 0.0
        self.last_activity  = time.monotonic()
        self.error_msg      = ""
        self.last_movement_id: int | None = None
        self.lcd: list[str] = [" " * LCD_COLS] * LCD_ROWS
        self.log: list[str] = []
        self._lock          = threading.Lock()

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

    # ── helpers para listas de 3 linhas ──────────────────────────────────────

    def _list_lines(self, items: list[str], selected: int) -> list[str]:
        """Retorna 3 linhas com scroll, seta > no item selecionado."""
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
        s     = self.state
        ops   = self.operators
        prods = self.products

        if s == State.IDLE:
            self._set_lcd(
                "  SorvPel Estoque   ",
                "--------------------",
                "   Pressione # para ",
                "       iniciar      ",
            )

        elif s == State.SELECT_OPERATOR:
            if not ops:
                self._set_lcd(
                    "- Selec. Operador --",
                    "  Sem operadores!   ",
                    "  Cheque servidor.  ",
                    "",
                )
                return
            nomes = [op["name"] for op in ops]
            r1, r2, r3 = self._list_lines(nomes, self.op_idx)
            self._set_lcd("- Selec. Operador --", r1, r2, r3)

        elif s == State.SELECT_TYPE:
            self._set_lcd(
                "-- Tipo Movimento --",
                "",
                "  [1] Entrada       ",
                "  [2] Saida  *=volta",
            )

        elif s == State.SELECT_PRODUCT:
            if not prods:
                self._set_lcd(
                    "-- Selec. Produto --",
                    "  Sem produtos!     ",
                    "  Cheque servidor.  ",
                    "",
                )
                return
            tipo = "Entrada" if self.is_entry else "Saida"
            nomes = [p["name"] for p in prods]
            r1, r2, r3 = self._list_lines(nomes, self.prod_idx)
            self._set_lcd(f"--{tipo}: Produto----", r1, r2, r3)

        elif s == State.ENTER_QUANTITY:
            if not prods:
                return
            p    = prods[self.prod_idx]
            op   = ops[self.op_idx] if ops else {"name": "?"}
            tipo = "Entrada" if self.is_entry else "Saida"
            unit = p.get("unit", "")
            qtd  = self.num_buf or "0"
            self._set_lcd(
                f"{tipo}: {p['name'][:13]}",
                f"Op: {op['name'][:16]}",
                f"Qtd: {qtd} {unit}"[:LCD_COLS],
                "#=ok  *=apaga  B=vol",
            )

        elif s == State.CONFIRM:
            if not prods or not ops:
                return
            op   = ops[self.op_idx]
            p    = prods[self.prod_idx]
            tipo = "ENT" if self.is_entry else "SAI"
            unit = p.get("unit", "")
            self._set_lcd(
                "--- Confirmar Env. -",
                f"{tipo}: {p['name'][:15]}",
                f"Op:{op['name'][:10]} {self.num_buf}{unit}"[:LCD_COLS],
                "#=enviar  *=cancelar",
            )

        elif s == State.SEND:
            self._set_lcd(
                "",
                "    Enviando...     ",
                "    Aguarde...      ",
                "",
            )

        elif s == State.SUCCESS:
            mid = f"   id: {self.last_movement_id}" if self.last_movement_id else ""
            self._set_lcd(
                "",
                "  Registrado! OK    ",
                mid,
                "  Pressione #       ",
            )

        elif s == State.ERROR:
            self._set_lcd(
                "",
                "  Erro:             ",
                f"  {self.error_msg[:17]}",
                "  Pressione #       ",
            )

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
                    self.prod_idx = 0
                    self._go(State.SELECT_TYPE)
            elif key == "*":
                self._go(State.IDLE)
            elif key == "A" and self.op_idx > 0:
                self.op_idx -= 1; self._render()
            elif key == "B" and self.op_idx + 1 < len(self.operators):
                self.op_idx += 1; self._render()

        elif s == State.SELECT_TYPE:
            if key == "1":
                self.is_entry = True;  self.prod_idx = 0; self._go(State.SELECT_PRODUCT)
            elif key == "2":
                self.is_entry = False; self.prod_idx = 0; self._go(State.SELECT_PRODUCT)
            elif key == "*":
                self._go(State.SELECT_OPERATOR)

        elif s == State.SELECT_PRODUCT:
            if key == "#":
                if self.products:
                    self.num_buf = ""; self._go(State.ENTER_QUANTITY)
            elif key == "*":
                self._go(State.SELECT_TYPE)
            elif key == "A" and self.prod_idx > 0:
                self.prod_idx -= 1; self._render()
            elif key == "B" and self.prod_idx + 1 < len(self.products):
                self.prod_idx += 1; self._render()

        elif s == State.ENTER_QUANTITY:
            if key.isdigit() and len(self.num_buf) < 6:
                self.num_buf += key; self._render()
            elif key == "*":
                if self.num_buf:
                    self.num_buf = self.num_buf[:-1]; self._render()
                else:
                    self._go(State.SELECT_PRODUCT)
            elif key == "#":
                if self.num_buf and float(self.num_buf) > 0:
                    self.quantity = float(self.num_buf); self._go(State.CONFIRM)
            elif key == "B":
                self._go(State.SELECT_PRODUCT)

        elif s == State.CONFIRM:
            if key == "#":
                self._go(State.SEND)
                threading.Thread(target=self._send_movement, daemon=True).start()
            elif key == "*":
                self._go(State.ENTER_QUANTITY)

        elif s in (State.SUCCESS, State.ERROR):
            self.op_idx = 0; self.prod_idx = 0; self.num_buf = ""
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
                    self.add_log(f"Scanner: operador '{op['name']}'")
                    self.prod_idx = 0; self._go(State.SELECT_TYPE); return
            self.add_log(f"Scanner: badge '{code}' nao encontrado")

        elif s == State.SELECT_PRODUCT:
            for i, prod in enumerate(self.products):
                if prod.get("name") == code or str(i) == code:
                    self.prod_idx = i
                    self.add_log(f"Scanner: produto '{prod['name']}'")
                    self.num_buf = ""; self._go(State.ENTER_QUANTITY); return
            self.add_log(f"Scanner: produto '{code}' nao encontrado")

    def check_idle_timeout(self):
        if self.state not in (State.IDLE, State.SEND):
            if time.monotonic() - self.last_activity >= IDLE_TIMEOUT:
                self.add_log("Timeout: retornando ao IDLE")
                self._go(State.IDLE)

    # ── API calls ─────────────────────────────────────────────────────────────

    def fetch_data(self):
        self._set_lcd(
            "   Conectando...    ",
            "  Buscando dados... ",
            "",
            "",
        )
        headers = {"X-API-Key": API_KEY}
        try:
            r = requests.get(f"{SERVER_URL}/api/v1/operators", headers=headers, timeout=8)
            r.raise_for_status()
            self.operators = r.json()
            self.add_log(f"GET /api/v1/operators -> {len(self.operators)} registros")
        except Exception as e:
            self.add_log(f"ERRO /api/v1/operators: {e}")

        try:
            r = requests.get(f"{SERVER_URL}/api/v1/products", headers=headers, timeout=8)
            r.raise_for_status()
            self.products = r.json()
            self.add_log(f"GET /api/v1/products  -> {len(self.products)} registros")
        except Exception as e:
            self.add_log(f"ERRO /api/v1/products: {e}")

        self._go(State.IDLE)

    def _send_movement(self):
        op   = self.operators[self.op_idx]
        prod = self.products[self.prod_idx]
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
    State.SELECT_TYPE:     "1=Entrada  2=Saida  Esc/*=voltar",
    State.SELECT_PRODUCT:  "Seta UP/A=anterior  Seta DN/B=proximo  Enter/#=ok  Esc/*=voltar",
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
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)  # LCD texto
        curses.init_pair(2, curses.COLOR_CYAN,  -1)                  # bordas/titulos
        curses.init_pair(3, curses.COLOR_WHITE, -1)                  # normal
        curses.init_pair(4, curses.COLOR_RED,   -1)                  # erro/scanner
        curses.init_pair(5, curses.COLOR_BLACK, -1)                  # dim

    C_LCD = curses.color_pair(1) if curses.has_colors() else 0
    C_HDR = (curses.color_pair(2) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD
    C_NRM = curses.color_pair(3) if curses.has_colors() else 0
    C_ERR = (curses.color_pair(4) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD
    C_DIM = curses.color_pair(5) if curses.has_colors() else curses.A_DIM

    # LCD box: LCD_ROWS linhas + 2 borda + 1 titulo = LCD_ROWS+2 rows de altura
    # largura: LCD_COLS + 4 (2 borda + 2 padding)
    LCD_WIN_H = LCD_ROWS + 2
    LCD_WIN_W = LCD_COLS + 4

    scanner_mode = False
    scanner_buf  = ""

    threading.Thread(target=sim.fetch_data, daemon=True).start()

    while True:
        sim.check_idle_timeout()
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        # ── Titulo ────────────────────────────────────────────────────────────
        title = f" ESP32 Simulator — LCD {LCD_COLS}x{LCD_ROWS} — SorvPel "
        _safe(stdscr, 0, max(0, (w - len(title)) // 2), title, C_HDR)

        # ── LCD box ───────────────────────────────────────────────────────────
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

        # ── Estado + dica de teclas ───────────────────────────────────────────
        info_row = lcd_row + LCD_WIN_H + 1
        _safe(stdscr, info_row, 2, f"Estado : {sim.state.value}", C_HDR)
        hint = _KEY_HINTS.get(sim.state, "")
        _safe(stdscr, info_row + 1, 2, f"Teclas : {hint}"[:w-3], C_NRM)

        # ── Scanner prompt ────────────────────────────────────────────────────
        scan_row = info_row + 2
        if scanner_mode:
            _safe(stdscr, scan_row, 2,
                  f" [SCANNER] Codigo: {scanner_buf}_  (Enter=ok  Esc=cancela)"[:w-3],
                  C_ERR)
        else:
            _safe(stdscr, scan_row, 2,
                  "  S=scanner  R=recarregar dados  Q=sair", C_DIM)

        # ── Divisor + Log ─────────────────────────────────────────────────────
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

        # ── Input ─────────────────────────────────────────────────────────────
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
            sim.add_log("Recarregando operadores e produtos...")
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
