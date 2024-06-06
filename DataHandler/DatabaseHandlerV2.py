import os
import shutil
import sqlite3
import logging
from DataObjects.Domain import Domain
from DataObjects.Predicate import Predicate
from DataObjects.Action import Action
from DataObjects.Problem import Problem
from DataObjects.Rule import Rule
from DataObjects.RulePredicate import RulePredicate
from DataObjects.State import State

path = os.path.dirname(__file__)

logger = logging.getLogger(__name__)

class DatabaseHandlerV2:
    def __init__(self, domain: Domain, runInMemory=True, deleteOldDb=False):
        self.db_connection = None
        self.domain = domain
        self.problemIndex = 0
        self.running_in_memory = runInMemory
        self.predicate_to_table_name_init = {"": ""}
        self.predicate_to_table_name_goal = {"": ""}
        self.action_to_table_name = {"" : ""}
        self.predicate_to_table_name_init.clear()
        self.predicate_to_table_name_goal.clear()
        self.action_to_table_name.clear()
        logger.info(f"This is using SQLite version: {sqlite3.version}")
        if not runInMemory:
            logger.info(F"Opening database: db_{domain.name}")
            db_path = os.path.join(path, "Database", f"db_{domain.name}.db")
        else:
            logger.info("Opening database in memory")
            db_path = ":memory:"
        try:
            if not os.path.exists(os.path.join(path, "Database")):
                os.mkdir(os.path.join(path, "Database"))
            if deleteOldDb:
                if os.path.exists(db_path):
                    os.remove(db_path)

            self.db_connection = sqlite3.connect(db_path)
            logger.info(f"Creating {len(domain.predicates)} tables for init and goal state")
            self.create_database_tables()
            logger.info(f"Done creating tables database contains following:")
            cursor = self.db_connection.cursor()
            sql_query = "SELECT name FROM sqlite_master WHERE type='table';"
            cursor.execute(sql_query)
            logger.info(cursor.fetchall())
        except Exception as e:
            logger.info(e)
            raise (e)

    def create_database_tables(self):
        for key, predicate in self.domain.predicates.items():
            for state in ["init", "goal"]:

                tableName = "{}{}_p".format(f"{state}_", predicate.name.replace("-", "_"))

                if len(predicate.parameters) > 0:
                    command = "create table IF NOT EXISTS {} (id INTEGER PRIMARY KEY AUTOINCREMENT, {}, problemNumber INTEGER)".format(
                        tableName,
                        ','.join([f"{str(x)}_p INTEGER" for x in predicate.parameters]))
                else:
                    command = f"create table IF NOT EXISTS {tableName} (id INTEGER PRIMARY KEY AUTOINCREMENT, problemNumber INTEGER)"

                self.db_connection.execute(command)
                if state == "init":
                    self.predicate_to_table_name_init[predicate.name] = tableName
                else:
                    self.predicate_to_table_name_goal[predicate.name] = tableName

        for key, action in self.domain.actions.items():

            tableName = "{}_a".format(action.name.replace("-", "_"))

            if len(action.parameters) > 0:
                command = "create table IF NOT EXISTS {} (id INTEGER PRIMARY KEY AUTOINCREMENT, {}, problemNumber INTEGER, goodOperator INTEGER)".format(
                    tableName,
                    ','.join([f"{str(x)}_a INTEGER" for x in action.parameters]))
            else:
                command = f"create table IF NOT EXISTS {tableName} (id INTEGER PRIMARY KEY AUTOINCREMENT, problemNumber INTEGER, goodOperator INTEGER)"

            self.db_connection.execute(command)
            self.action_to_table_name[action.name] = tableName

            command = f"create table IF NOT EXISTS {tableName}_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, ruleIndex INTEGER,  rule TEXT, queue TEXT)"
            self.db_connection.execute(command)

    def insert_problem(self, problem: Problem):
        for predicate in problem.init:
            command = self.build_predicate_insert_string(self.predicate_to_table_name_init[predicate.name],
                                                         predicate.parameters)
            self.db_connection.execute(command)

        for predicate in problem.goal:
            command = self.build_predicate_insert_string(self.predicate_to_table_name_goal[predicate.name],
                                                         predicate.parameters)
            self.db_connection.execute(command)

        for action in self.domain.actions:
            if action in problem.problemExamples:
                problemEx = problem.problemExamples[action]

                for action_input in problemEx.positives:
                    command = self.build_action_insert_string(action, action_input, 1)
                    self.db_connection.execute(command)

                for action_input in problemEx.negatives:
                    command = self.build_action_insert_string(action, action_input, 0)
                    self.db_connection.execute(command)

        self.db_connection.commit()
        self.problemIndex += 1

    def build_predicate_insert_string(self, tableName: str, parameters: list):
        if (len(parameters) > 0):
            return "INSERT INTO {} VALUES (NULL,{},{}) ".format(tableName,
                                                                ','.join([str(x) for x in parameters]),
                                                                self.problemIndex)
        else:
            return "INSERT INTO {} VALUES (NULL,{}) ".format(tableName, self.problemIndex)

    def build_action_insert_string(self, actionName: str, actionInput: list, goodOperator: int):
        if (len(actionInput) > 0):
            return "INSERT INTO {} VALUES (NULL,{},{},{}) ".format(self.action_to_table_name[actionName],
                                                                   ','.join([str(x) for x in actionInput]),
                                                                   self.problemIndex,
                                                                   goodOperator)
        else:
            return "INSERT INTO {} VALUES (NULL,{},{}) ".format(
                self.action_to_table_name[actionName],
                self.problemIndex,
                goodOperator)

    def fetch_rows_accepted_by_rule(self, rule: Rule, ruleIndex: int):
        command = self.build_rule_to_sql(rule)
        result = self.db_connection.execute(command)
        rows = result.fetchall()
        if self.running_in_memory:
            return rows

        query = command
        command = f"INSERT INTO {self.action_to_table_name[rule.action.name]}_rules VALUES (NULL, ?, ?, ?)"
        self.db_connection.execute(command, (ruleIndex, str(rule), query))
        self.db_connection.commit()

        # if(len(rows) > 0):
        # logger.info(f"Rule accepted: {len(rows)} rows")
        return rows

    def fetch_all_action_id_entries(self, action: Action):
        command = f"SELECT id, goodOperator FROM {self.action_to_table_name[action.name]}"
        result = self.db_connection.execute(command).fetchall()
        return result

    def get_good_operator_count(self, action:Action):
        command = f"SELECT COUNT(*) FROM {self.action_to_table_name[action.name]} WHERE goodOperator = 1"
        result = self.db_connection.execute(command).fetchall()
        return result[0][0]

    def get_bad_operator_count(self, action:Action):
        command = f"SELECT COUNT(*) FROM {self.action_to_table_name[action.name]} WHERE goodOperator = 0"
        result = self.db_connection.execute(command).fetchall()
        return result[0][0]

    def build_rule_to_sql(self, rule: Rule):
        binding_in_use = {}
        aliasIdx = 1
        join_table = self.action_to_table_name[rule.action.name]
        aliasToPred = {}
        selectCommand = "SELECT DISTINCT t0.id,t0.problemNumber,"
        command = f"FROM {join_table} as t0"

        # Create join and alias
        for index in range(0, len(rule.rule_predicates)):
            rPredicate: RulePredicate = rule.rule_predicates[index]
            join_table = self.fetch_table_name(rPredicate.predicate, rPredicate.state)

            # if join_table not in tableToAlias:
            alias = f"t{aliasIdx}"
            aliasToPred[aliasIdx] = rPredicate
            command += f" INNER JOIN {join_table} AS {alias}"
            aliasIdx += 1

        # Create ON conditions
        command += " ON"
        for index in range(1, len(aliasToPred) + 1):
            command += f" t{index - 1}.problemNumber = t{index}.problemNumber AND"

        for key, rPredicate in aliasToPred.items():
            rulePredAlias = f"t{key}"
            for linking in rPredicate.bound_linkings:
                if linking[0] == 0:
                    if linking[1][0] not in binding_in_use.keys():
                        selectCommand += f"t0.{linking[1][0]}_a,"  # as {linking[1][0]},"
                        binding_in_use[linking[1][0]] = f"{rulePredAlias}.{linking[1][1]}_p"
                        command += f" t0.{linking[1][0]}_a = {rulePredAlias}.{linking[1][1]}_p"
                        command += " AND"
                    else:
                        command += f" {binding_in_use[linking[1][0]]} = {rulePredAlias}.{linking[1][1]}_p"
                        command += " AND"
                else:
                    bindRulePredAlias = f"t{linking[0]}"
                    command += f" {bindRulePredAlias}.{linking[1][0]}_p = {rulePredAlias}.{linking[1][1]}_p"
                    command += " AND"

        select = selectCommand.removesuffix(",")
        command = command.removesuffix(" AND")
        command = command.removesuffix(" ON")
        final_command = select + " " + command

        return final_command

    def fetch_table_name(self, predicate: Predicate, state: State):
        if state == State.GOAL:
            return self.predicate_to_table_name_goal[predicate.name]
        elif state == State.INIT:
            return self.predicate_to_table_name_init[predicate.name]
        else:
            raise ("Unkowned state in rule predicate!")

    def build_rules_to_sql_schema(self, rule_list):
        sql_dir = {}
        for pair in rule_list:
            dict_key: int = pair[0]
            rule: Rule = pair[1]
            aliasToPred = {}
            binding_in_use = {}
            aliasIdx = 1
            if len(rule.rule_predicates) > 0:
                rPredicate: RulePredicate = rule.rule_predicates[0]
                command = ""
                selectCommand = "SELECT DISTINCT "
                select_table = self.fetch_table_name(rPredicate.predicate, rPredicate.state)
                command = f"FROM {select_table} as t0"
                aliasToPred[0] = rPredicate

                # Create join and alias
                for index in range(1, len(rule.rule_predicates)):
                    rPredicate: RulePredicate = rule.rule_predicates[index]
                    join_table = self.fetch_table_name(rPredicate.predicate, rPredicate.state)

                    # if join_table not in tableToAlias:
                    alias = f"t{aliasIdx}"
                    aliasToPred[aliasIdx] = rPredicate
                    command += f" INNER JOIN {join_table} AS {alias}"
                    aliasIdx += 1

                # Create ON conditions
                if len(rule.rule_predicates) > 1:
                    command += " ON"

                for key, rPredicate in aliasToPred.items():
                    rulePredAlias = f"t{key}"
                    for linking in rPredicate.bound_linkings:
                        if linking[0] == 0:
                            if linking[1][0] not in binding_in_use.keys():
                                selectCommand += f"{rulePredAlias}.{linking[1][1]}_p as {linking[1][0]}_a,"
                                binding_in_use[linking[1][0]] = f"{rulePredAlias}.{linking[1][1]}_p"
                            else:
                                command += f" {binding_in_use[linking[1][0]]} = {rulePredAlias}.{linking[1][1]}_p"
                                command += " AND"
                        else:
                            bindRulePredAlias = f"t{linking[0] - 1}"
                            command += f" {bindRulePredAlias}.{linking[1][0]}_p = {rulePredAlias}.{linking[1][1]}_p"
                            command += " AND"

                select = selectCommand.removesuffix(",")
                command = command.removesuffix(" AND")
                command = command.removesuffix(" ON")
                final_command = select + " " + command

                sql_dir[dict_key] = final_command
        return sql_dir

    def evaluate_node(self, query):
        cursor = self.db_connection.execute(query)
        rows = cursor.fetchall()
        return (cursor.description, rows)


    def get_initial_state(self, problem_number, predicate):

        table_name = "init_{}_p".format(predicate.name.replace("-", "_"))
        query = ("SELECT {} from {} where problemNumber = {}"
                 .format(','.join([f"{str(x)}_p" for x in predicate.parameters]), table_name, problem_number))
        cursor = self.db_connection.execute(query)
        rows = cursor.fetchall()
        return rows
        
    def clear_all_tables(self):
        for key, table in self.action_to_table_name.items():
            self.db_connection.execute(f"DELETE FROM {table}")
        for key, table in self.predicate_to_table_name_goal.items():
            self.db_connection.execute(f"DELETE FROM {table}")
        for key, table in self.predicate_to_table_name_init.items():
            self.db_connection.execute(f"DELETE FROM {table}")
        self.db_connection.commit()
