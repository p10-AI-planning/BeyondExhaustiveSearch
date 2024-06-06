import glob
import os
import shutil
import sqlite3
from DataObjects.Domain import Domain
from DataObjects.Predicate import Predicate
from DataObjects.Action import Action


class DatabaseHandler:
    def __init__(self, domain, folder_name):
        self.domain = domain
        self.folder_name = folder_name

    def create_problem(self, problem, overwrite_existing=True):
        if not overwrite_existing:
            path = f"./DataHandler/Database/{self.folder_name}"
            if os.path.exists('{}/{}.db'.format(path, problem.name)):
                return
        self.create_database(problem)
        conn = self.get_connection(problem)

        # Init
        for predicate in problem.init:
            self.add_predicate("init", predicate, conn)

        # Goal
        for predicate in problem.goal:
            self.add_predicate("goal", predicate, conn)

        # Actions
        for action, examples in problem.problemExamples.items():
            for p in examples.positives:
                self.add_action("pos", action, p, conn)
            for n in examples.negatives:
                self.add_action("neg", action, n, conn)

        # Litra To Number
        for litra, number in problem.litraToNumber.objStrToInt.items():
            self.add_litra_to_number(litra, number, conn)

        conn.close()

    def add_litra_to_number(self, litra, number, conn):
        c = conn.cursor()
        command = "create table IF NOT EXISTS LitraToNumber (litra TEXT, number INTEGER)"
        c.execute(command)
        command = "insert into LitraToNumber values ('{}', {})".format(litra, number)

        c.execute(command)
        conn.commit()
        c.close()

    def create_operator(self, action, rules, overwrite_existing=False):
        path = f"./DataHandler/Database/{self.folder_name}"

        if not os.path.exists(path):
            os.makedirs(path)
        if overwrite_existing and os.path.exists('{}/{}.db'.format(path, action.name)):
            os.remove('{}/{}.db'.format(path, action.name))
        conn = sqlite3.connect('{}/{}.db'.format(path, action.name))
        c = conn.cursor()
        command = ("create table IF NOT EXISTS rules " +
                   "(rule TEXT, TP INTEGER, FP INTEGER, TN INTEGER, FN INTEGER, " +
                   "accuracy REAL, recall REAL, precision REAL, f1 REAL, pos_table TEXT, neg_table TEXT)")
        c.execute(command)
        for rule in rules:
            command = (f"insert into rules values " +
                       f"('{str(rule[0])}',{rule[1].TP}, {rule[1].FP}, {rule[1].TN}, {rule[1].FN}, " +
                       f"{rule[1].accuracy()}, {rule[1].recall()}, {rule[1].precision()}, {rule[1].f1()}, " +
                       f"'{rule[2]}', '{rule[3]}')")
            c.execute(command)
        conn.commit()
        c.close()
        conn.close()

    def add_action(self, example_state, action, values, conn):
        c = conn.cursor()
        domain_action = self.domain.actions[action]
        if len(domain_action.parameters) > 0:
            command = "create table IF NOT EXISTS {}{} ({})".format(example_state, action.replace("-", "_"),
                                                                    ','.join(
                                                                        [str(x) + ' INTEGER' for x in
                                                                         domain_action.parameters]))
            c.execute(command)
            command = "insert into {}{} values ({})".format(example_state, action.replace("-", "_"),
                                                            ','.join([str(x) for x in values]))
            c.execute(command)
            conn.commit()
            c.close()

    def add_predicate(self, state, predicate, conn):
        c = conn.cursor()
        domain_predicate = self.domain.predicates[predicate.name]
        if len(domain_predicate.parameters) > 0:
            command = "insert into {}{} values ({})".format(state, domain_predicate.name.replace("-", "_"),
                                                            ','.join([str(x) for x in predicate.parameters]))
            c.execute(command)
            conn.commit()
            c.close()

    def create_database(self, problem):
        path = f"./DataHandler/Database/{self.folder_name}"

        if not os.path.exists(path):
            os.makedirs(path)
        if os.path.exists('{}/{}.db'.format(path, problem.name)):
            os.remove('{}/{}.db'.format(path, problem.name))
        conn = sqlite3.connect('{}/{}.db'.format(path, problem.name))
        c = conn.cursor()
        for key, predicate in self.domain.predicates.items():
            # domain_predicate = self.domain.predicates[predicate.name]
            for state in ["init", "goal"]:
                if len(predicate.parameters) > 0:
                    command = "create table IF NOT EXISTS {}{} ({})".format(state, predicate.name.replace("-", "_"),
                                                                            ','.join(
                                                                                [str(x) + ' INTEGER' for x in
                                                                                 predicate.parameters]))
                    c.execute(command)
        for key, action in self.domain.actions.items():
            for state in ["neg", "pos"]:
                if len(action.parameters) > 0:
                    command = "create table IF NOT EXISTS {}{} ({})".format(state, action.name.replace("-", "_"),
                                                                            ','.join(
                                                                                [str(x) + ' INTEGER' for x in
                                                                                 action.parameters]))
                    c.execute(command)

        c.close()
        conn.close()

    def get_connection(self, problem):
        path = f"./DataHandler/Database/{self.folder_name}"
        return sqlite3.connect('{}/{}.db'.format(path, problem.name))

    @staticmethod
    def generate_join_command(join_conditions):

        if len(join_conditions) < 2:
            raise ValueError("At least two tables are required for a JOIN operation.")
        alias_number = 0
        from_clause = join_conditions[0][0] + f" a{alias_number}"  # First table in the list
        for i in range(0, len(join_conditions) - 1, 2):
            table1, columns1 = join_conditions[i]
            table2, columns2 = join_conditions[i + 1]
            t1_alias = f"a{str(alias_number)}"
            t2_alias = f"a{str(alias_number + 1)}"
            alias_number = alias_number + 1

            # Convert columns to a string with "AND" conditions
            condition_string = " AND ".join(
                [f"{t1_alias}.{col1} = {t2_alias}.{col2}" for col1, col2 in zip(columns1, columns2)])

            from_clause += f" JOIN {table2} {t2_alias} ON {condition_string}"

        return from_clause.replace('-', '_')

    @staticmethod
    def get_joined_tables(action, join_conditions, conn):
        from_clause = DatabaseHandler.generate_join_command(join_conditions)
        command = "SELECT {} FROM {}".format(",".join(map(str, action.parameters)), from_clause)
        cur = conn.cursor()
        cur.execute(command)
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def save_joined_tables(action, join_conditions, table_name, conn, ):

        from_clause = DatabaseHandler.generate_join_command(join_conditions)
        command = "DROP TABLE IF EXISTS {}".format(table_name)
        cur = conn.cursor()
        try:
            cur.execute(command)
        except:
            print(command)
            raise

        command = "create table {} ({})".format(table_name, ','.join(
            [str(x) + ' INTEGER' for x in
             action.parameters]))
        try:
            cur.execute(command)
        except:
            print(command)
            raise
        command = "INSERT INTO {} SELECT {} FROM {}".format(table_name, ",".join(map(str, action.parameters)),
                                                            from_clause)
        try:
            cur.execute(command)
        except:
            print(command)
            raise
        conn.commit()
        cur.close()

    @staticmethod
    def get_joined_tables_count(join_conditions, conn):
        from_clause = DatabaseHandler.generate_join_command(join_conditions)
        command = "SELECT COUNT(*) FROM (SELECT DISTINCT a0.* FROM {})".format(from_clause)
        cur = conn.cursor()
        cur.execute(command)
        row = cur.fetchone()
        cur.close()
        return row[0]

    @staticmethod
    def get_positive_examples_count(action, conn):
        command = "SELECT COUNT(*) FROM pos{}".format(action.replace("-", "_"))
        cur = conn.cursor()
        cur.execute(command)
        row = cur.fetchone()
        cur.close()
        return row[0]

    @staticmethod
    def get_negative_examples_count(action, conn):
        command = "SELECT COUNT(*) FROM neg{}".format(action.replace("-", "_"))
        cur = conn.cursor()
        cur.execute(command)
        row = cur.fetchone()
        cur.close()
        return row[0]

    @staticmethod
    def get_count(table_name, conn):
        command = "SELECT COUNT(*) FROM {}".format(table_name)
        cur = conn.cursor()
        cur.execute(command)
        row = cur.fetchone()
        cur.close()
        return row[0]

    def select_candidate_rules(self, action, column, min_score):
        path = f"./DataHandler/Database/{self.folder_name}"
        conn = sqlite3.connect('{}/{}.db'.format(path, action.name))
        command = "SELECT rule, pos_table, neg_table, TP, TN, FP, FN FROM rules WHERE {} >= {}".format(
            column, min_score)
        cur = conn.cursor()
        cur.execute(command)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def create_candidate_rules(self, candidate_rules, action):
        path = f"./DataHandler/Database/{self.folder_name}"
        conn = sqlite3.connect('{}/{}evaluation.db'.format(path, action.name))
        command = ("create table IF NOT EXISTS candidate_rules " +
                   "(rule TEXT, pos_table TEXT, neg_table TEXT, TP INTEGER, TN INTEGER, FP INTEGER, FN INTEGER)")
        cur = conn.cursor()
        cur.execute(command)
        for cr in candidate_rules:
            command = (f"INSERT INTO candidate_rules VALUES('{cr.rule}', '{cr.pos_table}', '{cr.neg_table}', " +
                       f"'{cr.matrix.TP}', '{cr.matrix.TN}', '{cr.matrix.FP}', '{cr.matrix.FN}')")
            cur.execute(command)
            conn.commit()
        cur.close()
        conn.close()

    def get_candidate_rules(self, action, column):
        path = f"./DataHandler/Database/{self.folder_name}"
        conn = sqlite3.connect('{}/{}evaluation.db'.format(path, action.name))
        command = "SELECT * FROM candidate_rules ORDER BY {} ASC".format(column)
        cur = conn.cursor()
        cur.execute(command)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def get_hypothesis_join_pos(rules, conn):
        command = "SELECT COUNT(*) FROM ({}) AS derived".format(" UNION ".join([x.pos_table for x in rules]))
        cur = conn.cursor()
        try:
            cur.execute(command)
        except:
            print("test")
            raise
        row = cur.fetchone()
        cur.close()
        return row[0]

    @staticmethod
    def get_hypothesis_join_neg(rules, conn):
        command = "SELECT COUNT(*) FROM ({}) AS derived".format(" UNION ".join([x.neg_table for x in rules]))
        cur = conn.cursor()
        try:
            cur.execute(command)
        except:
            print("test")
            raise
        row = cur.fetchone()
        cur.close()
        return row[0]

    def create_hypothesis(self, hypothesis, confusion_matrix, action):
        path = f"./DataHandler/Database/{self.folder_name}"
        conn = sqlite3.connect('{}/{}evaluation.db'.format(path, action.name))
        command = "create table IF NOT EXISTS hypothesis (rule TEXT)"
        cur = conn.cursor()
        cur.execute(command)
        command = ("create table IF NOT EXISTS confusion_matrix " +
                   "(TP INTEGER, FP INTEGER, TN INTEGER, FN INTEGER, " +
                   "accuracy REAL, recall REAL, precision REAL, f1 REAL )")
        cur.execute(command)
        for r in hypothesis:
            command = f"INSERT INTO hypothesis VALUES('{r.rule}')"
            cur.execute(command)
        command = (f"INSERT INTO confusion_matrix VALUES" +
                   f"('{confusion_matrix.TP}', '{confusion_matrix.FP}', '{confusion_matrix.TN}', " +
                   f"'{confusion_matrix.FN}', '{confusion_matrix.accuracy()}', '{confusion_matrix.recall()}', " +
                   f"'{confusion_matrix.precision()}', '{confusion_matrix.f1()}')")
        cur.execute(command)
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def delete_database():
        path = './DataHandler/Database'
        if os.path.exists(path):
            shutil.rmtree(path)

    def save_aggregate_hypothesis(self, hypothesis, confusion_matrix):
        path = f"./DataHandler/Database/{self.folder_name}"
        conn = sqlite3.connect('{}/final_evaluation.db'.format(path))
        command = "create table IF NOT EXISTS hypothesis (rule TEXT)"
        cur = conn.cursor()
        cur.execute(command)
        command = ("create table IF NOT EXISTS confusion_matrix " +
                   "(TP INTEGER, FP INTEGER, TN INTEGER, FN INTEGER, " +
                   "accuracy REAL, recall REAL, precision REAL, f1 REAL )")
        cur.execute(command)
        for r in hypothesis:
            command = f"INSERT INTO hypothesis VALUES('{r.rule}')"
            cur.execute(command)

        command = (f"INSERT INTO confusion_matrix VALUES" +
                   f"('{confusion_matrix.TP}', '{confusion_matrix.FP}', '{confusion_matrix.TN}', " +
                   f"'{confusion_matrix.FN}', '{confusion_matrix.accuracy()}', '{confusion_matrix.recall()}', " +
                   f"'{confusion_matrix.precision()}', '{confusion_matrix.f1()}')")
        cur.execute(command)

        conn.commit()
        cur.close()
        conn.close()

    def save_aleph_hypothesis(self, rules, confusion_matrix):
        path = f"./DataHandler/Database/{self.folder_name}"
        if not os.path.exists(path):
            os.makedirs(path)
        conn = sqlite3.connect('{}/{}.db'.format(path, self.domain.name))
        command = "create table IF NOT EXISTS hypothesis (rule TEXT, pos TEXT, neg TEXT)"
        cur = conn.cursor()
        cur.execute(command)
        command = ("create table IF NOT EXISTS confusion_matrix " +
                   "(TP INTEGER, FP INTEGER, TN INTEGER, FN INTEGER, " +
                   "accuracy REAL, recall REAL, precision REAL, f1 REAL )")
        cur = conn.cursor()
        cur.execute(command)
        for r in rules:
            command = f"INSERT INTO hypothesis VALUES('{r.rule}', '{r.pos}', '{r.neg}')"
            cur.execute(command)

        command = (f"INSERT INTO confusion_matrix VALUES" +
                   f"('{confusion_matrix.TP}', '{confusion_matrix.FP}', '{confusion_matrix.TN}', " +
                   f"'{confusion_matrix.FN}', '{confusion_matrix.accuracy()}', '{confusion_matrix.recall()}', " +
                   f"'{confusion_matrix.precision()}', '{confusion_matrix.f1()}')")
        cur.execute(command)
        conn.commit()
        cur.close()
        conn.close()

    def get_aleph_hypothesis(self):
        path = f"./DataHandler/Database/{self.folder_name}"
        conn = sqlite3.connect('{}/{}.db'.format(path, self.domain.name))
        command = "SELECT * FROM hypothesis"
        cur = conn.cursor()
        cur.execute(command)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
