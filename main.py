# main.py
import os
import random
import time
from threading import Thread, Event as ThreadEvent
from datetime import datetime

import win32api
import win32con
import win32gui

import keyboard_detector
from admin_privileges import running_as_admin
from device_validation import DeviceValidation
from windowcapture import WindowCapture

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- Güvenlik / startup ---
registered_devices = ['20-0B-74-35-B3-8E', '20-0B-74-35-B3-8F', 'D0-AD-08-64-48-C6']
device_registration = DeviceValidation(registered_devices)
running_as_admin()

keyboard_monitor = keyboard_detector.KeyboardDetector()
keyboard_monitor.start()

window_name = 'Rise Online Client'
window = WindowCapture(window_name=window_name)
hwnd = window.get_hwnd()

# --- Tuş kodları ---
R = 0x52
Z = 0x5A
ONE = 0x31
M_KEY = 0x4D
F_KEY = 0x46

# --- Ekran koordinatları ---
TELEPORT = (-586, 990)
PROTEAN_GATE = (-976, 412)
GO_TO = (-821, 752)
SIEANA_VILLAGE = (-1104, 561)
TRAVEL = (-868, 842)
SIEANA_TELEPORT = (-1170, 426)
MOONWIND = (-1107, 497)

# --- Ayarlar ---
COMBO_MIN_DELAY = 0.1
COMBO_MAX_DELAY = 3.0
CLICK_WAIT = 2.0
ONE_KEY_INTERVAL = 540
WALK_DELAY = 10.0
F_PRESS_COUNT = 5

# --- Global flag ---
teleporting = False

# ------------------ Fonksiyonlar ------------------

def sleep(min_delay=0.1, max_delay=0.5):
    time.sleep(random.uniform(min_delay, max_delay))

def press_key_to_window(key, min_delay=0.05, max_delay=0.25):
    try:
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, key, 0)
        sleep(min_delay, max_delay)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, key, 0)
    except Exception as e:
        print(f"[WARN] press_key_to_window failed: {e}")

def click_abs(x, y, times=1, between_click_delay=(0.08, 0.18)):
    for _ in range(times):
        try:
            win32api.SetCursorPos((int(x), int(y)))
            sleep(*between_click_delay)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            sleep(0.06, 0.16)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            sleep(*between_click_delay)
        except Exception as e:
            print(f"[WARN] click_abs failed at ({x},{y}): {e}")

def press_f_multiple(times=5):
    print(f"[INFO] F tuşuna {times} kez basılıyor...")
    for _ in range(times):
        press_key_to_window(F_KEY)
        sleep(0.5, 1.0)

def run_combos_for_duration(duration_seconds):
    """
    Z-R kombinasyonları çalışır. 
    1 tuşu 9 dakikada bir basılır ve 3 saniye kombinasyon duraklatılır.
    teleporting=True ise Z tuşu durur, F ve R basışı devam eder.
    """
    global teleporting
    end_time = time.time() + duration_seconds
    last_one_press = time.time()

    while time.time() < end_time:
        if keyboard_monitor.get_combination_active():
            time.sleep(0.1)
            continue

        # Z kombinasyonu sadece teleporting=False iken çalışır
        if not teleporting:
            press_key_to_window(Z)
            sleep(COMBO_MIN_DELAY, COMBO_MAX_DELAY)

        # R tuşu her zaman basılacak
        press_key_to_window(R)
        sleep(COMBO_MIN_DELAY, COMBO_MAX_DELAY)

        # 1 tuşu 9 dakikada bir
        if (time.time() - last_one_press) >= ONE_KEY_INTERVAL:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 1 tuşuna basılıyor (9dk aralık)")
            press_key_to_window(ONE)
            last_one_press = time.time()
            print("[INFO] 3 saniyelik duraklama (Z duracak, R ve F devam edecek)...")
            # teleporting = True gibi davran, sadece Z duracak
            time.sleep(3)

        remaining = int(end_time - time.time())
        mins, secs = divmod(remaining, 60)
        print(f"\r[INFO] Kombinasyon sürüyor: {mins:02d}:{secs:02d} kaldı...", end="")
        time.sleep(1)
    print("\n[INFO] Kombinasyon süresi tamamlandı.")

