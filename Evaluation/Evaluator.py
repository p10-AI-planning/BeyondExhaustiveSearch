import time

from DataHandler.DatabaseHandler import DatabaseHandler
from DataObjects.State import convert_state_to_string
from DataObjects.ConfusionMatrix import ConfusionMatrix
from DataObjects.CandidateRule import CandidateRule


class Evaluator:

    def __init__(self, db_handler):
        self.db_handler = db_handler

    # Rule:{
    #   Action:{
    #       name = "pickup"
    #       parameters = [1]
    #   },
    #   rule_predicates: [{
    #   state = INIT
    #   predicate = {
    #       name = "on"
    #       parameters = [1,2]
    #       bound_variables = [(x,x)]
    #   }, {
    #   state = GOAL
    #   predicate = {
    #       name = "clear"
    #       parameters = [2]
    #       bound_variables = [(y,x)]
    #   {]

    def evaluate(self, rule, problem, pos_table_name, neg_table_name):
        conn = self.db_handler.get_connection(problem)
        matrix = ConfusionMatrix()

        # positive examples
        join_conditions = self.generate_join_conditions(rule, "pos")
        pos_count = DatabaseHandler.get_joined_tables_count(join_conditions, conn)
        example_count = DatabaseHandler.get_positive_examples_count(rule.action.name, conn)
        matrix.TP = pos_count
        matrix.FN = example_count - pos_count

        join_conditions = self.generate_join_conditions(rule, "neg")
        neg_count = DatabaseHandler.get_joined_tables_count(join_conditions, conn)
        example_count = DatabaseHandler.get_negative_examples_count(rule.action.name, conn)
        matrix.FP = neg_count
        matrix.TN = example_count - neg_count

        return matrix

    def generate_join_conditions(self, rule, example_state):
        join_conditions = []
        prev = example_state + rule.action.name
        for rp in rule.rule_predicates:
            pred_name = convert_state_to_string(rp.state) + rp.predicate.name
            columns1 = []
            columns2 = []
            for bvs in rp.bound_parameters:
                columns1.append(bvs[0])
                columns2.append(bvs[1])
            join_conditions.append((prev, columns1))
            join_conditions.append((pred_name, columns2))
            prev = pred_name

        return join_conditions

    def get_joined_table_command(self, action, rule, state):
        join_conditions = self.generate_join_conditions(rule, state)
        from_clause = DatabaseHandler.generate_join_command(join_conditions)
        return "SELECT DISTINCT {} FROM {}".format(",".join([f"a0.{str(x)}" for x in action.parameters]), from_clause)

    def create_evaluation_tables(self, action, rule, problem, pos_table_name, neg_table_name):
        conn = self.db_handler.get_connection(problem)

        join_conditions = self.generate_join_conditions(rule, "pos")
        DatabaseHandler.save_joined_tables(action, join_conditions, pos_table_name, conn)

        join_conditions = self.generate_join_conditions(rule, "neg")
        DatabaseHandler.save_joined_tables(action, join_conditions, neg_table_name, conn)

    def select_candidate_rules(self, action, column, min_score):
        rows = self.db_handler.select_candidate_rules(action, column, min_score)

        result = [CandidateRule(row[0], row[1], row[2], ConfusionMatrix(row[3], row[4], row[5], row[6])) for row in
                  rows]
        return result

    def evaluate_hypothesis(self, hypothesis, problem, action):
        conn = self.db_handler.get_connection(problem)
        matrix = ConfusionMatrix()
        pos_count = 0
        if hypothesis:
            pos_count = DatabaseHandler.get_hypothesis_join_pos(hypothesis, conn)
        example_count = DatabaseHandler.get_positive_examples_count(action.name, conn)
        matrix.TP = pos_count
        matrix.FN = example_count - pos_count

        neg_count = 0
        if hypothesis:
            neg_count = DatabaseHandler.get_hypothesis_join_neg(hypothesis, conn)
        example_count = DatabaseHandler.get_negative_examples_count(action.name, conn)
        matrix.FP = neg_count
        matrix.TN = example_count - neg_count

        return matrix

    def should_expand(self, matrix):
        if (matrix.FP == 0 and matrix.TP == 0) or (matrix.TN == 0 and matrix.FN == 0):
            return False
        else:
            return True
