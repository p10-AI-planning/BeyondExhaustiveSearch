import math
import os

import networkx as nx
import matplotlib.pyplot as plt
import numpy

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FLATTEN_FACTOR = 3
OFFSET_FACTOR = 0.5


class POCLGraph:
    def __init__(self, facts, actions, init_node, goal_node):
        self.facts = facts
        self.actions = actions
        self.init_node = init_node
        self.goal_node = goal_node

    def draw_graph(self, title, use_offset=False):
        node_level_dict = {}
        for fact in self.facts:
            if fact.level not in node_level_dict.keys():
                node_level_dict[fact.level] = []
            node_level_dict[fact.level].append(fact)

        for action in self.actions:
            if action.level not in node_level_dict.keys():
                node_level_dict[action.level] = []
            node_level_dict[action.level].append(action)

        keys = list(node_level_dict.keys())
        keys.sort()
        node_level_dict = {i: node_level_dict[i] for i in keys}
        G = nx.DiGraph()

        # add nodes

        G.add_node(str(self.init_node), size=100000, shape='line', pos=(-1, 0))
        G.add_node(str(self.goal_node), size=100000, shape='line', pos=(self.goal_node.level + 1, 0))
        prev_start = 0
        prev_end = 0
        lowest_y = 0
        highest_y = 0
        offset = False
        for level, nodes in node_level_dict.items():
            y_pos = self.find_median_range(prev_start, prev_end, len(nodes))
            prev_start = 0 + y_pos
            for node in nodes:
                y = 0 + y_pos
                if use_offset and offset:
                    y = OFFSET_FACTOR + y_pos
                if hasattr(node, "fact"):
                    G.add_node(str(node), size=100, shape='point', pos=(level, y / FLATTEN_FACTOR))
                if hasattr(node, "action"):
                    G.add_node(str(node), size=300, shape='square', pos=(level, y / FLATTEN_FACTOR))
                prev_end = 0 + y_pos
                if y_pos > highest_y:
                    highest_y = 0 + y_pos
                if y_pos < lowest_y:
                    lowest_y = 0 + y_pos
                y_pos = y_pos + 1
            offset = not offset

        # add edges:
        for node in self.init_node.from_edges:
            G.add_edge(str(self.init_node), str(node))

        for fact in self.facts:
            for node in fact.from_edges:
                G.add_edge(str(fact), str(node))

        for action in self.actions:
            for node in action.from_edges:
                G.add_edge(str(action), str(node))

        node_shapes = nx.get_node_attributes(G, 'shape')
        node_positions = nx.get_node_attributes(G, 'pos')
        node_sizes = nx.get_node_attributes(G, 'size')

        plt.figure(figsize=(self.goal_node.level, highest_y))

        nx.draw_networkx_edges(G, pos=node_positions, arrowsize=5, arrows=True)

        for node, shape in node_shapes.items():
            size = node_sizes[node]
            x, y = node_positions[node]
            if shape == 'point':
                plt.scatter(x, y, s=size, edgecolors="black", c="black", marker='.')
            elif shape == 'square':
                plt.scatter(x, y, s=size, edgecolors="black", c="white", marker='s')
            elif shape == 'line':
                plt.scatter(x, y, s=size, c="black", marker='|')
            else:
                raise ValueError(f"Unrecognized shape: {shape}")

        for node, (x, y) in node_positions.items():
            if x == -1 or x == self.goal_node.level + 1:
                plt.annotate(node, xy=(x, y), xytext=(0, 170), textcoords='offset points', ha='center', fontsize=13)
            else:
                plt.annotate(node, xy=(x, y), xytext=(0, 0), textcoords='offset points', ha='center', fontsize=9,
                             rotation=25)

        plt.title(title)
        plt.xticks(range(0, self.goal_node.level))
        plt.yticks([math.floor(lowest_y / FLATTEN_FACTOR), math.ceil(highest_y / FLATTEN_FACTOR)])
        plt.savefig(os.path.join(ROOT_DIR, "graphs", title))
        plt.axis('off')
        plt.show()

    @staticmethod
    def median_range(start, end):
        length = end - start + 1
        if length % 2 == 0:
            return (start + end) / 2
        else:
            return start + (length - 1) / 2

    @staticmethod
    def find_median_range(n1, n2, n3):
        median_original = POCLGraph.median_range(n1, n2)
        half_length = n3 // 2
        start_range = median_original - math.floor(half_length)
        return int(start_range)
