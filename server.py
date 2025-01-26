import socket
import threading
import random
from protocol import decode_message, encode_message

HOST = '127.0.0.1'
PORT = 12346

clients = []
registered_users = set()
lobbies = {f"{i}": [] for i in range(1, 6)}


def generate_real_maze(width, height, num_coins):
    """Генерация лабиринта"""
    maze = [[1 for _ in range(width)] for _ in range(height)]

    def carve_passages(cx, cy):
        """Алгоритм Карса"""
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(directions)

        for dx, dy in directions:
            nx, ny = cx + dx * 2, cy + dy * 2
            if 0 <= nx < width and 0 <= ny < height and maze[ny][nx] == 1:
                maze[cy + dy][cx + dx] = 0
                maze[ny][nx] = 0
                carve_passages(nx, ny)

    maze[0][0] = 0
    carve_passages(0, 0)
    for _ in range(num_coins):
        while True:
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            if maze[y][x] == 0:
                maze[y][x] = 2
                break

    return maze

room_mazes = {room: generate_real_maze(6,6,1) for room in lobbies}


def show_active_players():
    """Отображение активных игроков в каждой комнате"""
    print("[АКТИВНЫЕ ИГРОКИ]:")
    for room, players in lobbies.items():
        print(f"room_{room}: {len(players)} игрок(ов)")

def handle_client(client_socket, address):
    """Обработка подключения клиента"""
    print(f"[НОВОЕ ПОДКЛЮЧЕНИЕ] Клиент {address} подключился.")
    clients.append(client_socket)
    player_positions = {}
    player_scores = {}
    level = 1
    up = 0

    try:
        encoded_message = client_socket.recv(1024)
        message = decode_message(encoded_message)

        if message["type"] == "list_rooms":
            """Создание списка комнат и количества игроков"""
            room_info = {room: len(players) for room, players in lobbies.items()}
            response = {"type": "list_rooms", "data": room_info}
            client_socket.send(encode_message(response))

        """Обработка выбора комнаты"""
        if message["type"] == "join_room":
            room_name = message["data"]
            if room_name in lobbies:
                lobbies[room_name].append(client_socket)
                response = {"type": "join_room", "status": "ok", "message": f"Вы вошли в {room_name}."}
                client_socket.send(encode_message(response))
            else:
                response = {"type": "error", "message": "Такой комнаты не существует."}
                client_socket.send(encode_message(response))
                return

        while True:
            encoded_message = client_socket.recv(1024)
            if not encoded_message:
                break
            message = decode_message(encoded_message)
            print(f"[СООБЩЕНИЕ ОТ {address}] Тип: {message['type']}")

            if message["type"] == "move":
                username = message["from_user"]
                direction = message["data"]
                x, y = player_positions.get(username, (0, 0))
                room_name = None

                for room, players in lobbies.items():
                    if client_socket in players:
                        room_name = room
                        break

                if not room_name:
                    response = {"type": "error", "message": "Комната не найдена."}
                    client_socket.send(encode_message(response))
                    continue

                if direction == "вверх" and y > 0:
                    y -= 1
                elif direction == "вниз" and y < len(room_mazes[room_name]) - 1:
                    y += 1
                elif direction == "влево" and x > 0:
                    x -= 1
                elif direction == "вправо" and x < len(room_mazes[room_name][0]) - 1:
                    x += 1

                if room_mazes[room_name][y][x] == 1:
                    level = 1
                    up = 0
                    room_mazes[room_name] = generate_real_maze(6,6,1)
                    player_positions[username] = (0, 0)
                    player_scores[username] = 0
                    response = {
                        "type": "reset",
                        "data": {
                            "message": "Вы попали в стену! Лабиринт сгенерирован заново.",
                            "maze": room_mazes[room_name],
                            "player_position": (0, 0),
                            "score": 0,
                        },
                    }
                    client_socket.send(encode_message(response))
                else:
                    player_positions[username] = (x, y)
                    if room_mazes[room_name][y][x] == 2:
                        room_mazes[room_name][y][x] = 0
                        player_scores[username] = player_scores.get(username, 0) + 1

                    remaining_coins = sum(row.count(2) for row in room_mazes[room_name])

                    response = {
                        "type": "maze",
                        "data": {
                            "maze": room_mazes[room_name],
                            "player_position": (x, y),
                            "score": player_scores.get(username, 0),
                            "remaining_coins": remaining_coins,
                        },
                    }
                    client_socket.send(encode_message(response))

                    """Если все монеты собраны"""
                    if remaining_coins == 0:
                        level += 1
                        if level == 5:
                            up += 1
                            level = 1
                        room_mazes[room_name] = generate_real_maze(6 + (2*up), 6 + (2*up), 1*(up+1) + level - 1)
                        print(10 + (5*up), 10 + (5*up), 1 + level - 1)
                        player_positions[username] = (0, 0)
                        response = {
                            "type": "level_up",
                            "data": {
                                "message": "Вы собрали все монеты! Лабиринт сгенерирован заново.",
                                "maze": room_mazes[room_name],
                                "player_position": (0, 0),
                                "score": player_scores[username],
                            },
                        }
                        client_socket.send(encode_message(response))
            elif message["type"] == "start_game":
                username = message["from_user"]
                room_name = None
                for room, players in lobbies.items():
                    if client_socket in players:
                        room_name = room
                        break

                if room_name:
                    player_scores[username] = 0
                    player_positions[username] = (0, 0)
                    room_mazes[room_name] = generate_real_maze(6,6,1)
                    response = {
                        "type": "maze",
                        "data": {
                            "maze": room_mazes[room_name],
                            "player_position": (0, 0),
                            "score": 0,
                            "remaining_coins": sum(row.count(2) for row in room_mazes[room_name]),
                        },
                    }
                    client_socket.send(encode_message(response))
                else:
                    response = {"type": "error", "message": "Комната не найдена."}
                    client_socket.send(encode_message(response))

            elif message["type"] == "chat":
                for client in clients:
                    client.send(encode_message(message))

            elif message["type"] == "exit":
                username = message["from_user"]
                response = {"type": "exit", "status": "ok", "message": "До свидания!"}
                client_socket.send(encode_message(response))
                for room, players in lobbies.items():
                    if client_socket in players:
                        players.remove(client_socket)
                        break
                if client_socket in clients:
                    clients.remove(client_socket)
                print(f"[ОТКЛЮЧЕНИЕ] {username} отключился.")
                break


    except Exception as e:
        print(f"[ОШИБКА] С клиентом {address}: {e}")
    finally:
        print(f"[ОТКЛЮЧЕНИЕ] Клиент {address} отключился.")
        for room, players in lobbies.items():
            if client_socket in players:
                players.remove(client_socket)
                break
        if client_socket in clients:
            clients.remove(client_socket)
        show_active_players()
        client_socket.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[ЗАПУЩЕН] Сервер запущен на {HOST}:{PORT}")

    while True:
        client_socket, address = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, address))
        thread.start()
        print(f"[ПОДКЛЮЧЕНИЯ] Активных подключений: {threading.active_count() - 1}")
        show_active_players()


if __name__ == "__main__":
    start_server()
