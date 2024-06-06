class Node:
    def __init__(self, action, feature=None, classification=None, present_child=None, missing_child=None):
        self.feature = feature
        self.present_child = present_child
        self.missing_child = missing_child
        self.classification = classification
        self.query = None
        self.data_handler = None
        self.allowed_operators = None
        self.action = action
        self.missing = False

    def is_leaf(self):
        return self.present_child is None and self.missing_child is None

    def is_class(self):
        return self.classification is not None

    def find_feature(self, target):
        if self.is_leaf():
            return None

        if self.feature == target and (self.present_child is None or self.missing_child is None):
            return self

        if self.present_child is not None:
            present_result = self.present_child.find_feature(target)
            if present_result:
                return present_result

        if self.missing_child is not None:
            missing_result = self.missing_child.find_feature(target)
            if missing_result:
                return missing_result

        return None

    def fill(self, query_dict):
        if self.is_class():
            return

        self.query = query_dict[self.feature]
        if self.missing_child is None or self.present_child is None:
            print("aefae")
        self.present_child.fill(query_dict)
        self.missing_child.fill(query_dict)

    def add_data_handler(self, data_handler):
        if self.is_class():
            return
        self.data_handler = data_handler
        self.present_child.add_data_handler(data_handler)
        self.missing_child.add_data_handler(data_handler)

    def clear_cache(self):
        if not self.is_class():
            self.allowed_operators = None
            self.missing_child.clear_cache()
            self.present_child.clear_cache()
    
    def item_in_description(self, item, desc):
        idx = 0
        for val in desc:
            if str(val[0]).removesuffix("_a") == item:
                return idx
            idx += 1
        return -1

    def evaluate(self, operator):
        if self.is_class():
            return self.classification

        if self.allowed_operators is None:
            (description, rows) = self.data_handler.evaluate_node(self.query)
            self.allowed_operators = []

            for index, row in enumerate(rows):
                self.allowed_operators.append([])
                for item in self.action.parameters:
                    idx = self.item_in_description(item, description)
                    if idx >= 0:
                        self.allowed_operators[index].append(row[idx])
                    else:
                        self.allowed_operators[index].append(-1)

        if not any(self.allowed_operators):
            return self.missing_child.evaluate(operator)

        for op in self.allowed_operators:
            match = True
            for i, item in enumerate(operator):
                if not (item == op[i] or op[i] == -1):
                    match = False
                    break

            if match:
                return self.present_child.evaluate(operator)

        return self.missing_child.evaluate(operator)



