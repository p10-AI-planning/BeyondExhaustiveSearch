from itertools import permutations
from DataObjects.Node import Node
from DataObjects.State import State
from DataObjects.RulePredicate import RulePredicate
from DataObjects.Rule import Rule
from DataObjects.Action import Action
from DataObjects.Predicate import Predicate


class TreeBuilder:

    def __init__(self, domain, action, use_bias, use_types):
        self.domain = domain
        self.use_types = use_types
        self.root = self.build_root(action)
        self.use_bias = use_bias
        self.action = action

    def build_root(self, action):
        name = action.name
        parameters = []
        mapping = {}
        type_mapping = {}
        last_variable = []
        for i in range(len(action.parameters)):
            p = i + 1
            mapping[p] = action.parameters[i]
            if self.use_types:
                type_mapping[p] = action.type_map[action.parameters[i]]
            parameters.append(p)
            last_variable = p

        return Node(name, parameters, mapping, last_variable, [], parameters, None, State.NONE, type_mapping)

    def expand_node(self, node):
        if not node.expandable:
            return
        for name, predicate in self.domain.predicates.items():
            if self.use_types:
                common_types = (set(predicate.type_map.values()) & set(node.type_mapping.values()))
                if not common_types:
                    continue

            objects = node.free_variables
            parameter_cnt = len(predicate.parameters)
            if parameter_cnt < 1:
                continue
            objects = list(set(objects) | set(list(range(node.last_variable + 1, node.last_variable + parameter_cnt))))
            last_variable = node.last_variable + parameter_cnt - 1
            perms = permutations(objects, parameter_cnt)
            for perm in list(perms):
                parameters = list(perm)
                type_mapping = {}

                free_variables = list(set(parameters))
                if self.use_bias:
                    free_variables = list(set(free_variables) - set(node.free_variables))
                mapping = dict(zip(parameters, predicate.parameters))
                if self.use_types:
                    for parameter in parameters:
                        type_mapping[parameter] = predicate.type_map[mapping[parameter]]
                common_parameters = list(set(parameters) & set(node.parameters))
                include = True
                bound_variables = []
                for p in common_parameters:
                    bound_variables.append((node.mapping[p], mapping[p]))
                    if self.use_types and type_mapping[p] != node.type_mapping[p]:
                        include = False
                        break
                if include:
                    type_mapping.update(node.type_mapping)
                    init = Node(name, parameters, mapping, last_variable, bound_variables, free_variables, node,
                                State.INIT, type_mapping)
                    goal = Node(name, parameters, mapping, last_variable, bound_variables, free_variables, node,
                                State.GOAL, type_mapping)
                    if len(free_variables) < 1:
                        init.expandable = False
                        goal.expandable = False

                    if self.use_bias or node.is_allowed(name, parameters, State.INIT):
                        node.children.append(init)
                    if self.use_bias or node.is_allowed(name, parameters, State.GOAL):
                        node.children.append(goal)

    def create_rule(self, node):
        current_node = node
        rule_predicates = []
        while current_node.parent is not None:
            rule_predicate = RulePredicate(
                current_node.state, Predicate(current_node.name, current_node.parameters), current_node.bound_variables)
            rule_predicates.insert(0, rule_predicate)
            current_node = current_node.parent
        return Rule(Action(current_node.name, current_node.parameters), rule_predicates)
