from POCL.POCLNode import POCLNode


class ActionNode(POCLNode):
    def __init__(self, level, action):
        super().__init__(level)
        self.action = action

    def __str__(self):
        return f"{self.level}: ({self.action.name} {self.action.parameters})"

    def find_init_facts(self):
        fact_nodes = []
        for node in self.to_edges:
            fact_nodes.extend([x for x in node.find_init_facts() if x not in fact_nodes])
        return fact_nodes

    def find_goal_facts(self):
        fact_nodes = []
        for node in self.from_edges:
            fact_nodes.extend([x for x in node.find_goal_facts() if x not in fact_nodes])
        return fact_nodes
