from DataObjects.State import convert_state_to_string, State


class Node:

    def __init__(self, name, parameters, mapping, last_variable, bound_variables, free_variables, parent, state,
                 type_mapping=None):
        if type_mapping is None:
            type_mapping = {}
        self.name = name
        self.parameters = parameters
        self.mapping = mapping
        self.children = []
        self.last_variable = last_variable
        self.bound_variables = bound_variables
        self.free_variables = free_variables
        self.expandable = True
        self.parent = parent
        self.state = state
        self.type_mapping = type_mapping

    def __str__(self, level=0):
        prefix = ""
        if not self.state == State.NONE:
            prefix = f"{convert_state_to_string(self.state)}:"
        result = ("  " * level +
                  f"{prefix}{self.name}({', '.join(map(str, self.parameters))})")

        for child in self.children:
            result += "\n" + child.__str__(level + 1)

        return result

    def is_allowed(self, name, parameters, state):
        if self.name == name and self.parameters == parameters and self.state == state:
            return False
        elif self.parent is None:
            return True
        else:
            return self.parent.is_allowed(name, parameters, state)