# ------------------ Teleport Sequence ------------------

def teleport_sequence_a():
    global teleporting
    teleporting = True  # Z tuşu duracak
    print("[INFO] Başlıyor: TELEPORT sequence A")

    click_abs(*TELEPORT)
    time.sleep(CLICK_WAIT)
    press_key_to_window(M_KEY)
    time.sleep(CLICK_WAIT)
    click_abs(*PROTEAN_GATE)
    time.sleep(CLICK_WAIT)
    click_abs(*GO_TO)

    print(f"[INFO] Harita yürüme süresi ({WALK_DELAY} sn)...")
    time.sleep(WALK_DELAY)

    press_f_multiple(F_PRESS_COUNT)

    click_abs(*SIEANA_VILLAGE)
    time.sleep(CLICK_WAIT)
    click_abs(*TRAVEL)
    time.sleep(CLICK_WAIT)

    print("[INFO] TELEPORT sequence A tamam.")
    teleporting = False  # Z tekrar çalışabilir

def teleport_sequence_b():
    global teleporting
    teleporting = True  # Z tuşu duracak
    print("[INFO] Başlıyor: TELEPORT sequence B")

    press_key_to_window(M_KEY)
    time.sleep(CLICK_WAIT)
    click_abs(*SIEANA_TELEPORT)
    time.sleep(CLICK_WAIT)
    click_abs(*GO_TO)

    print(f"[INFO] Harita yürüme süresi ({WALK_DELAY} sn)...")
    time.sleep(WALK_DELAY)

    press_f_multiple(F_PRESS_COUNT)

    click_abs(*MOONWIND)
    time.sleep(CLICK_WAIT)
    click_abs(*TRAVEL)
    time.sleep(CLICK_WAIT)

    print("[INFO] TELEPORT sequence B tamam.")
    teleporting = False  # Z tekrar çalışabilir

# ------------------ Bot Döngüsü ------------------

def run_bot_loop():
    """
    Tur sıralamasına göre kombinasyonları çalıştırır.
    Tur ve teleport dizisi sabitlenmiş:
    1. tur: 120s → sequence_a
    2. tur: 30s → sequence_b
    3. tur: 120s → sequence_b
    """
    turler = [
        {"sure": 120, "teleport": teleport_sequence_a},
        {"sure": 30,  "teleport": teleport_sequence_b},
        {"sure": 120, "teleport": teleport_sequence_b}
    ]

    while True:
        for idx, tur in enumerate(turler):
            while keyboard_monitor.get_combination_active():
                time.sleep(0.1)

            print(f"[INFO] Tur {idx+1}: {tur['sure']} saniye boyunca kombinasyonlar başlıyor...")
            run_combos_for_duration(tur["sure"])

            print(f"[INFO] Tur {idx+1} tamamlandı -> teleport sequence çalıştırılıyor...")
            tur["teleport"]()

        print("[INFO] Döngü başa dönüyor...")

def run_thread(_pause_event):
    while True:
        if keyboard_monitor.get_combination_active():
            _pause_event.set()
            time.sleep(0.1)
        else:
            if _pause_event.is_set():
                _pause_event.clear()
            run_bot_loop()

# ------------------ Main ------------------

if __name__ == '__main__':
    print('📌 Oyunu 1920x1080 pencere modunda ayarla.')
    print('⏸️ Duraklatmak/devam ettirmek için Sağ CTRL + Sağ ALT tuşlarına aynı anda bas.')
    print('🚀 Bot 3 saniye içinde başlıyor...')
    time.sleep(3)

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"[WARN] SetForegroundWindow failed: {e}")

    pause_event = ThreadEvent()
    thread = Thread(target=run_thread, args=(pause_event,))
    thread.daemon = True
    thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nÇıkılıyor...")
