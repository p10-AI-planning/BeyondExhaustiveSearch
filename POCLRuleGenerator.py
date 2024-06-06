import itertools
import logging
import time
from DataObjects.Action import Action
from DataObjects.Predicate import Predicate
from DataObjects.Rule import Rule
from DataObjects.RulePredicate import RulePredicate
from DataObjects.State import State

logger = logging.getLogger(__name__)


class POCLRuleGenerator:

    def __init__(self, graphs, domain):
        self.graphs = graphs
        self.domain = domain

    def generate_rules(self, action, number_of_rules=2000, time_limit=60):
        rules = {}
        start_time = time.time()
        break_loop = False
        for graph in self.graphs:
            if break_loop:
                    break
            for node in graph.actions:
                if time.time() - start_time > time_limit:
                    break_loop = True
                    break
                if node.action.name == action.name:
                    init_facts = [x.fact for x in node.find_init_facts()]
                    goal_facts = [x.fact for x in node.find_goal_facts()]
                    rule_facts = [RulePredicate(State.INIT, fact, []) for fact in init_facts]
                    rule_facts.extend([RulePredicate(State.GOAL, fact, []) for fact in goal_facts])
                    for i in range(len(rule_facts)):
                        if time.time() - start_time > time_limit:
                            break
                        combinations = list(itertools.combinations(rule_facts, i + 1))
                        for item in combinations:
                            if time.time() - start_time > time_limit:
                                break
                            rule = self.construct_rule(node.action, item)
                            include = self.analyze_rule(rule)
                            if include:
                                if hash(rule) in rules.keys():
                                    rules[hash(rule)] = (rules[hash(rule)][0], rules[hash(rule)][1] + 1)
                                else:
                                    rules[hash(rule)] = (rule, 1)

        logger.info(f"Rule Generation took {time.time() - start_time}s")
        return [x[0] for x in sorted(rules.values(), key=lambda x: x[1], reverse=True)[:number_of_rules]]

    def construct_rule_combinations(self, action, init_facts, goal_facts):
        rules = []
        rule_facts = [RulePredicate(State.INIT, fact, []) for fact in init_facts]
        rule_facts.extend([RulePredicate(State.GOAL, fact, []) for fact in goal_facts])
        for i in range(len(rule_facts)):
            combinations = list(itertools.combinations(rule_facts, i + 1))
            for item in combinations:
                rules.append(self.construct_rule(action, item))
        return rules

    def construct_rule(self, action, rule_facts):
        sorted_facts = sorted(rule_facts, key=lambda x: (x.state, x.predicate.name))
        rule_action = Action(action.name, [x for x in action.parameters])  # copy to remove relations
        next_value = 1
        lookup = {}

        for idx, parameter in enumerate(rule_action.parameters):
            if parameter in lookup.keys():
                rule_action.parameters[idx] = lookup[parameter]
            else:
                rule_action.parameters[idx] = next_value
                lookup[parameter] = next_value
                next_value += 1

        facts = []

        for fact in sorted_facts:
            predicate = Predicate(fact.predicate.name, [x for x in fact.predicate.parameters])
            rule_fact = RulePredicate(fact.state, predicate, [])
            for idx, parameter in enumerate(rule_fact.predicate.parameters):
                if parameter in lookup.keys():
                    rule_fact.predicate.parameters[idx] = lookup[parameter]
                else:
                    rule_fact.predicate.parameters[idx] = next_value
                    lookup[parameter] = next_value
                    next_value += 1
            facts.append(rule_fact)

        return Rule(rule_action, facts)

    def analyze_rule(self, rule):
        parameter_to_link_dir = {}
        parameter_to_str = {}
        list_of_links = []
        predicates_bound = []
        # logger.info(rule)

        for parameter in range(1, len(rule.action.parameters) + 1):
            parameter_to_str[parameter] = self.domain.actions[rule.action.name].parameters[parameter - 1]
            parameter_to_link_dir[parameter] = 0

        link_idx = 1
        for rule_predicate in rule.rule_predicates:
            for parameterIdx in range(0, len(rule_predicate.predicate.parameters)):
                parameter = rule_predicate.predicate.parameters[parameterIdx]
                if parameter not in parameter_to_link_dir:

                    parameter_to_link_dir[parameter] = link_idx
                    parameter_to_str[parameter] = self.domain.predicates[rule_predicate.predicate.name].parameters[
                        parameterIdx]
                else:
                    list_of_links.append(
                        (parameter_to_link_dir[parameter], (parameter_to_str[parameter], self.domain.predicates[
                            rule_predicate.predicate.name].parameters[parameterIdx])))
                    rule_predicate.bound_linkings.append(list_of_links[-1])
                    predicates_bound.append(parameter_to_link_dir[parameter])
                    # logger.info(listOfLinks[-1])
            link_idx += 1

        for i in range(0, len(rule.rule_predicates)):
            if i not in predicates_bound:
                return False
        return True
