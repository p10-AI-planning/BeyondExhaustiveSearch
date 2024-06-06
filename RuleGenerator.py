import time
import logging
from collections import deque
from DataObjects.Rule import Rule
from DataObjects.Domain import Domain

logger = logging.getLogger(__name__)

class RuleGenerator:
    def __init__(self, tree_builder):
        self.tb = tree_builder
        self.current_node = self.tb.root
        self.tb.expand_node(self.current_node)
        self.queue = deque(self.current_node.children)

    def next(self):
        node = self.queue.popleft()
        self.current_node = node
        return self.tb.create_rule(self.current_node)

    def expand(self):
        if self.current_node.expandable and not self.current_node.children:
            self.tb.expand_node(self.current_node)
            self.queue.extend(self.current_node.children)
    
    def AnalyzeRule(self, rule : Rule, domain : Domain):
        paramterToLinkDir = {int:int}
        paramterToStr = {int:str}
        listOfLinks = []
        #logger.info(rule)

        for parameter in range(1,len(rule.action.parameters)+1):
            paramterToStr [parameter] = domain.actions[rule.action.name].parameters[parameter-1]
            paramterToLinkDir[parameter] = 0
        
        linkIdx = 1
        for rule_predicate in rule.rule_predicates:
            for parameterIdx in range(0, len(rule_predicate.predicate.parameters)):
                parameter = rule_predicate.predicate.parameters[parameterIdx]
                if(parameter not in paramterToLinkDir):
                    paramterToLinkDir[parameter] = linkIdx
                    paramterToStr[parameter] = domain.predicates[rule_predicate.predicate.name].parameters[parameterIdx]
                else:
                    listOfLinks.append((paramterToLinkDir[parameter],(paramterToStr[parameter],domain.predicates[rule_predicate.predicate.name].parameters[parameterIdx])))
                    rule_predicate.bound_linkings.append(listOfLinks[-1])
                    #logger.info(listOfLinks[-1])
            linkIdx += 1
        
        return listOfLinks
