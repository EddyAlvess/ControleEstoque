#include "menu.h"
#include "config.h"
#include "display.h"
#include "api_client.h"

Menu menu;

void Menu::begin(Operator* ops, int opCount, Product* prods, int prodCount) {
    _operators  = ops;
    _opCount    = opCount;
    _products   = prods;
    _prodCount  = prodCount;
    setState(STATE_IDLE);
}

void Menu::setState(MenuState s) {
    _state = s;
    _lastActivity = millis();
    _numBuf = "";
}

// ── Entrada de tecla do teclado matricial ─────────────────────────────────────
void Menu::handleKey(char key) {
    if (key == '\0') return;
    _lastActivity = millis();

    switch (_state) {

    case STATE_IDLE:
        if (key == '#' || key == 'A' || key == 'B') {
            _opIdx = 0;
            setState(STATE_SELECT_OPERATOR);
        }
        break;

    case STATE_SELECT_OPERATOR:
        if (key == 'A' && _opIdx > 0)           _opIdx--;
        if (key == 'B' && _opIdx < _opCount - 1) _opIdx++;
        if (key == '#')  setState(STATE_SELECT_TYPE);
        if (key == '*')  setState(STATE_IDLE);
        break;

    case STATE_SELECT_TYPE:
        if (key == '1') { _isEntry = true;  setState(STATE_SELECT_PRODUCT); }
        if (key == '2') { _isEntry = false; setState(STATE_SELECT_PRODUCT); }
        if (key == '*') setState(STATE_SELECT_OPERATOR);
        break;

    case STATE_SELECT_PRODUCT:
        if (key == 'A' && _prodIdx > 0)              _prodIdx--;
        if (key == 'B' && _prodIdx < _prodCount - 1) _prodIdx++;
        if (key == '#') setState(STATE_ENTER_QUANTITY);
        if (key == '*') setState(STATE_SELECT_TYPE);
        break;

    case STATE_ENTER_QUANTITY:
        if (key >= '0' && key <= '9') {
            if (_numBuf.length() < 6) _numBuf += key;
        }
        if (key == '*') { _numBuf = _numBuf.length() > 0 ? _numBuf.substring(0, _numBuf.length()-1) : ""; }
        if (key == '#') {
            if (_numBuf.length() == 0) break;
            _quantity = _numBuf.toFloat();
            if (_quantity > 0) setState(STATE_CONFIRM);
        }
        if (key == 'B') setState(STATE_SELECT_PRODUCT);
        break;

    case STATE_CONFIRM:
        if (key == '#') setState(STATE_SEND);
        if (key == '*') setState(STATE_ENTER_QUANTITY);
        break;

    case STATE_SUCCESS:
    case STATE_ERROR:
        if (key != '\0') setState(STATE_IDLE);
        break;

    default: break;
    }
}

// ── Scanner de código de barras ───────────────────────────────────────────────
void Menu::handleScanner(const String& code) {
    _lastActivity = millis();
    if (_state == STATE_SELECT_OPERATOR) {
        for (int i = 0; i < _opCount; i++) {
            if (_operators[i].badge_code == code) {
                _opIdx = i;
                setState(STATE_SELECT_TYPE);
                return;
            }
        }
        display.showTwoLines("Cracha invalido", code);
        delay(2000);
    } else if (_state == STATE_SELECT_PRODUCT) {
        for (int i = 0; i < _prodCount; i++) {
            if (_products[i].name == code || String(i) == code) {
                _prodIdx = i;
                setState(STATE_ENTER_QUANTITY);
                return;
            }
        }
    }
}

// ── Envio HTTP ────────────────────────────────────────────────────────────────
void Menu::sendMovement() {
    display.showProgress("Enviando...");
    const char* type = _isEntry ? "ENTRY" : "EXIT";
    bool ok = apiClient.postMovement(
        type,
        _operators[_opIdx].id,
        _products[_prodIdx].id,
        _quantity,
        nullptr  // turno detectado automaticamente no api_client
    );
    setState(ok ? STATE_SUCCESS : STATE_ERROR);
    if (!ok) _lastError = "Erro de conexao";
}

// ── Renderização no LCD ───────────────────────────────────────────────────────
void Menu::render() {
    // Timeout de inatividade → volta ao início
    if (_state != STATE_IDLE && millis() - _lastActivity > MENU_IDLE_MS) {
        setState(STATE_IDLE);
    }

    switch (_state) {
    case STATE_IDLE:             renderIdle();          break;
    case STATE_SELECT_OPERATOR:  renderOperatorList();  break;
    case STATE_SELECT_TYPE:      renderTypeSelect();    break;
    case STATE_SELECT_PRODUCT:   renderProductList();   break;
    case STATE_ENTER_QUANTITY:   renderQuantityInput(); break;
    case STATE_CONFIRM:          renderConfirm();       break;
    case STATE_SEND:             sendMovement();        break;
    case STATE_SUCCESS:
        display.showTwoLines("Registrado!", "Pressione #");
        break;
    case STATE_ERROR:
        display.showTwoLines("Erro:", _lastError);
        break;
    }
}

void Menu::renderIdle() {
    display.showTwoLines("SorvPel Estoque", "Pressione # para");
}

void Menu::renderOperatorList() {
    if (_opCount == 0) { display.showTwoLines("Sem operadores", "Contate admin"); return; }
    String items[_opCount];
    for (int i = 0; i < _opCount; i++) items[i] = _operators[i].name;
    display.showMenu(items, _opCount, _opIdx);
}

void Menu::renderTypeSelect() {
    display.showTwoLines("1-Entrada  2-Sai", "* = Voltar");
}

void Menu::renderProductList() {
    if (_prodCount == 0) { display.showTwoLines("Sem produtos", "Contate admin"); return; }
    String items[_prodCount];
    for (int i = 0; i < _prodCount; i++) items[i] = _products[i].name;
    display.showMenu(items, _prodCount, _prodIdx);
}

void Menu::renderQuantityInput() {
    String label = _isEntry ? "Entrada: " : "Saida: ";
    display.showTwoLines(label + _products[_prodIdx].name,
                         "Qtd: " + (_numBuf.length() ? _numBuf : "0") + " " + _products[_prodIdx].unit);
}

void Menu::renderConfirm() {
    String tipo = _isEntry ? "ENT" : "SAI";
    display.showTwoLines(
        tipo + ":" + _products[_prodIdx].name.substring(0, 10),
        "Qtd:" + String(_quantity) + " # Conf *Canc"
    );
}
