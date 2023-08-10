import logging

class RequestHandler:
    def __init__(self):
        self.handle_message = "Handled: "

    def handle(self, request):
        logging.debug(f"Entrée dans handle!")
        request_text, peer = request
        return self.handle_message + request_text, peer

