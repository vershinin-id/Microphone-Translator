import pyaudio
import vosk
import threading
import queue
import time
import tkinter as tk
from tkinter import Label, StringVar, Scale, HORIZONTAL, Toplevel, DoubleVar, OptionMenu, colorchooser, filedialog, Button, Canvas, Checkbutton, IntVar, Menu, ttk
from googletrans import Translator
import os
import sys

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Создание переводчика
translator = Translator()

model = None
text_queue = queue.Queue()
loading_model = False

def choose_model_path():
    root = tk.Tk()
    root.withdraw()
    model_path = filedialog.askdirectory(title="Выберите путь к папке модели Vosk")
    root.destroy()
    return model_path

def load_model(progress_var, status_label):
    global model, loading_model
    model_path = choose_model_path()
    if not model_path:
        print("Путь к модели Vosk не был выбран.")
        return
    loading_model = True
    progress_var.set(0)
    status_label.config(text="Загрузка...")
    threading.Thread(target=_load_model_thread, args=(model_path, progress_var, status_label)).start()

def _load_model_thread(model_path, progress_var, status_label):
    global model, loading_model
    try:
        model = vosk.Model(model_path)
        for i in range(101):
            progress_var.set(i)
            time.sleep(0.02)  # Имитация загрузки модели
        status_label.config(text="Готово")
        start_recognition_thread()
    except Exception as e:
        print(f"Ошибка при загрузке модели: {e}")
        status_label.config(text="Ошибка")
    finally:
        loading_model = False

def start_recognition_thread():
    recognizer_thread = threading.Thread(target=recognize_speech_from_mic)
    recognizer_thread.daemon = True
    recognizer_thread.start()

def recognize_speech_from_mic():
    global model
    if model is None:
        print("Модель Vosk не загружена.")
        return

    rec = vosk.KaldiRecognizer(model, RATE)
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, input_device_index=None)
    stream.start_stream()

    while True:
        data = stream.read(CHUNK)
        if rec.AcceptWaveform(data):
            result = rec.Result()
            text = eval(result).get('text', '')
            if text:
                text_queue.put(text)

