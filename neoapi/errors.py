class WrongTypeError(Exception):

    def __init__(self, value='wrong type error'):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ParameterNotSupported(Exception):
    def __init__(self, value='wrong type error'):
        self.value = value

    def __str__(self):
        return repr(self.value)

