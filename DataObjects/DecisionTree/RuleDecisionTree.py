from DataObjects.DecisionTree.Node import Node


class RuleDecisionTree:
    def __init__(self, tree, action):
        self.action = action
        self.root = None
        self.rule_list = []
        self.root = self.build_tree(tree)

    def clear_cache(self):
        self.root.clear_cache()

    def build_tree(self, tree):
        root = None
        if tree.left_child is None and tree.right_child is None:
            root = Node(self.action, classification=tree.label)
        else:
            root = Node(self.action, feature=tree.feature)
            self.rule_list.append(root.feature)
            root.missing_child = self.build_tree(tree.left_child)
            root.present_child = self.build_tree(tree.right_child)

        return root

    def parse_tree(self, lines):
        feature_list = []
        tree = None
        prev_node = None
        current_path = 0
        for line in lines:
            if line == "":
                continue
            parts = line.split('|')
            current_node = FileNotFoundError

            if ':' in line:
                # Leaf node (classification)
                classification = int(parts[-1].strip().split(':')[-1])
                current_node = Node(self.action, classification=classification)
            else:
                # Feature node
                feature_info = parts[-1].strip()
                feature_number = feature_info.split()[1].split('#')[-1]  # Corrected this line
                feature_id = int(feature_number)
                current_node = Node(self.action, feature=feature_id)

                if "missing" in line:
                    current_node.missing = True

            if tree is None:
                tree = current_node
                prev_node = tree

            elif current_node.missing:
                feature_list.append(current_node.feature)
                prev_node = tree.find_feature(current_node.feature)
                current_path = 1

            else:
                if current_path == 0:
                    prev_node.present_child = current_node
                    prev_node = prev_node.present_child
                else:
                    prev_node.missing_child = current_node
                    prev_node = prev_node.missing_child
                current_path = 0

        self.root = tree
        self.rule_list = feature_list

    def fill(self, query_dict):
        self.root.fill(query_dict)

    def add_data_handler(self, data_handler):
        self.root.add_data_handler(data_handler)

    def evaluate(self, operator):
        return self.root.evaluate(operator)

    @staticmethod
    def read_lines(path):
        file = open(path, 'r')
        lines = file.readlines()
        file.close()
        return lines
