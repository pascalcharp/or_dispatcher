# coding: utf-8
import logging
import selectors
import socket
import threading
import time


class Client:
    def __init__(self, host, port):
        logging.basicConfig(filename="client.log", level=logging.DEBUG)
        self.server_host = host
        self.server_port = port

        self.sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockobj.connect((self.server_host, self.server_port))
        self.sockobj.setblocking(False)
        logging.info(f"Connexion établie avec {self.sockobj.getpeername()}")
        logging.info(f"Adresse locale: {self.sockobj.getsockname()}")

        self.pending = []
        self.keep_running = True

        self.user_input_thread = threading.Thread(target=self.monitor_user_input, name="userInputThread")
        self.selector = selectors.DefaultSelector()
        self.selector.register(fileobj=self.sockobj, events=selectors.EVENT_WRITE | selectors.EVENT_READ)

    def monitor_user_input(self):
        while True:
            user = input("Saisir votre requête:  ")
            self.pending.append(user)
            if not user:
                self.keep_running = False
                break
        logging.info("Thread des saisies utilisateur terminée.")

    def handle_io_event(self, sock, mask):
        if mask & selectors.EVENT_READ:
            data = sock.recv(1024)
            message = data.decode()
            logging.info(f"Réponse du serveur: {message} reçue à {self.now}")
            print(f"Réponse du serveur: {message} à {self.now}")
        elif mask & selectors.EVENT_WRITE:
            if self.pending:
                request = self.pending.pop(0)
                sock.send(request.encode())
                logging.info(f"Requête {request} envoyée à {self.now}")
        else:
            logging.info(f"Masque inattendu dans handle_io_event")

    @property
    def now(self):
        return time.ctime(time.time())

    def start_client(self):
        self.user_input_thread.start()

        while self.keep_running:
            events = self.selector.select()
            for key, mask in events:
                self.handle_io_event(key.fileobj, mask)

        self.shutdown_client()

    def shutdown_client(self):
        self.selector.modify(fileobj=self.sockobj, events=selectors.EVENT_WRITE)

        while self.pending:
            request = self.pending.pop(0)
            keep_trying = True

            while keep_trying:
                events = self.selector.select()
                for key, mask in events:
                    print(f"Masque = {mask}")
                    if key.fileobj == self.sockobj and mask & selectors.EVENT_WRITE:
                        self.sockobj.send(request.encode())
                        keep_trying = False
                        break

        self.selector.unregister(fileobj=self.sockobj)
        self.sockobj.close()
        self.selector.close()


if __name__ == "__main__":
    client = Client("localhost", 50007)
    client.start_client()
