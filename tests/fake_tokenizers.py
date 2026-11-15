class CharacterTokenizer:
    """Offline chat-tokenizer stand-in: one id per character, and the end-of-turn marker is one id.

    It records every conversation it templates so tests can count template applications.
    """

    chat_template = 'character-test-template'

    def __init__(self, eos_token: str = '<eot>') -> None:
        self.eos_token = eos_token
        self.conversations: list[list[dict[str, str]]] = []

    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]:
        assert not add_special_tokens
        ids: list[int] = []
        for index, piece in enumerate(text.split(self.eos_token)):
            if index:
                ids.append(0)
            ids.extend(ord(character) for character in piece)
        return ids

    def apply_chat_template(self, conversation: list[dict[str, str]], *, tokenize: bool = False,
                            add_generation_prompt: bool = True) -> str:
        assert not tokenize and add_generation_prompt
        self.conversations.append(list(conversation))
        return '<chat>' + ''.join(f"<{message['role']}>{message['content']}{self.eos_token}"
                                  for message in conversation) + '<assistant>'
