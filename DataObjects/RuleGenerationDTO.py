class RuleGenerationDTO:
    def __init__(self, rule_generator, tree_builder, murtree_input_generator, rules, rule_count, discarded_rule_count, total_time, rule_gen_time):
        self.rule_generator = rule_generator
        self.tree_builder = tree_builder
        self.murtree_input_generator = murtree_input_generator
        self.rules = rules
        self.rule_count = rule_count
        self.discarded_rule_count = discarded_rule_count
        self.total_time = total_time
        self.rule_gen_time = rule_gen_time