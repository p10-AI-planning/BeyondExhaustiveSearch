class POCLNode:
    def __init__(self, level):
        self.level = level
        self.to_edges = []
        self.from_edges = []