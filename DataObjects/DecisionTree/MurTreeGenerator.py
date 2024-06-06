#import pymurtree
import numpy
import pickle
from multiprocessing import Process, Queue
from threading import Thread
from pystreed import STreeDClassifier
from DataObjects.DecisionTree.RuleDecisionTree import RuleDecisionTree

#from pystreed import STreeDClassifier


class MurTreeGenerator:
    def __init__(self):
        pass

    @staticmethod
    def generate(mur_tree_input, path, timeout, treeDepth, max_node_count, action):
        que = Queue()
        p = Process(target=MurTreeGenerator.generate3, args=(mur_tree_input, path, timeout, treeDepth, max_node_count, action, que))
        p.start()
        
        #Allow for murtree to timeout and export if needed before killed by process timeout
        p.join(timeout+20)

        if p.exitcode is None or p.exitcode != 0:
            p.kill()
            p.join()
            raise Exception("murtree generation failed")
        
        if not que.empty():
            return que.get()
        
        return None
   
    @staticmethod
    def generate3(mur_tree_input, path, timeout, treeDepth, max_node_count, action, que):
        rule_results = numpy.array(mur_tree_input[0])
        actual = numpy.array(mur_tree_input[1])
        model = STreeDClassifier(max_depth=treeDepth, max_num_nodes=max_node_count, time_limit=timeout, optimization_task="f1-score")
        model.fit(rule_results, actual)
        model.print_tree(path)
        t = model.get_tree()
        rule_tree = RuleDecisionTree(t,action)
        que.put(rule_tree)