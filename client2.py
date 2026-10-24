import base64
import io
import os
import threading
from socket import socket, AF_INET, SOCK_STREAM
from customtkinter import *
from tkinter import filedialog, END
from PIL import Image
SERVER_HOST = 'localhost'
SERVER_PORT = 8080
COLORS = ['#c0392b', '#8e44ad', '#2980b9', '#16a085', '#d35400', '#7f8c8d', '#27ae60']
def color_for(name):
    return COLORS[sum(ord(c) for c in name) % len(COLORS)]
def make_ctk_image(pil_img, max_size=250):
    w, h = pil_img.size
    scale = min(max_size / w, max_size / h, 1)
    return CTkImage(pil_img, size=(max(int(w * scale), 1), max(int(h * scale), 1)))
class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry('600x450')
        self.minsize(400, 300)
        self.title("Chat Client")
        self.username = "Artem"
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.label = None
        self.entry = None
        self.save_button = None
        self.menu_width = 30
        self.menu_anim_id = None
        self.is_show_menu = False
        self.speed_animate_menu = 20
        self.menu_frame = CTkFrame(self, width=30, corner_radius=0)
        self.menu_frame.pack_propagate(False)
        self.menu_frame.grid(row=0, column=0, sticky='ns')
        self.btn = CTkButton(self.menu_frame, text='▶️', command=self.toggle_show_menu, width=30)
        self.btn.pack(anchor='w')
        self.right_frame = CTkFrame(self, fg_color='transparent')
        self.right_frame.grid(row=0, column=1, sticky='nsew')
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.chat_field = CTkScrollableFrame(self.right_frame)
        self.chat_field.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        self.bottom_frame = CTkFrame(self.right_frame, fg_color='transparent')
        self.bottom_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=(0, 5))
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.message_entry = CTkEntry(self.bottom_frame, placeholder_text='Введіть повідомлення:', height=40)
        self.message_entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        self.message_entry.bind('<Return>', lambda event: self.send_message())
        self.open_img_button = CTkButton(self.bottom_frame, text='📂', width=50, height=40, command=self.open_image)
        self.open_img_button.grid(row=0, column=1, padx=(0, 5))
        self.send_button = CTkButton(self.bottom_frame, text='>', width=50, height=40, command=self.send_message)
        self.send_button.grid(row=0, column=2)
        self.sock = None
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            self.sock.sendall(hello.encode('utf-8'))
            threading.Thread(target=self.recv_message, daemon=True).start()
            self.add_message("Ви підключені до чату", system=True)
        except Exception as e:
            self.sock = None
            self.add_message(f"Не вдалося підключитися до сервера: {e}", system=True)
    def toggle_show_menu(self):
        if self.is_show_menu:
            self.is_show_menu = False
            self.speed_animate_menu = -20
            self.btn.configure(text='▶️')
            for widget in (self.label, self.entry, self.save_button):
                if widget:
                    widget.destroy()
            self.label = self.entry = self.save_button = None
        else:
            self.is_show_menu = True
            self.speed_animate_menu = 20
            self.btn.configure(text='◀️')
            self.label = CTkLabel(self.menu_frame, text='Імʼя')
            self.label.pack(pady=30)
            self.entry = CTkEntry(self.menu_frame, placeholder_text="Ваш нік...")
            self.entry.pack()
            self.save_button = CTkButton(self.menu_frame, text="Зберегти", command=self.save_name)
            self.save_button.pack(pady=5)
        if self.menu_anim_id:
            self.after_cancel(self.menu_anim_id)
        self.show_menu()
    def show_menu(self):
        self.menu_width += self.speed_animate_menu
        done = False
        if self.is_show_menu and self.menu_width >= 200:
            self.menu_width = 200
            done = True
        elif not self.is_show_menu and self.menu_width <= 30:
            self.menu_width = 30
            done = True
        self.menu_frame.configure(width=self.menu_width)
        if done:
            self.menu_anim_id = None
        else:
            self.menu_anim_id = self.after(10, self.show_menu)
    def save_name(self):
        new_name = self.entry.get().strip()
        if new_name and new_name != self.username:
            old_name = self.username
            self.username = new_name
            self.add_message(f"Ваш новий нік: {new_name}", system=True)
            self.send_raw(f"TEXT@{new_name}@[SYSTEM] {old_name} тепер {new_name}\n")
            self.entry.delete(0, END)
    def add_message(self, message, img=None, author=None, mine=False, system=False):
        if system:
            color, anchor = '#555555', 'center'
        elif mine:
            color, anchor = '#1f6aa5', 'e'
        elif author:
            color, anchor = color_for(author), 'w'
        else:
            color, anchor = 'grey', 'w'
        message_frame = CTkFrame(self.chat_field, fg_color=color)
        message_frame.pack(pady=5, padx=5, anchor=anchor)
        wrap = max(self.winfo_width() - self.menu_width - 100, 150)
        if img:
            CTkLabel(message_frame, text=message, wraplength=wrap, text_color='white',
                     image=img, compound='top', justify='left').pack(padx=10, pady=5)
        else:
            CTkLabel(message_frame, text=message, wraplength=wrap, text_color='white',
                     justify='left').pack(padx=10, pady=5)

        self.after(50, lambda: self.chat_field._parent_canvas.yview_moveto(1.0))
    def send_raw(self, text):
        if not self.sock:
            return False
        try:
            self.sock.sendall(text.encode('utf-8'))
            return True
        except Exception:
            return False
    def send_message(self):
        message = self.message_entry.get().strip()
        if message:
            message = message.replace("\n", " ")
            self.add_message(f"{self.username}: {message}", mine=True)
            if not self.send_raw(f"TEXT@{self.username}@{message}\n"):
                self.add_message("Повідомлення не надіслано: немає звʼязку з сервером", system=True)
        self.message_entry.delete(0, END)
    def recv_message(self):
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.after(0, self.handle_line, line.strip())
            except Exception:
                break
        self.after(0, lambda: self.add_message("Зʼєднання з сервером втрачено", system=True))
        if self.sock:
            self.sock.close()
    def handle_line(self, line):
        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]
        if msg_type == "TEXT" and len(parts) >= 3:
            author = parts[1]
            message = "@".join(parts[2:])
            if message.startswith("[SYSTEM]"):
                self.add_message(message.replace("[SYSTEM] ", "", 1), system=True)
            else:
                self.add_message(f"{author}: {message}", author=author)
        elif msg_type == "IMAGE" and len(parts) >= 4:
            author = parts[1]
            filename = parts[2]
            b64_img = parts[3]
            try:
                img_data = base64.b64decode(b64_img)
                pil_img = Image.open(io.BytesIO(img_data))
                self.add_message(f"{author} надіслав(ла) зображення: {filename}",
                                 img=make_ctk_image(pil_img), author=author)
            except Exception as e:
                self.add_message(f"Помилка відображення зображення: {e}", system=True)
        else:
            self.add_message(line)
    def open_image(self):
        file_name = filedialog.askopenfilename(
            filetypes=[("Зображення", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not file_name:
            return
        try:
            with open(file_name, "rb") as f:
                raw = f.read()
            b64_data = base64.b64encode(raw).decode()
            short_name = os.path.basename(file_name).replace("@", "_")
            if not self.send_raw(f"IMAGE@{self.username}@{short_name}@{b64_data}\n"):
                self.add_message("Зображення не надіслано: немає звʼязку з сервером", system=True)
                return
            self.add_message(f"{self.username}: {short_name}",
                             img=make_ctk_image(Image.open(file_name)), mine=True)
        except Exception as e:
            self.add_message(f"Не вдалося надіслати зображення: {e}", system=True)
if __name__ == "__main__":
    win = MainWindow()
    win.mainloop()