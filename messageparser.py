import json


class InvalidMessageException(Exception):
    pass


class InvalidCommandMessageException(InvalidMessageException):
    pass


class InvalidRequestIdException(InvalidMessageException):
    pass


class InvalidUserMessageException(InvalidMessageException):
    pass


class InvalidRecipientException(InvalidMessageException):
    pass


class InvalidRoomNumberMessageException(InvalidMessageException):
    pass


class InvalidTaskMessageException(InvalidMessageException):
    pass


class InvalidDataFieldMessageException(InvalidMessageException):
    pass


class MessageIncompleteException(InvalidMessageException):
    pass


class NoStartMessageIncompleteException(MessageIncompleteException):
    pass


class NoEndMessageIncompleteException(MessageIncompleteException):
    pass


VALID_COMMANDS = {
    "logon": {"priority": 1, "fields": []},
    "logoff": {"priority": 1, "fields": []},
    "emergency": {"priority": 0, "fields": ["roomno"]},
    "new": {"priority": 2, "fields": ["task", "roomno"]},
    "respond": {"priority": 2, "fields": ["id"]},
    "acknowledge": {"priority": 2, "fields": ["id"]},
    "cancel": {"priority": 2, "fields": ["id"]}
}

VALID_TASKS = {
    "cleanup": 100,
    "spinal": 100,
    "gyneco": 100,
    "installation": 100
}

MAX_ROOM_NO = 15


class MessageParser:
    def __init__(self, commands):
        self.commands = VALID_COMMANDS

    def validUser(self, userName):
        return True

    def convertId(self, requestId):
        id = int(requestId)
        if id < 0:
            raise ValueError
        return id

    def validTask(self, task):
        return task in VALID_TASKS.keys()

    def convertRoomNumber(self, roomno):
        number = int(roomno)
        if number < 1:
            raise ValueError
        return number

    def parse(self, message):
        tokens = message.split(":")
        result = {}

        if len(tokens) < 4:
            raise MessageIncompleteException

        if tokens.pop(0) != "start":
            raise NoStartMessageIncompleteException

        if tokens.pop(-1) != "end":
            raise NoEndMessageIncompleteException

        command = tokens.pop(0)
        if command not in self.commands.keys():
            raise InvalidCommandMessageException
        result["command"] = command

        user = tokens.pop(0)
        if not self.validUser(user):
            raise InvalidUserMessageException
        result["user"] = user

        if len(tokens) != len(self.commands[command]["fields"]):
            raise MessageIncompleteException

        for field in self.commands[command]["fields"]:
            token = tokens.pop(0)
            if field == "roomno":
                try:
                    result[field] = self.convertRoomNumber(token)
                except ValueError:
                    raise InvalidRoomNumberMessageException

            elif field == "task":
                if not self.validTask(token):
                    raise InvalidTaskMessageException
                result[field] = token

            elif field == "id":
                try:
                    result[field] = self.convertId(token)
                except ValueError:
                    raise InvalidRequestIdException

            else:
                raise InvalidDataFieldMessageException

        return result

    @classmethod
    def parserConfig(cls, fileName):
        with open(fileName, "r") as fileObject:
            params = json.load(fileObject)
        return MessageParser(params["commands"])
