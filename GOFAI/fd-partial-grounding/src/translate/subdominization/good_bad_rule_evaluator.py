from collections import defaultdict
import os
import pickle
import sys
import pddl
import pddl.logic
import pddl.logic.base

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
from DomainParser import PDDLDomain
from DataObjects.DecisionTree.RuleDecisionTree import RuleDecisionTree
from DataObjects.Predicate import Predicate
from DataObjects.Problem import Problem
from DataObjects.ProblemExample import ProblemExample
from DataObjects.LitraToNumber import LitraToNumber


class GodBadRuleEvaluator:
    def __init__(self, task, args):
        self.num_good_actions = defaultdict(int)
        self.num_bad_actions = defaultdict(int)
        self.good_operators = defaultdict()
        self.bad_operators = defaultdict()
        self.domain = PDDLDomain.from_pddl_file(args.domain)
        self.domain2 = pddl.parse_domain(args.domain)
        self.problem = pddl.parse_problem(args.task)
        self.our_problem_model = ProblemToOurProblemParser().parse(self.domain2, self.problem)
        self.modelDict = {"":RuleDecisionTree}
        self.dataHandler = DatabaseHandlerV2(self.domain, False, True)
        self.dataHandler.insert_problem(self.our_problem_model)
        for key, action in self.domain.actions.items():
            self.good_operators[action.name] = []
            self.bad_operators[action.name] = []
            file_name = f"model_{self.domain.name}_{action.name}.rulemodel"
            if os.path.isfile(os.path.join(args.trained_model_folder, file_name)):
                with open(os.path.join(args.trained_model_folder, file_name),'rb') as model_file:
                    self.modelDict[action.name] = pickle.load(model_file)
                    self.modelDict[action.name].add_data_handler(self.dataHandler)


    def get_action_schemas(self):
        return set()
    
    def is_good_action(self, action):
        if action.predicate.name in self.modelDict.keys():
            if self.modelDict[action.predicate.name].evaluate(action.args):
                self.num_good_actions[action.predicate.name] += 1
                self.good_operators[action.predicate.name].append(action.args)
                return True
            else:
                return False
        else:
            return False
    
    def is_bad_action(self, action):
        if action.predicate.name in self.modelDict.keys():
            if not self.modelDict[action.predicate.name].evaluate(action.args):
                self.num_bad_actions[action.predicate.name] += 1
                self.bad_operators[action.predicate.name].append(action.args)
                return True
            else:
                False
        else:
            return False
    
    def print_stats(self):
        for schema, num in self.num_good_actions.items():
            print(f"Detected {num} good operators of action schema {schema}.")
        for schema, num in self.num_bad_actions.items():
            print(f"Detected {num} bad operators of action schema {schema}.")


class ProblemToOurProblemParser:
    def __init__(self):
        pass
    
    def to_tuple(self, listToConvert:list):
        if len(listToConvert) == 1:
            listToConvert.append(-1)
        return tuple(listToConvert)
    
    def predicate_parser(self, converter: LitraToNumber, predicates: frozenset):
        retval = []
        for predicate in predicates:
            p = Predicate(predicate.name, [])
            objList = []
            for term in predicate.terms:
                objList.append(converter.get_number(term.name))
            p.parameters = objList
            retval.append(p)
        return retval
    
    def action_parser(self, listOfAction: list, dictOfExamples: dict, converter: LitraToNumber, positiveExample: bool):
        for action in listOfAction:
            if(action.name not in dictOfExamples):
                dictOfExamples[action.name] = ProblemExample()
            objList = []
            for parameter in action.parameters:
                objList.append(converter.get_number(parameter))
            if positiveExample:
                dictOfExamples[action.name].positives.append(objList)
            else:
                dictOfExamples[action.name].negatives.append(objList)
        return dictOfExamples


    def parse(self, input_domain, input_problem):
        actionExample = {"":[]}
        actionExample.clear()
        defaultObjects = []
        for obj in input_domain.constants:
            defaultObjects.append(obj.name)

        #Generate number for all objects in problem
        converter = LitraToNumber(defaultObjects)
        for obj in input_problem.objects:
            converter.add_litra(obj.name)

        #convert init from problem
        init = self.predicate_parser(converter, input_problem.init)
        
        #convert goal from problem. if goal contains one predicate it is type Predicate otherwise type And
        problemGoal = []
        if(type(input_problem.goal) is pddl.logic.base.And):
            problemGoal = input_problem.goal.operands
        else:
            problemGoal.append(input_problem.goal)
            
        goal = self.predicate_parser(converter, problemGoal)

        #pack problem
        problem = Problem()
        problem.name = input_problem.name
        problem.problemExamples = actionExample
        problem.litraToNumber = converter
        problem.goal = goal
        problem.init = init
        
        return problem