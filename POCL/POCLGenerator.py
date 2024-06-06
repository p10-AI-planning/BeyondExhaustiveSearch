from DataObjects.Predicate import Predicate
from POCL.ActionNode import ActionNode
from POCL.FactNode import FactNode
from POCL.POCLGraph import POCLGraph
from POCL.POCLNode import POCLNode
from POCL.StateNode import StateNode


class POCLGenerator:
    def __init__(self, domain):
        self.domain = domain

    def generate_graph(self, problem):
        facts = []
        actions = []
        init_node = StateNode(0, "Init")
        goal_node = StateNode(0, "Goal")
        # Initial state
        for fact in problem.init:
            if fact.parameters:
                fact_node = FactNode(1, fact)
                init_node.from_edges.append(fact_node)
                fact_node.to_edges.append(init_node)
                facts.append(fact_node)
        current_facts = [node for node in facts]

        for action in problem.plan:
            domain_action = self.domain.actions[action.name]
            lookup = dict(zip(domain_action.parameters, action.parameters))
            for const in self.domain.constants:
                lookup[const] = problem.litraToNumber.objStrToInt[const]

            node = ActionNode(0, action)

            # Add precondition links
            for pre in domain_action.preconditions:
                precondition = Predicate(pre.name, [lookup[term] for term in pre.parameters])
                for fact_node in current_facts:
                    if fact_node.fact == precondition:
                        fact_node.from_edges.append(node)
                        node.to_edges.append(fact_node)
                        if node.level <= fact_node.level:
                            node.level = fact_node.level + 1

            # Add Effects
            for eff in domain_action.effects:
                if not eff[0].parameters:
                    continue
                effect = Predicate(eff[0].name, [lookup[term] for term in eff[0].parameters])
                fact_node = FactNode(node.level + 1, effect)
                if eff[1]:
                    existing_fact = next((n for n in current_facts if fact_node == n), None)
                    if existing_fact is None:
                        node.from_edges.append(fact_node)
                        fact_node.to_edges.append(node)
                        facts.append(fact_node)
                        current_facts.append(fact_node)
                    else:
                        node.from_edges.append(existing_fact)
                        existing_fact.to_edges.append(node)
                        if existing_fact.level <= node.level:
                            existing_fact.level = node.level + 1
                else:
                    if fact_node in current_facts:
                        current_facts.remove(fact_node)

            actions.append(node)

        for node in facts:
            if node.fact in problem.goal:
                if goal_node.level <= node.level:
                    goal_node.level = node.level + 1
            elif goal_node.level <= node.level:
                goal_node.level = node.level + 2

        for node in current_facts:
            if node.fact in problem.goal:
                node.from_edges.append(goal_node)
                goal_node.to_edges.append(node)

        for node in goal_node.to_edges:
            node.level = goal_node.level - 1

        return POCLGraph(facts, actions, init_node, goal_node)
