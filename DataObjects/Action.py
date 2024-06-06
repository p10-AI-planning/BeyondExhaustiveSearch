class Action:

    def __init__(self, name="", parameters=None, type_map=None, preconditions=None, effects=None):
        if type_map is None:
            type_map = {}
        if parameters is None:
            parameters = []
        self.name = name
        self.parameters = parameters
        self.type_map = type_map
        self.preconditions = preconditions
        self.effects = effects

    def __str__(self):
        return f"Action: {self.name} \nParameters: {self.parameters}"

    def __eq__(self, other) -> bool:
        if self.name == other.name:
            if len(self.parameters) == len(other.parameters):
                for idx in range(0, len(self.parameters)):
                    if self.parameters[idx] != other.parameters[idx]:
                        return False
                return True
        return False

