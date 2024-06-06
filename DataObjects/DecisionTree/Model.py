import os
import sys
import pickle
import pddl as pip_package_pddl


root_folder_path =  os.path.dirname(os.path.realpath(__file__))
while True:
    if not os.path.isdir(root_folder_path):
        raise FileExistsError("Unable to locate package folders")
    dirs = os.listdir(root_folder_path)
    if "DataHandler" in dirs:
        break
    root_folder_path = os.path.dirname(root_folder_path)

sys.path.append(root_folder_path)

from DataHandler.DatabaseHandlerV2 import DatabaseHandlerV2
from DataObjects.LitraToNumber import LitraToNumber
from DataObjects.Predicate import Predicate
from DataObjects.Problem import Problem
from DomainParser import PDDLDomain


class Model:

    def __init__(self, domain_path, problem_path, model_path):

        self.domain = pip_package_pddl.parse_domain(domain_path)
        self.problem = self.problem_parser(problem_path)
        domain = PDDLDomain.from_pddl_file(domain_path)
        self.db_handler = DatabaseHandlerV2(domain, False, True)
        self.db_handler.insert_problem(self.problem)
        self.model_dict = {}
        for action in self.domain.actions:
            file = open(model_path + f"model_{self.domain.name}_{action.name}.model", 'rb')
            model = pickle.load(file)
            model.add_data_handler(self.db_handler)
            self.model_dict[action.name] = model
            file.close()
        self.evaluated_operators = {}

    def problem_parser(self, path):
        problem = pip_package_pddl.parse_problem(path)

        default_objects = []

        for obj in self.domain.constants:
            default_objects.append(obj.name)

        converter = LitraToNumber(default_objects)

        for obj in problem.objects:
            converter.add_litra(obj.name)

        init = self.predicate_parser(converter, problem.init)
        # convert goal from problem. if goal contains one predicate it is type Predicate otherwise type And
        problem_goal = []
        if type(problem.goal) is pddl.logic.base.And:
            problem_goal = problem.goal.operands
        else:
            problem_goal.append(problem.goal)

        goal = self.predicate_parser(converter, problem_goal)

        prob = Problem()
        prob.init = init
        prob.goal = goal
        prob.litraToNumber = converter
        return prob

    def predicate_parser(self, converter: LitraToNumber, predicates: frozenset):
        retval = []
        for predicate in predicates:
            p = Predicate(predicate.name, [])
            obj_list = []
            for term in predicate.terms:
                obj_list.append(converter.get_number(term.name))
            p.parameters = obj_list
            retval.append(p)
        return retval

    def is_good_operator(self, action_name, operator):
        result = 1
        if str(operator) in self.evaluated_operators.keys():
            result = self.evaluated_operators[str(operator)]
        else:
            new_operator = []
            for item in operator:
                new_operator.append(self.problem.litraToNumber.get_number(item))
            if action_name in self.model_dict.keys():
                result = self.model_dict[action_name].evaluate(new_operator)

            self.evaluated_operators[str(operator)] = result
        return result == 1

    def is_bad_operator(self, action_name, operator):
        result = 1
        if str(operator) in self.evaluated_operators.keys():
            result = self.evaluated_operators[str(operator)]
        else:
            new_operator = []
            for item in operator:
                new_operator.append(self.problem.litraToNumber.get_number(item))
            if action_name in self.model_dict.keys():
                result = self.model_dict[action_name].evaluate(new_operator)

            self.evaluated_operators[str(operator)] = result
        return result == 0
