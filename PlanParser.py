import re

from DataObjects.Action import Action


class PlanParser:

    @staticmethod
    def parse_plan(file_name):
        parsed_actions = []
        with open(file_name, 'r') as file:
            for line in file:
                if line.startswith(";"):
                    break
                action = PlanParser.parse_action(line)
                if action:
                    parsed_actions.append(action)
        return parsed_actions

    @staticmethod
    def parse_action(action_str):
        match = re.match(r'\((\w+)\s+([\w\d]+(?:\s+[\w\d]+)*)\)', action_str)
        if match:
            action_type = match.group(1)
            parameters = match.group(2).split()  # Convert to list to capture all parameters
            return Action(action_type, parameters)
        else:
            return None
