import uuid
from datetime import datetime


class Conversation:

    def __init__(self, conversation_id=None):
        if conversation_id is None:
            conversation_id = uuid.uuid4()

        self.id = conversation_id
        self.date_started = datetime.now()
        self.messages = []

    def get_messages(self):
        return self.messages

    def add_message(self, message):
        self.messages.append(message)

    def how_long(self):
        return datetime.now() - self.date_started


if __name__ == '__main__':
    conv = Conversation()
    print(conv.id)
    print(conv.date_started)

    from time import sleep
    sleep(1000000000)
    print(conv.how_long().seconds)