class CandidateRule:
    def __init__(self, rule, pos_table, neg_table, matrix=None):
        self.rule = rule
        self.pos_table = pos_table
        self.neg_table = neg_table
        self.matrix = matrix

