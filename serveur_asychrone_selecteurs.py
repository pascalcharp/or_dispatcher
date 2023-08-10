from socket import socket, AF_INET, SOCK_STREAM
import selectors
import time
import json
import logging
import threading


class SocketException(Exception):
    pass


class WriteEventSocketException(SocketException):
    pass


class RequestHandler:
    def __init__(self):
        self.handle_message = "Handled: "

    def handle(self, request):
        logging.debug(f"Entrée dans handle!")
        request_text, peer = request
        return self.handle_message + request_text, peer


class Serveur:
    def __init__(self, **kwargs):
        logging.basicConfig(filename="server.log", level=logging.INFO)
        self.numPortSocks = kwargs["numPortSocks"]
        self.host = kwargs["host"]
        self.port = kwargs["port"]
        self.selector = selectors.DefaultSelector()
        self.active_clients, self.pending_requests, self.pending_replies = [], [], {}

        self.request_handler = RequestHandler()
        self.keep_handling_requests = True
        self.handler_thread = threading.Thread(target=self.start_handler_thread, name="handlerthread")

    def start_handler_thread(self):
        logging.info(f"Début du gestionnaire de requêtes à {self.now}")
        while self.keep_handling_requests:
            if self.pending_requests:
                current_request = self.pending_requests.pop(0)
                logging.info(f"Le gestionnaire traite la requête: {current_request} à {self.now}")
                current_reply_text, current_reply_peer = self.request_handler.handle(current_request)
                logging.info(f"Réponse {current_reply_text} générée à {self.now}")
                self.pending_replies[current_reply_peer].append(current_reply_text)
                logging.info(f"La réponse {current_reply_text} prête pour envoi à {self.now}")

    def start_server(self):
        listening_port = self.port
        for i in range(self.numPortSocks):
            portsock = socket(AF_INET, SOCK_STREAM)
            portsock.bind((self.host, listening_port))
            portsock.listen(5)
            portsock.setblocking(False)
            self.selector.register(portsock, selectors.EVENT_READ, self.accept_new_client)
            listening_port += 1

        self.handler_thread.start()
        self.main_loop()

    def main_loop(self):
        """Accepte une requête et renvoie un écho!"""
        while True:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def accept_new_client(self, sock, mask):
        try:
            clientsocket, clientaddress = sock.accept()
            logging.info(f"Connexion à {clientaddress} établies à {self.now}")
            clientsocket.setblocking(False)
            self.selector.register(clientsocket, selectors.EVENT_READ | selectors.EVENT_WRITE, self.handle_io_event)
            self.active_clients.append(clientsocket)
            self.pending_replies[clientaddress] = []
        except OSError:
            logging.error(f"Le serveur n'a pas pu établir la connexion avec un client à {self.now}")

    def handle_io_event(self, sock, mask):
        if mask & selectors.EVENT_READ:
            try:
                data = sock.recv(1024)
                if not data:
                    logging.error(f"EOF inattendu de {sock.getpeername()} à {self.now}")
                    raise OSError

                message = data.decode()
                self.pending_requests.append((message, sock.getpeername()))
                logging.info(f"Reçu : [{message}] de {sock.getpeername()} à {self.now}")

            except OSError:
                logging.error(f"Socket non-valide {sock.getpeername()} à {self.now}")
                self.selector.unregister(sock)
                sock.close()
                self.active_clients.remove(sock)

        elif mask & selectors.EVENT_WRITE:
            if self.pending_replies[sock.getpeername()]:
                text = self.pending_replies[sock.getpeername()].pop(0)
                logging.info(f"Réponse {text} retirée des réponses en attente")
                try:
                    logging.info(f"Envoi de la réponse {text} à {self.now}")
                    data = text.encode()
                    if sock.sendall(data) is not None:
                        logging.error(f"Erreur d'écriture avec le client {sock.getpeername()} à {self.now}")
                        raise OSError
                    logging.info(f"Envoyé : [{text}] à {sock.getpeername()} à {self.now}")

                except OSError:
                    logging.error(f"Socket non valide {sock.getpeername()} à {self.now}")
                    self.selector.unregister(sock)
                    sock.close()
                    self.active_clients.remove(sock)
                    self.pending_replies.pop(sock.getpeername())

        else:
            logging.warning(f"Masque inattendu: {mask} à {self.now}")

    @property
    def now(self):
        return time.ctime(time.time())

    @classmethod
    def server_config(cls, file_name):
        with open(file_name, "r") as fileObj:
            params = json.load(fileObj)

        return Serveur(host=params["host"], port=params["port"], numPortSocks=params["numPortSocks"])


if __name__ == "__main__":
    serveur = Serveur.server_config("serverconfig.json")
    serveur.start_server()
