import email
import os
import poplib
import re
from email.header import decode_header



class EmailPop3Reader:
    def __init__(self, mail_server, server_port, user_login, user_password):
        """
        Инициализация клиента для чтения почты через POP3.
        :param mail_server: Адрес сервера (например, 'pop.yandex.ru')
        :param server_port: Порт подключения (например, 995)
        :param user_login: Логин пользователя (почта)
        :param user_password: Пароль от аккаунта 
        """
        self.mail_server = mail_server
        self.server_port = server_port
        self.user_login = user_login
        self.user_password = user_password
        self.email_message = None  # Здесь будет храниться прочитанное письмо

        print("[+] Подключение к почтовому серверу...")
        self.fetch_last_email()  # Получаем последнее письмо

        if self.email_message:
            print("[+] Разбор данных письма...")
            self.process_email_data()  # Анализируем содержимое письма
        else:
            print("[-] Письмо не найдено или произошла ошибка при получении.")

    def fetch_last_email(self):
        """
        Подключается к серверу, авторизуется и загружает последнее письмо.
        """
        try:
            # Подключение к серверу по SSL
            connection = poplib.POP3_SSL(self.mail_server, self.server_port)
            connection.user(self.user_login)
            connection.pass_(self.user_password)

            # Получение количества сообщений
            message_count = len(connection.list()[1])

            if message_count < 1:
                print("[-] Нет сообщений в ящике.")
                connection.quit()
                return

            print(f"[+] Загружается последнее письмо (№{message_count})...")
            raw_data = connection.retr(message_count)[1]
            full_email = b'\n'.join(raw_data)

            # Преобразование в объект Message из библиотеки email
            self.email_message = email.message_from_bytes(full_email)

            connection.quit()  # Закрываем соединение

        except Exception as e:
            print(f"[!] Ошибка при подключении к серверу: {e}")

    def process_email_data(self):
        """
        Обрабатывает данные письма: заголовки, тело, вложения.
        Выводит информацию в консоль и сохраняет вложения.
        """
        # Извлечение основных заголовков
        subject_info = decode_header(self.email_message.get('Subject'))[0]
        sender_info = decode_header(self.email_message.get('From'))[0]
        date_info = decode_header(self.email_message.get('Date'))[0]

        # Декодирование значений заголовков
        subject = subject_info[0].decode(subject_info[1]) if subject_info and subject_info[1] else subject_info[0]
        sender = sender_info[0].decode(sender_info[1]) if sender_info and sender_info[1] else sender_info[0]
        send_date = date_info[0].decode(date_info[1]) if date_info and date_info[1] else date_info[0]

        # Словарь с данными письма
        email_data = {
            "subject": subject,
            "sender": sender,
            "date": send_date,
            "body": ""
        }

        # Обработка содержимого письма
        print("[*] Извлечение содержимого письма...")

        if self.email_message.is_multipart():
            for part in self.email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Сохранение вложений
                if "attachment" in content_disposition:
                    attachment_data = part.get_payload(decode=True)
                    if not attachment_data:
                        continue

                    # Получение имени файла
                    file_name = part.get_filename()
                    if not file_name:
                        continue

                    decoded_file_name = decode_header(file_name)[0][0]
                    if isinstance(decoded_file_name, bytes):
                        decoded_file_name = decoded_file_name.decode(errors='replace')

                    # Очистка имени файла от лишних символов
                    clean_file_name = decoded_file_name.replace("\"", "").strip()

                    # Создание папки и сохранение файла
                    os.makedirs("attachments", exist_ok=True)
                    file_path = os.path.join("attachments", clean_file_name)

                    with open(file_path, "wb") as file:
                        file.write(attachment_data)

                    print(f"[+] Сохранено вложение: {clean_file_name}")

                # Извлечение текстовой части письма
                elif content_type == "text/plain":
                    body = part.get_payload(decode=True)
                    if body:
                        email_data["body"] = body.decode(errors='replace')

        else:
            # Если письмо не содержит частей
            payload = self.email_message.get_payload(decode=True)
            if payload:
                email_data["body"] = payload.decode(errors='replace')

        # Чистка текста письма от лишних пробелов и переносов
        email_data["body"] = re.sub(r'[\n\t\s]{2,}', '\n', email_data["body"])

        # Вывод информации о письме
        print("\n" + "-" * 40)
        print(f" Тема: {email_data['subject']}")
        print(f" От кого: {email_data['sender']}")
        print(f" Дата: {email_data['date']}")
        print("-" * 40)
        print(" Текст письма:\n")
        print(email_data['body'])
        print("-" * 40)


if __name__ == "__main__":
    print("Введите адрес электронной почты:")
    login = input().strip()

    print("Введите пароль:")
    password = input().strip()

    print("Подождите...")

    # Пример для Gmail. Для Yandex 
    client = EmailPop3Reader(
        mail_server="pop.yandex.ru",   # Сервер для Yandex
        server_port=995,              # Порт для POP3 + SSL
        user_login=login,
        user_password=password
    )