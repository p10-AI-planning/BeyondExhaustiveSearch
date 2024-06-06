class LitraToNumber:
    def __init__(self, defaultLitra = []):
        self.indexCnt = 0
        self.objStrToInt = {"": 0}
        self.objIntToStr = {0: ""}
        self.objStrToInt.clear()
        self.objIntToStr.clear()
        for litra in defaultLitra:
            self.add_litra(litra.lower())
    
    def get_number(self, litra:str):
        return self.objStrToInt[litra.lower()]
    
    def get_litra(self, number:int):
        return self.objIntToStr[number].lower()
    
    def add_litra(self, litra:str):
        litra = litra.lower()
        if litra in self.objStrToInt:
            return self.objStrToInt[litra]
        self.objIntToStr[self.indexCnt] = litra
        self.objStrToInt[litra] = self.indexCnt
        self.indexCnt += 1
        return  self.objStrToInt[litra]