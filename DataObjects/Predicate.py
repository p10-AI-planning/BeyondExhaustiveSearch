class Predicate:
    def __init__(self, name, parameters, type_map=None):
        if type_map is None:
            type_map = {}
        self.name = name
        self.parameters = parameters
        self.type_map = type_map

    def __str__(self):
        return f"Action: {self.name} \nParameters: {self.parameters}"

    def __eq__(self, other):
        return self.name == other.name and self.parameters == other.parameters
        