def display_text():
    global target_language, show_rus_window  

    root = tk.Tk()
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.8)
    root.overrideredirect(True)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 1200
    window_height = 100
    x_position = (screen_width // 2) - (window_width // 2)
    y_position = screen_height - window_height - 50
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    root.config(bg="black")

    displayed_text = StringVar(value="")
    full_text = ""
    alpha_value = DoubleVar(value=0.8)
    font_size = DoubleVar(value=24)
    font_color = StringVar(value="white")
    bg_color = StringVar(value="black")
    target_language = StringVar(value="zh-cn")
    show_rus_window = IntVar(value=1)

    def start_move(event, window):
        window.x = event.x
        window.y = event.y

    def do_move(event, window):
        x = event.x_root - window.x
        y = event.y_root - window.y
        window.geometry(f"+{x}+{y}")

    def start_resize(event, window):
        window.start_x = event.x
        window.start_y = event.y
        window.start_width = window.winfo_width()
        window.start_height = window.winfo_height()

    def do_resize(event, window, canvas, text_id):
        dx = event.x - window.start_x
        dy = event.y - window.start_y
        new_width = window.start_width + dx
        new_height = window.start_height + dy
        window.geometry(f"{new_width}x{new_height}")
        canvas.coords(text_id, new_width // 2, new_height // 2)
        canvas.itemconfig(text_id, width=new_width - 20)  # Установка ширины для переноса текста

    canvas = Canvas(root, bg=bg_color.get(), highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.bind("<Button-1>", lambda event: start_move(event, root))
    canvas.bind("<B1-Motion>", lambda event: do_move(event, root))

    canvas.bind("<Button-3>", lambda event: start_resize(event, root))
    canvas.bind("<B3-Motion>", lambda event: do_resize(event, root, canvas, text_id))

    text_id = canvas.create_text(window_width // 2, window_height // 2, text="", font=("Calibri", int(font_size.get())), fill=font_color.get(), anchor="center", width=window_width - 20)

    rus_window = Toplevel(root)
    rus_window.attributes("-topmost", True)
    rus_window.attributes("-alpha", 0.8)
    rus_window.overrideredirect(True)

    rus_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position-150}")

    rus_window.config(bg="black")

    rus_canvas = Canvas(rus_window, bg=bg_color.get(), highlightthickness=0)
    rus_canvas.pack(fill="both", expand=True)
    rus_canvas.bind("<Button-1>", lambda event: start_move(event, rus_window))
    rus_canvas.bind("<B1-Motion>", lambda event: do_move(event, rus_window))

    rus_canvas.bind("<Button-3>", lambda event: start_resize(event, rus_window))
    rus_canvas.bind("<B3-Motion>", lambda event: do_resize(event, rus_window, rus_canvas, rus_text_id))

    rus_text_id = rus_canvas.create_text(window_width // 2, window_height // 2, text="", font=("Calibri", int(font_size.get())), fill=font_color.get(), anchor="center", width=window_width - 20)

    def update_label():
        nonlocal full_text
        if not text_queue.empty():
            text = text_queue.get()
            try:
                translated_text = translator.translate(text, dest=target_language.get()).text
                full_text = translated_text
            except Exception as e:
                print(f"Ошибка при переводе текста: {e}")
                full_text = "Ошибка перевода текста"
            canvas.itemconfig(text_id, text=full_text)

            rus_canvas.itemconfig(rus_text_id, text=text)

        root.after(1000, update_label)

    def change_alpha(value):
        root.attributes("-alpha", float(value))
        rus_window.attributes("-alpha", float(value))

    def change_font_size(value):
        canvas.itemconfig(text_id, font=("Calibri", int(value)))
        rus_canvas.itemconfig(rus_text_id, font=("Calibri", int(value)))

    def change_font_color():
        color = colorchooser.askcolor(title="Выберите цвет текста")
        if color[1]:
            font_color.set(color[1])
            canvas.itemconfig(text_id, fill=color[1])
            rus_canvas.itemconfig(rus_text_id, fill=color[1])

    def change_bg_color():
        color = colorchooser.askcolor(title="Выберите цвет фона")
        if color[1]:
            bg_color.set(color[1])
            canvas.config(bg=color[1])
            rus_canvas.config(bg=color[1])

    def open_settings():
        settings_window = Toplevel(root)
        settings_window.geometry("500x400+850+100")
        settings_window.title("Настройки")
        settings_window.config(bg="white")

        Label(settings_window, text="Прозрачность фона:", bg="white").pack()
        alpha_slider = Scale(settings_window, from_=0.1, to=1.0, resolution=0.1, orient=HORIZONTAL, variable=alpha_value, command=change_alpha)
        alpha_slider.pack()

        Label(settings_window, text="Размер шрифта:", bg="white").pack()
        font_slider = Scale(settings_window, from_=10, to=40, orient=HORIZONTAL, variable=font_size, command=change_font_size)
        font_slider.pack()

        Button(settings_window, text="Цвет текста", command=change_font_color, bg="white").pack()
        Button(settings_window, text="Цвет фона", command=change_bg_color, bg="white").pack()

        Label(settings_window, text="Язык перевода основного окна:", bg="white").pack()
        OptionMenu(settings_window, target_language, "ru", "en", "zh-cn").pack()

        show_rus_checkbutton = Checkbutton(settings_window, text="Показать окно распознанного текста", variable=show_rus_window, bg="white", command=toggle_rus_window)
        show_rus_checkbutton.pack()

        Label(settings_window, text="Загрузка модели Vosk:", bg="white").pack()
        progress_var = DoubleVar(value=0)
        progress_bar = ttk.Progressbar(settings_window, variable=progress_var, maximum=100)
        progress_bar.pack(fill="x", padx=10, pady=10)
        status_label = Label(settings_window, text="", bg="white")
        status_label.pack()

        Button(settings_window, text="Загрузить модель Vosk", command=lambda: load_model(progress_var, status_label), bg="white").pack()

        Label(settings_window, text="by I.Vershinin - Postgraduate student of the Ural State University of Railway Transport", bg="white", fg="gray", anchor="center" ).pack(side="bottom", pady=10)

    def toggle_rus_window():
        if show_rus_window.get():
            rus_window.deiconify()
        else:
            rus_window.withdraw()

    def restart_program():
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def show_context_menu(event):
        if event.type == tk.EventType.ButtonPress and event.num == 3:
            root.bind("<Double-Button-3>", open_context_menu)

    def open_context_menu(event):
        context_menu = Menu(root, tearoff=0)
        context_menu.add_command(label="Настройки", command=open_settings)
        context_menu.add_command(label="Перезапуск", command=restart_program)
        context_menu.add_command(label="Закрыть", command=lambda: os._exit(0))
        context_menu.post(event.x_root, event.y_root)

    root.bind("<Button-3>", show_context_menu)

    update_label()
    root.mainloop()

display_text()

while True:
    time.sleep(1)
