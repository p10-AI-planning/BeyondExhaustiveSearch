from POCL.POCLNode import POCLNode


class FactNode(POCLNode):
    def __init__(self, level, fact):
        super().__init__(level)
        self.fact = fact

    def __eq__(self, other):
        return self.fact == other.fact

    def __str__(self):
        return f"{self.level}: ({self.fact.name} {self.fact.parameters})"

    def find_init_facts(self):
        fact_nodes = []
        for node in self.to_edges:
            if hasattr(node, "state"):
                if node.state == "Init":
                    return [self]
            fact_nodes.extend([x for x in node.find_init_facts() if x not in fact_nodes])
        return fact_nodes

    def find_goal_facts(self):
        fact_nodes = []
        for node in self.from_edges:
            if hasattr(node, "state"):
                if node.state == "Goal":
                    return [self]
            fact_nodes.extend([x for x in node.find_goal_facts() if x not in fact_nodes])
        return fact_nodes
