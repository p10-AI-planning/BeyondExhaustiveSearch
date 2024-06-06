class ConfusionMatrix:
    def __init__(self, TP=0, TN=0, FP=0, FN=0):
        self.TP = TP
        self.TN = TN
        self.FP = FP
        self.FN = FN

    def precision(self):
        divisor = self.TP + self.FP
        if divisor == 0:
            return -1
        return self.TP / divisor

    def recall(self):
        divisor = self.TP + self.FN
        if divisor == 0:
            return -1
        return self.TP / divisor

    def accuracy(self):
        divisor = self.TP + self.TN + self.FP + self.FN
        if divisor == 0:
            return -1
        return (self.TP + self.TN) / divisor

    def f1(self):
        divisor = self.precision() + self.recall()
        if divisor == 0:
            return -1
        return 2 * ((self.precision() * self.recall()) / divisor)

    def __add__(self, other):
        result = ConfusionMatrix()
        result.TP = self.TP + other.TP
        result.TN = self.TN + other.TN
        result.FP = self.FP + other.FP
        result.FN = self.FN + other.FN
        return result
