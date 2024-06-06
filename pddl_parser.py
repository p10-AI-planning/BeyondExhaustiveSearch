import pddl
from DataObjects.Action import Action
from DataObjects.Predicate import Predicate
from operator import attrgetter

class PddlParser:

    @staticmethod
    def get_name(domain_path):
        domain = pddl.parse_domain(domain_path)

        name = getattr(domain, 'name', [])
        return name

    @staticmethod
    def get_actions(domain_path):
        domain = pddl.parse_domain(domain_path)
        actions = {"": Action}
        actions.clear()
        for action in domain.actions:
            actions[action.name] = Action(action.name, [parameter.name for parameter in action.parameters])

    @staticmethod
    def get_predicates(domain_path):
        domain = pddl.parse_domain(domain_path)

        # Create Predicate instances
        predicates = {"": Predicate}
        predicates.clear()
        for pred in domain.predicates:
            predicates[pred.name] = Predicate(pred.name, [term.name for term in pred.terms])

    @staticmethod
    def print_actions(domain_path):
        actions_list = PddlParser.get_actions(domain_path)
        print("Actions in the domain:")
        for action in actions_list:
            print(action)

    @staticmethod
    def print_predicates(domain_path):
        predicates_list = PddlParser.get_predicates(domain_path)
        print("Predicates in the domain:")
        for predicates in predicates_list:
            print(predicates)