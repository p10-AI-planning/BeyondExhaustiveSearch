import pickle
import re
import logging
from pddl import parse_problem
from pddl import parse_domain
from pddl.logic.base import And
import os
import pathlib
from DataObjects.Action import Action
from DataObjects.Predicate import Predicate
from DataObjects.Problem import Problem
from DataObjects.Domain import Domain
from DataObjects.ProblemExample import ProblemExample
from DataObjects.LitraToNumber import LitraToNumber

logger = logging.getLogger(__name__)
class ExampleGenerator:
    def __init__(self):
        pass

    def parse_all_operators(self, path):
        result = []
        file = open(path, "r")
        lines = file.readlines()

        if " ===== FILE TOO LARGE --> MIDDLE FILE CONTENTS OMITTED ===== \n" in lines:
            logger.info("All operators missing middel for: " + path)
            return result

        lineCnt = 0
        for line in lines:
            line = line.strip()
            cmds = line.split("(")
            if len(cmds) > 0:
                action = Action("", [])
                action.name = cmds[0]
                cmds[1] = cmds[1].replace(" ", "")
                cmds[1] = cmds[1].replace(")", "")
                cmds = cmds[1].split(",")
                for cmd in cmds:
                    action.parameters.append(cmd)
                lineCnt += 1
                result.append(action)
        return result

    def parse_good_operators(self, path):
        result = []
        file = open(path, "r")
        lines = file.readlines()
        if " ===== FILE TOO LARGE --> MIDDLE FILE CONTENTS OMITTED ===== \n" in lines:
            logger.info("Good operators missing middel for: " + path)
            return result
        lineCnt = 0
        for line in lines:
            line = line.strip()
            cmds = line.split(" ")
            if len(cmds) > 0:
                action = Action("", [])
                action.name = cmds[0]
                for cmdIdx in range(1, len(cmds)):
                    action.parameters.append(cmds[cmdIdx])
                lineCnt += 1
                result.append(action)
        return result

    def to_tuple(self, listToConvert: list):
        if len(listToConvert) == 1:
            listToConvert.append(-1)
        return tuple(listToConvert)

    def predicate_parser(self, converter: LitraToNumber, predicates: frozenset):
        retval = []
        for predicate in predicates:
            if not hasattr(predicate, "name"):
                continue
            p = Predicate(predicate.name, [])
            objList = []
            for term in predicate.terms:
                objList.append(converter.get_number(term.name))
            p.parameters = objList
            retval.append(p)
        return retval

    def action_parser(self, listOfAction: list, dictOfExamples: dict, converter: LitraToNumber, positiveExample: bool):
        for action in listOfAction:
            if (action.name not in dictOfExamples):
                dictOfExamples[action.name] = ProblemExample()
            objList = []
            for parameter in action.parameters:
                objList.append(converter.get_number(parameter))
            if positiveExample:
                dictOfExamples[action.name].positives.append(objList)
            else:
                dictOfExamples[action.name].negatives.append(objList)
        return dictOfExamples

    def generat_problem_examples(self, folderPath: str, domain: Domain):
        runsFolder = os.listdir(folderPath)
        runsFolder.sort()
        problemCnt = range(len(runsFolder))
        problems = []
        problems_name_used = []
        
        for number in problemCnt:
            problemPath = os.path.join(folderPath, runsFolder[number], "problem.pddl")
            allOperatorsPath = os.path.join(folderPath, runsFolder[number], "all_operators")
            goodOperatorsPath = os.path.join(folderPath, runsFolder[number], "good_operators")
            plan_path = os.path.join(folderPath, runsFolder[number], "sas_plan")

            problemExsist = pathlib.Path(problemPath).is_file()
            allOperatorsExsist = pathlib.Path(allOperatorsPath).is_file()
            goodOperatorsExsist = pathlib.Path(goodOperatorsPath).is_file()
            plan_exists = pathlib.Path(plan_path).is_file()

            if (problemExsist & allOperatorsExsist & goodOperatorsExsist & plan_exists):
                problems_name_used.append(runsFolder[number])
                actionExample = {"":[]}
                actionExample.clear()

                # Generate number for all objects in problem
                converter = LitraToNumber(domain.constants)
                problem = parse_problem(problemPath)
                for obj in problem.objects:
                    converter.add_litra(obj.name.lower())

                # convert init from problem
                init = self.predicate_parser(converter, problem.init)

                # convert goal from problem. if goal contains one predicate it is type Predicate otherwise type And
                problemGoal = []
                if (type(problem.goal) is And):
                    problemGoal = problem.goal.operands
                else:
                    problemGoal.append(problem.goal)

                goal = self.predicate_parser(converter, problemGoal)

                # add positive examples
                allOperators = self.parse_all_operators(allOperatorsPath)
                if len(allOperators) == 0:
                    continue
                goodOperators = self.parse_good_operators(goodOperatorsPath)
                if (len(goodOperators) == 0):
                    continue

                # Add positive examples
                actionExample = self.action_parser(goodOperators, actionExample, converter, True)

                # subset consist of allOperators subtracted goodOperators are negative examples
                for operator in goodOperators:
                    for opr in allOperators:
                        if (operator == opr):
                            allOperators.remove(opr)
                            break
                # Add negative examples
                actionExample = self.action_parser(allOperators, actionExample, converter, False)

                # parse plan
                plan = self.parse_plan(plan_path, converter)

                # pack problem
                problem = Problem()
                problem.name = runsFolder[number]
                problem.problemExamples = actionExample
                problem.litraToNumber = converter
                problem.goal = goal
                problem.init = init
                problem.plan = plan

                problems.append(problem)
            else:
                if(problemExsist == False):
                    logger.info("problem missing for: " + problemPath)
                if(allOperatorsExsist == False):
                    logger.info("All operators missing for: " + allOperatorsPath)
                if(goodOperatorsExsist == False):
                    logger.info("Good operators missing for: " + goodOperatorsPath)
                #write to file
        
        if pathlib.Path("examples.pe").is_file():
            os.remove("examples.pe")
        examplesFile = open("examples.pe", 'ab')
        pickle.dump(problems, examplesFile)
        examplesFile.close()
        used_problems = str(problems_name_used)
        logger.info(f"Using following problems: {used_problems}")
        return problems

    def generate_from_file(self):
        examplesFile = open("examples.pe", 'rb')
        problems = pickle.load(examplesFile)
        return problems

    def parse_plan(self, file_name, converter):
        parsed_actions = []
        with open(file_name, 'r') as file:
            for line in file:
                if line.startswith(";"):
                    break
                action = self.parse_action(line, converter)
                if action:
                    parsed_actions.append(action)
        return parsed_actions

    def parse_action(self, action_str, converter):
        match = re.match(r'\(([\w-]+)\s+(\w+(?:\s+[\w-]+)*)\)', action_str)
        if match:
            action_type = match.group(1)
            parameters = match.group(2).split()  # Convert to list to capture all parameters
            parameters = list(map(lambda x: converter.objStrToInt[x], parameters))
            return Action(action_type, parameters)
        else:
            return None
