from socket import socket, AF_INET, SOCK_STREAM
import selectors
import time
import json


class Serveur:
    def __init__(self, **kwargs):
        self.numPortSocks = kwargs["numPortSocks"]
        self.host = kwargs["host"]
        self.port = kwargs["port"]
        self.selector = selectors.DefaultSelector()
        self.activeClients, self.pendingRequests = [], []

    def startServer(self):
        myPort = self.port
        for i in range(self.numPortSocks):
            portsock = socket(AF_INET, SOCK_STREAM)
            portsock.bind((self.host, myPort))
            portsock.listen(5)
            portsock.setblocking(False)
            self.selector.register(portsock, selectors.EVENT_READ, self.accept)
            myPort += 1

        self.mainloop()

    def mainloop(self):
        """Accepte une requête et renvoie un écho!"""
        while True:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def accept(self, sock, mask):
        connection, address = sock.accept()
        print(f"Connexion à {address} établies à {self.now}")
        connection.setblocking(False)
        self.selector.register(connection, selectors.EVENT_READ | selectors.EVENT_WRITE, self.handleEvent)
        self.activeClients.append(connection)

    def handleEvent(self, sock, mask):
        if mask & selectors.EVENT_READ:
            data = sock.recv(1024)
            if not data:
                print(f"Le client {sock.getpeername()} désire se déconnecter.")
                for request in self.pendingRequests:
                    (text, address) = request
                    if address == sock.getpeername():
                        self.pendingRequests.remove(request)
            else:
                message = data.decode()
                self.pendingRequests.append((message, sock.getpeername()))
                print(f"Reçu : [{message}] de {sock.getpeername()} à {self.now}")
        else:
            for request in self.pendingRequests:
                (text, peer) = request
                if peer == sock.getpeername():
                    reply = f"Écho: {text}"
                    sock.send(reply.encode())
                    print(f"Envoyé : [{text}] à {sock.getpeername()} à {self.now}")
                    self.pendingRequests.remove(request)
                    break

    @property
    def now(self):
        return time.ctime(time.time())

    @classmethod
    def serverConfig(cls, fileName):
        with open(fileName, "r") as fileObj:
            params = json.load(fileObj)

        return Serveur(host=params["host"], port=params["port"], numPortSocks=params["numPortSocks"])


if __name__ == "__main__":
    serveur = Serveur.serverConfig("serverconfig.json")
    serveur.startServer()
