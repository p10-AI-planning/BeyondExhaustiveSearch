from DataObjects.LitraToNumber import LitraToNumber

class Problem:
    def __init__(self, name, init, goal):
        self.name = name
        self.init = init
        self.goal = goal

    def __init__(self):
        self.name: str = ""
        self.problemExamples: dict = {}
        self.litraToNumber: LitraToNumber
        self.init = []
        self.goal = []