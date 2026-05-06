#pragma once
#include <Arduino.h>

class Display {
public:
    bool begin();
    void clear();
    void print(uint8_t row, const String& text);
    void print(uint8_t row, const char* text);
    void showTwoLines(const String& line1, const String& line2);
    void showMenu(const String* items, int count, int selected);
    void showProgress(const String& msg);
};

extern Display display;
