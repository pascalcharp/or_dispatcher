from socket import socket, AF_INET, SOCK_STREAM
import selectors
import time
import json
import logging
import threading

from RequestHandler import RequestHandler


class SocketException(Exception):
    pass


class WriteEventSocketException(SocketException):
    pass


class Serveur:
    def __init__(self, **kwargs):
        """
        Constructeur de la classe Serveur. Initialise le sélecteur, le gestionnaire de requêtes et son thread de
        contrôle, ainsi que la liste des sockets écoutants, des sockets clients, des requêtes en attentes et le
        dictionnaire des réponses en attente.
        :param kwargs: Dictionnaire contenant les entrées "host" et "port" et "numPortSock".  "port" sera le numéro
        du premier port écoutant, et les numPortSocks consécutifs suivants seront aussi connectés pour écoute.
        """
        logging.basicConfig(filename="server.log", level=logging.INFO)
        self.numPortSocks = kwargs["numPortSocks"]
        self.host = kwargs["host"]
        self.port = kwargs["port"]
        self.selector = selectors.DefaultSelector()
        self.listening_sockets = []
        self.active_clients, self.pending_requests, self.pending_replies = [], [], {}

        self.request_handler = RequestHandler()
        self.keep_handling_requests = True
        self.handler_thread = threading.Thread(target=self.start_handler_thread, name="handlerthread")

    def start_handler_thread(self):
        """
        Démarre le thread du gestionnaire de requête. Celui-ci est responsable de retirer une requête de la file des
        requêtes en attente, traiter cette requête, et mettre les réponses générées dans le dictionnaire des réponses
        en attente, au destinataire adéquat.
        :return: None
        """
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
        """
        Connecte le serveur à ses ports d'écoute.  Si aucun port n'est disponible le serveur n'est pas démarré.
        Si au-moins un port a été contacté avec succès, la boucle principale du serveur est démarrée, ainsi que le
        thread s'occupant de traiter les requêtes.
        :return: None
        """
        listening_port = self.port
        for i in range(self.numPortSocks):
            try:
                portsock = socket(AF_INET, SOCK_STREAM)
                portsock.bind((self.host, listening_port))
                portsock.listen(5)
                portsock.setblocking(False)
                self.selector.register(portsock, selectors.EVENT_READ, self.accept_new_client)
                self.listening_sockets.append(portsock)
            except OSError:
                logging.error(f"Impossible d'écouter sur le port {listening_port} à {self.now}")
            listening_port += 1
        if self.listening_sockets:
            self.handler_thread.start()
            self.main_loop()
        else:
            logging.error("Le serveur ne peut être démarré car aucun port d'écoute n'est disponible.")

    def main_loop(self):
        """
        Réagit aux évènements retournés par le sélecteur, soit que des sockets sont prêts en lecture, soit en écriture.
        :return: None
        """
        while True:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def accept_new_client(self, sock, mask):
        """
        Accepte une demande de connexion sur un socket d'écoute.  Un nouveau socket client est intégré à la liste des
        clients existants.  Ce socket est enregistré dans le sélecteur, et une entrée est créée dans le dictionnaire
        des réponses.
        :param sock: Le socket d'écoute ayant reçu la demande de connexion
        :param mask: Non-utilisé
        :return: None
        """
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
        """
        Réagit à un évènement retourné par le sélecteur. Si le socket est prêt en lecture, le message est lu sur le
        socket et intégré à la file des messages reçus, avec l'adresse du socket envoyeur. Si le socket est prêt en
        écriture, on vérifie d'abord qu'il y a au-moins un message en attente pour ce socket, si oui, il est retiré
        du dictionnaire des messages en attente, et envoyé sur le socket.  Si une erreur se produit en lecture ou en
        écriture, le socket est retiré de la liste des clients actifs, désenregistré du sélecteur, et fermé.
        :param sock: Socket client qui est prêt
        :param mask: Indique si le socket est prêt en lecture (selectors.EVENT_READ) ou en écriture
        (selectors.EVENT_WRITE)
        :return: None
        """
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
        """Retourne l'heure système sous forme de string"""
        return time.ctime(time.time())

    @classmethod
    def server_config(cls, file_name):
        """
        Retourne un objet serveur configuré avec un fichier de configuration au format json contenant les entrées:
        "port": le port initial d'écoute, "host": l'adresse IP du serveur, et "numPortSocks": le nombre total de
        sockets d'écoute.
        :param file_name: Nom du fichier de configuration
        :return: Un objet serveur prêt à démarrer
        """
        with open(file_name, "r") as fileObj:
            params = json.load(fileObj)

        return Serveur(host=params["host"], port=params["port"], numPortSocks=params["numPortSocks"])


if __name__ == "__main__":
    serveur = Serveur.server_config("serverconfig.json")
    serveur.start_server()
