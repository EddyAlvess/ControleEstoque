#include "display.h"
#include "config.h"
#include <LiquidCrystal_I2C.h>

static LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);
static bool lcdOk = false;

Display display;

bool Display::begin() {
    Wire.begin();
    lcd.init();
    lcd.backlight();
    lcdOk = true;
    lcd.clear();
    return true;
}

void Display::clear() {
    if (lcdOk) lcd.clear();
}

void Display::print(uint8_t row, const String& text) {
    if (!lcdOk) { Serial.println(text); return; }
    lcd.setCursor(0, row);
    String padded = text;
    while ((int)padded.length() < LCD_COLS) padded += ' ';
    lcd.print(padded.substring(0, LCD_COLS));
}

void Display::print(uint8_t row, const char* text) {
    print(row, String(text));
}

void Display::showTwoLines(const String& line1, const String& line2) {
    print(0, line1);
    print(1, line2);
}

void Display::showMenu(const String* items, int count, int selected) {
    if (count == 0) return;
    // Mostra item selecionado na linha 0 com seta, próximo na linha 1
    String l0 = String("> ") + items[selected];
    String l1 = (selected + 1 < count) ? String("  ") + items[selected + 1] : String("  [fim]");
    showTwoLines(l0, l1);
}

void Display::showProgress(const String& msg) {
    print(0, msg);
    print(1, "Aguarde...");
}
