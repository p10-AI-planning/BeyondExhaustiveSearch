from POCL.POCLNode import POCLNode


class StateNode(POCLNode):
    def __init__(self, level, state):
        super().__init__(level)
        self.state = state

    def __str__(self):
        return f"{self.level}: ({self.state})"
