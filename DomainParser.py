import pddl as pddl_parser
from operator import attrgetter
from DataObjects.Action import Action
from DataObjects.Predicate import Predicate
from DataObjects.Domain import Domain


class PDDLDomain:

    def __init__(self, name, predicates, actions):
        self.name = name
        self.predicates = predicates
        self.actions = actions

    def __str__(self):
        return f"Domain: {self.name}\nPredicates: {self.predicates}\nActions: {self.actions}"

    @classmethod
    def from_pddl_file(cls, domain_path):
        domain = pddl_parser.parse_domain(domain_path)
        name = domain.name

        # Create Predicate instances
        predicates = {"": Predicate}
        predicates.clear()
        for pred in domain.predicates:
            parameters = []
            types = {}
            for term in pred.terms:
                parameters.append(term.name)
                if term.type_tags:
                    t, *_ = term.type_tags
                    types[term.name] = str(t)
            predicates[pred.name] = Predicate(pred.name, parameters, types)

        # Create Action instances
        actions = {"": Action}
        actions.clear()
        for action in domain.actions:
            parameters = []
            types = {}
            preconditions = []
            effects = []

            # parameters
            for parameter in action.parameters:
                parameters.append(parameter.name)
                if parameter.type_tags:
                    t, *_ = parameter.type_tags
                    types[parameter.name] = str(t)

            # preconditions
            if hasattr(action.precondition, "SYMBOL"):
                if action.precondition.SYMBOL != 'and':
                    raise Exception("unsupported action preconditions")  # We don't support "or" yet

                for pre in action.precondition.operands:
                    if hasattr(pre, "SYMBOL"):
                        continue
                    preconditions.append(Predicate(pre.name, [term.name for term in pre.terms]))
            else:
                preconditions.append(Predicate(action.precondition.name, [term.name for term in action.precondition.terms]))

            # effects
            if hasattr(action.effect, "operands"):
                for effect in action.effect.operands:
                    if hasattr(effect, "argument") or hasattr(effect, "terms"):
                        if hasattr(effect, "SYMBOL"):
                            effects.append((Predicate(effect.argument.name, [term.name for term in effect.argument.terms]), False))
                        else:
                            effects.append((Predicate(effect.name, [term.name for term in effect.terms]), True))
            else:
                effect = action.effect
                if hasattr(effect, "SYMBOL"):
                    effects.append(
                        (Predicate(effect.argument.name, [term.name for term in effect.argument.terms]), False))
                else:
                    effects.append((Predicate(effect.name, [term.name for term in effect.terms]), True))

            actions[str(action.name).lower()] = Action(str(action.name).lower(), parameters, types, preconditions, effects)

        defaultObjects = []
        for obj in domain.constants:
            defaultObjects.append(obj.name)

        return Domain(name, predicates, actions, defaultObjects)
