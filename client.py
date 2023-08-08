# coding: utf-8
import selectors
import sys, socket
from select import select
import queue
import threading
import time

class Client:
    def __init__(self, host, port):
        self.serverHost = host
        self.serverPort = port

        self.sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockobj.connect((self.serverHost, self.serverPort))

        self.pending = []
        self.keepRunning = True

        self.userInputThread = threading.Thread(target=self.userInput, name="userInputThread")
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sockobj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    def userInput(self):
        while True:
            user = input("Saisir votre requête:  ")
            self.pending.append(user)
            if not user:
                self.keepRunning = False
                break
        print("Thread des saisies utilisateur terminée.")


    def handleEvent(self, mask):
        if mask & selectors.EVENT_WRITE:
            if self.pending:
                request = self.pending.pop(0)
                self.sockobj.send(request.encode())
        else:
            data = self.sockobj.recv(1024)
            message = data.decode()
            print(f"Réponse du serveur: {message} à {self.now}")


    @property
    def now(self):
        return time.ctime(time.time())

    def startClient(self):
        self.userInputThread.start()

        while self.keepRunning:

            events = self.selector.select()
            for _, mask in events:
                self.handleEvent(mask)

        self.shutDownClient()

    def shutDownClient(self):
        self.selector.modify(fileobj=self.sockobj, events=selectors.EVENT_WRITE)

        while self.pending:
            request = self.pending.pop(0)
            keepTrying = True

            while keepTrying:
                events = self.selector.select()

                for key, mask in events:
                    if key.fileobj == self.sockobj and mask & selectors.EVENT_WRITE:
                        self.sockobj.send(request.encode())
                        keepTrying = False
                        break

        self.sockobj.close()

if __name__ == "__main__":
    client = Client("localhost", 50007)
    client.startClient()

