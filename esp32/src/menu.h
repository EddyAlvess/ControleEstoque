#pragma once
#include <Arduino.h>
#include "api_client.h"

enum MenuState {
    STATE_IDLE,
    STATE_SELECT_OPERATOR,
    STATE_SELECT_TYPE,
    STATE_SELECT_PRODUCT,
    STATE_ENTER_QUANTITY,
    STATE_CONFIRM,
    STATE_SEND,
    STATE_SUCCESS,
    STATE_ERROR,
};

class Menu {
public:
    void begin(Operator* ops, int opCount, Product* prods, int prodCount);
    void handleKey(char key);
    void handleScanner(const String& code);
    void render();
    MenuState getState() const { return _state; }

private:
    MenuState _state = STATE_IDLE;

    Operator* _operators;
    int       _opCount = 0;
    int       _opIdx   = 0;

    Product*  _products;
    int       _prodCount = 0;
    int       _prodIdx   = 0;

    bool      _isEntry = true;         // true = ENTRY, false = EXIT
    float     _quantity = 0.0f;
    String    _numBuf;
    String    _lastError;
    unsigned long _lastActivity = 0;

    void setState(MenuState s);
    void sendMovement();
    void renderIdle();
    void renderOperatorList();
    void renderTypeSelect();
    void renderProductList();
    void renderQuantityInput();
    void renderConfirm();
};

extern Menu menu;
