import os
import re

from DataHandler.DatabaseHandler import DatabaseHandler
from DataObjects.CandidateRule import CandidateRule
from DataObjects.ConfusionMatrix import ConfusionMatrix
from DomainParser import PDDLDomain
from Evaluation.Evaluator import Evaluator
from ExampleGenerator import ExampleGenerator


class Predicate:
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters


class AlephRule:
    def __init__(self, head, body):
        self.head = head
        self.body = body


class AlephHypothesisRule:
    def __init__(self, rule_string, pos, neg):
        self.rule = rule_string
        self.pos = pos
        self.neg = neg


def parse_rule(rule_str, predicates):
    # Split the rule into head and body
    head_str, body_str = map(str.strip, rule_str.split(":-"))

    # Parse head
    head = parse_predicate(head_str, predicates)

    # Parse body
    body = [parse_predicate(pred_str, predicates) for pred_str in body_str.split(";")]

    return AlephRule(head, body)


def parse_predicate(predicate_str, predicates):
    # Extract predicate name and parameters
    predicate_str = predicate_str.replace(" ", "")
    match = re.match(r"(\w+):(\w+(?:-\w+)?)\(([^)]*)\)|(\w+)\(([^)]*)\)|(\w+):\(([^)]*)\)", predicate_str)

    if match:
        prefix, name, param_str1, name2, param_str2, name3, param_str3 = match.groups()
        name = name if name else name2 if name2 else name3

        param_str_to_use = param_str1 if param_str1 else param_str2 if param_str2 else param_str3
        # Parse parameters
        param_names = [param.strip() for param in param_str_to_use.split(",")]
        parameters = list(zip(predicates[name], param_names))
        if prefix:
            # Translate prefixes
            if prefix == "ini":
                prefix = "init"
            elif prefix == "goal":
                prefix = "goal"
            name = f"{prefix}{name}".replace("-", "_")

        return Predicate(name, parameters)
    else:
        raise ValueError(f"Invalid predicate format: {predicate_str}")


def create_statement(parsed_rule, prefix, predicates):
    alias_number = 0
    from_clause = prefix + parsed_rule.head.name + f" a{alias_number}"
    conditions = []
    seen_variables = {}
    selectors = []
    equals = []
    for param in parsed_rule.head.parameters:
        seen_variables[param[1]] = f"a{alias_number}.{param[0]}"
        selectors.append(f"a{alias_number}.{param[0]}")
    for p in parsed_rule.body:
        if p.name == "equal":
            equals.append(p)
            continue
        alias_number = alias_number + 1
        alias = f"a{str(alias_number)}"
        from_clause += f" JOIN {p.name} {alias}"
        for param in p.parameters:
            if param[1] == "_":
                continue
            if param[1] in seen_variables:
                conditions.append(f"{seen_variables[param[1]]} = {alias}.{param[0]} ")
            else:
                seen_variables[param[1]] = f"{alias}.{param[0]}"
    for eq in equals:
        conditions.append(f"{seen_variables[eq.parameters[0][1]]} = {seen_variables[eq.parameters[1][1]]}")

    condition_string = " AND ".join(conditions)
    selector_string = ", ".join(selectors)
    command = f"SELECT DISTINCT {selector_string} FROM {from_clause} ON {condition_string}"
    return command


def parse_lines(input_str):
    lines = input_str.split(".")
    # Remove empty lines and leading/trailing whitespaces
    lines = [line.strip() for line in lines if line.strip()]
    return lines


def evaluate_aleph_hypothesis(hypothesis_strings, domain):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path_split = dir_path.split("\\")
    dir_path = dir_path_split[0]
    for i in range(1, len(dir_path_split)):
        dir_path += "\\" + dir_path_split[i]
    fold_path = dir_path + "\\Data\\" + domain


    # parse domain
    domain = PDDLDomain.from_pddl_file(fold_path + "\\domain.pddl")
    predicates = {}
    for key, predicate in domain.predicates.items():
        predicates[key] = predicate.parameters
    predicates["equal"] = ["x", "y"]
    db_handler = DatabaseHandler(domain, "YAPHG_" + domain.name)
    evaluator = Evaluator(db_handler)
    example_generator = ExampleGenerator()
    examples = example_generator.generat_problem_examples(fold_path, True)
    total_eval = ConfusionMatrix()
    for problem in examples:
        db_handler.create_problem(problem)
    hypothesis = []
    for key, action in domain.actions.items():
        predicates[key] = action.parameters
        hypothesis_to_evaluate = []
        if key in hypothesis_strings:
            for line in parse_lines(hypothesis_strings[key]):
                rule = parse_rule(line, predicates)
                pos = create_statement(rule, "pos", predicates)
                neg = create_statement(rule, "neg", predicates)
                hypothesis.append(AlephHypothesisRule(line, pos, neg))
                hypothesis_to_evaluate.append(CandidateRule(line, pos, neg))

        matrix = ConfusionMatrix()
        for problem in examples:
            matrix += evaluator.evaluate_hypothesis(hypothesis_to_evaluate, problem, action)
        total_eval += matrix
        db_handler.create_hypothesis(hypothesis_to_evaluate, matrix, action)

    db_handler.save_aleph_hypothesis(hypothesis, total_eval)
