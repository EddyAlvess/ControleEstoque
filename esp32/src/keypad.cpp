#include "keypad.h"
#include "config.h"
#include <Keypad.h>

// Layout padrão teclado 4x4
static const byte ROWS = 4;
static const byte COLS = 4;
static char keys[ROWS][COLS] = {
    {'1','2','3','A'},
    {'4','5','6','B'},
    {'7','8','9','C'},
    {'*','0','#','D'}
};
// A = scroll cima/anterior   B = scroll baixo/próximo
// # = confirmar              * = cancelar/voltar

static byte rowPins[ROWS] = {KP_ROW1, KP_ROW2, KP_ROW3, KP_ROW4};
static byte colPins[COLS] = {KP_COL1, KP_COL2, KP_COL3, KP_COL4};
static Keypad kp = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

KeypadInput keypadInput;

void KeypadInput::begin() {
    kp.setDebounceTime(50);
}

char KeypadInput::read() {
    return kp.getKey();
}

bool KeypadInput::available() {
    return kp.getKeys();
}

String KeypadInput::readNumber() {
    String num = "";
    while (true) {
        char k = kp.waitForKey();
        if (k == '#') break;
        if (k == '*') return "";   // cancelado
        if (k >= '0' && k <= '9') num += k;
    }
    return num;
}
