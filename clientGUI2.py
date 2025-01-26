import socket
import threading
import tkinter as tk
from tkinter import messagebox
from protocol import encode_message, decode_message

HOST = '127.0.0.1'
PORT = 12346


class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Labyrinthium")
        self.root.geometry("800x600")

        self.client_socket = None
        self.username = ""
        self.room = ""
        self.is_connected = False
        self.maze_data = []
        self.player_score = 0
        self.player_position = (0, 0)

        self.create_frames()
        self.create_connection_window()

    def create_frames(self):
        """Создание и настройка окон"""
        self.connection_frame = tk.Frame(self.root)
        self.game_frame = tk.Frame(self.root)

        for frame in (self.connection_frame, self.game_frame):
            frame.grid(row=0, column=0, sticky="nsew")

        """Начальное окно"""
        self.switch_frame(self.connection_frame)

    def switch_frame(self, frame):
        """Переключение между окнами."""
        frame.tkraise()

    def create_connection_window(self):
        """Создаёт окно подключения."""
        tk.Label(self.connection_frame, text="Имя пользователя:").grid(row=0, column=0, padx=5, pady=5)
        self.username_entry = tk.Entry(self.connection_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.connection_frame, text="Комната: room_").grid(row=1, column=0, padx=5, pady=5)
        self.room_entry = tk.Entry(self.connection_frame)
        self.room_entry.grid(row=1, column=1, padx=5, pady=5)

        self.room_list = tk.Listbox(self.connection_frame, height=10, width=30)
        self.room_list.grid(row=2, column=0, columnspan=2, pady=10)

        tk.Button(self.connection_frame, text="Показать список комнат", command=self.request_room_list).grid(row=3,
                                                                                                             column=0,
                                                                                                             columnspan=2)
        tk.Button(self.connection_frame, text="Подключиться", command=self.start_connection_thread).grid(row=4,
                                                                                                         column=0,
                                                                                                         columnspan=2,
                                                                                                         pady=10)

        self.status_label = tk.Label(self.connection_frame, text="", fg="red")
        self.status_label.grid(row=5, column=0, columnspan=2)


    def request_room_list(self):
        """Запрашивает список доступных комнат с сервера."""
        if not self.client_socket:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))

        message = {"type": "list_rooms"}
        self.client_socket.send(encode_message(message))

        threading.Thread(target=self.receive_room_list, daemon=True).start()

    def receive_room_list(self):
        """Обрабатывает ответ с информацией о комнатах."""
        try:
            response = decode_message(self.client_socket.recv(4096))
            if response["type"] == "list_rooms":
                self.update_room_list(response["data"])
        except Exception as e:
            print(f"[ОШИБКА ПОЛУЧЕНИЯ СПИСКА КОМНАТ]: {e}")

    def update_room_list(self, room_info):
        """Обновляет список комнат в интерфейсе."""
        self.room_list.delete(0, tk.END)
        for room, count in room_info.items():
            self.room_list.insert(tk.END, f"room_{room}: {count} игрок(ов)")

    def start_connection_thread(self):
        """Запускает поток для подключения к серверу"""
        self.status_label.config(text="Подключение...")
        threading.Thread(target=self.connect_to_server, daemon=True).start()

    def connect_to_server(self):
        """Подключение к серверу"""
        self.username = self.username_entry.get()
        self.room = self.room_entry.get()

        if not self.username or not self.room:
            self.update_status("Введите имя и номер комнаты!")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))

            message = {"type": "join_room", "from_user": self.username, "data": self.room}
            self.client_socket.send(encode_message(message))

            response = decode_message(self.client_socket.recv(1024))
            if response.get("status") == "ok":
                self.is_connected = True
                self.update_status("Успешное подключение!", "green")
                self.switch_frame(self.game_frame)
                self.create_game_window()
                threading.Thread(target=self.receive_messages, daemon=True).start()
            else:
                self.update_status(response.get("message"))
        except Exception as e:
            self.update_status(f"Ошибка: {str(e)}")

    def update_status(self, message, color="red"):
        """Обновляет текст статуса"""
        self.status_label.config(text=message, fg=color)

    def create_game_window(self):
        """Создаёт игровое окно."""
        # Лабиринт
        self.canvas = tk.Canvas(self.game_frame, width=400, height=400, bg="lightgray")
        self.canvas.grid(row=0, column=0)

        # Информация для игрока
        self.info_label = tk.Label(self.game_frame, text="Счет: 0 | Монет осталось: 0 | Цель: Доберитесь до выхода!", anchor="w")
        self.info_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        # Кнопка "Старт"
        self.start_button = tk.Button(self.game_frame, text="Старт", command=self.start_game)
        self.start_button.grid(row=3, column=0, pady=10)

        tk.Button(self.game_frame, text="Выход", command=self.exit_game).grid(row=3, column=1, pady=10)

        # Чат
        self.chat_log = tk.Text(self.game_frame, state="disabled", width=40, height=10)
        self.chat_log.grid(row=0, column=1, padx=10)
        self.chat_entry = tk.Entry(self.game_frame)
        self.chat_entry.grid(row=1, column=1, padx=10, pady=10)

        tk.Button(self.game_frame, text="Отправить", command=self.send_message).grid(row=2, column=1)


        # Управление движением
        controls_frame = tk.Frame(self.game_frame)
        controls_frame.grid(row=2, column=0)

        tk.Button(controls_frame, text="↑", command=lambda: self.move("вверх")).grid(row=0, column=1)
        tk.Button(controls_frame, text="←", command=lambda: self.move("влево")).grid(row=1, column=0)
        tk.Button(controls_frame, text="→", command=lambda: self.move("вправо")).grid(row=1, column=2)
        tk.Button(controls_frame, text="↓", command=lambda: self.move("вниз")).grid(row=2, column=1)

    def send_message(self):
        """Отправка сообщения в чат."""
        msg = self.chat_entry.get()
        if msg:
            message = {"type": "chat", "from_user": self.username, "data": msg}
            self.client_socket.send(encode_message(message))
            self.chat_entry.delete(0, tk.END)

    def start_game(self):
        """Отправка запроса на начало игры (генерация лабиринта)."""
        if not self.is_connected:
            messagebox.showerror("Ошибка", "Вы не подключены к серверу!")
            return
        message = {"type": "start_game", "from_user": self.username, "data": self.room}
        self.client_socket.send(encode_message(message))


    def receive_messages(self):
        """Приём сообщений от сервера"""
        while self.is_connected:
            try:
                encoded_message = self.client_socket.recv(1024)
                if not encoded_message:
                    break
                message = decode_message(encoded_message)

                if message["type"] == "chat":
                    with open("chat_log.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(f"[{message['from_user']}]: {message['data']}\n")
                    self.chat_log.config(state="normal")
                    self.chat_log.insert(tk.END, f"[{message['from_user']}]: {message['data']}\n")
                    self.chat_log.config(state="disabled")

                elif message["type"] == "maze":
                    self.maze_data = message["data"]["maze"]
                    self.player_score = message["data"]["score"]
                    self.player_position = tuple(message["data"].get("player_position", self.player_position))
                    remaining_coins = message["data"].get("remaining_coins", 0)
                    self.display_maze()
                    self.info_label.config(
                        text=f"Счет: {self.player_score} | Монет осталось: {remaining_coins} | Цель: Соберите все монеты!")

                elif message["type"] == "end_game":
                    messagebox.showinfo("Игра завершена", message["message"])
                    self.exit_game()

                elif message["type"] == "level_up":
                    self.maze_data = message["data"]["maze"]
                    self.player_score = message["data"]["score"]
                    self.player_position = tuple(message["data"].get("player_position", self.player_position))
                    self.display_maze()

                elif message["type"] == "reset":
                    self.maze_data = message["data"]["maze"]
                    self.player_score = message["data"]["score"]
                    self.player_position = tuple(message["data"].get("player_position", self.player_position))
                    self.info_label.config(
                        text=f"Счет: {self.player_score} | Монет осталось: {message['data'].get('remaining_coins', 0)} | Цель: Соберите все монеты!")
                    self.display_maze()

                    messagebox.showwarning("Столкновение", message["data"]["message"])

            except Exception as e:
                print(f"[ОШИБКА]: {e}")
                break

    def move(self, direction):
        """Отправляет запрос на движение."""
        if not self.is_connected:
            messagebox.showerror("Ошибка", "Вы не подключены к серверу!")
            return
        message = {"type": "move", "from_user": self.username, "data": direction}
        self.client_socket.send(encode_message(message))

    def display_maze(self):
        """Отображение лабиринта."""
        if not self.maze_data:
            return

        self.canvas.delete("all")
        cell_size = 400 // max(len(self.maze_data), len(self.maze_data[0]))
        for y, row in enumerate(self.maze_data):
            for x, cell in enumerate(row):
                if cell == 1:
                    self.canvas.create_rectangle(x * cell_size, y * cell_size, (x + 1) * cell_size, (y + 1) * cell_size, fill="black")
                elif cell == 2:
                    self.canvas.create_oval(x * cell_size, y * cell_size, (x + 1) * cell_size, (y + 1) * cell_size, fill="gold")
        px, py = self.player_position
        self.canvas.create_oval(px * cell_size, py * cell_size, (px + 1) * cell_size, (py + 1) * cell_size, fill="blue")

    def exit_game(self):
        """Выход из игры."""
        if self.is_connected:
            try:
                message = {"type": "exit", "from_user": self.username}
                self.client_socket.send(encode_message(message))
            except Exception as e:
                print(f"[ОШИБКА ПРИ ВЫХОДЕ]: {e}")
        self.is_connected = False
        self.client_socket.close()
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    game_client = GameClient(root)
    root.mainloop()
