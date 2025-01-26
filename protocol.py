import pickle


def encode_message(message: dict) -> bytes:
    """Сериализует словарь в байты."""
    return pickle.dumps(message)


def decode_message(message: bytes) -> dict:
    """Десериализует байты в словарь."""
    return pickle.loads(message)


MESSAGE_TYPES = {
    "signup": "Регистрация",
    "move": "Движение игрока",
    "exit": "Выход из игры",
    "save": "Сохранение данных",
    "chat": "Сообщение пользователям",
    "score": "Количество монет",
    "show_maze": "Показ лабиринта",
}
