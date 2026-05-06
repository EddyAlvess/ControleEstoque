#pragma once
#include <Arduino.h>

class KeypadInput {
public:
    void begin();
    char read();            // retorna '\0' se nenhuma tecla pressionada
    String readNumber();    // lê sequência numérica até '#' (confirma)
    bool available();
};

extern KeypadInput keypadInput;
