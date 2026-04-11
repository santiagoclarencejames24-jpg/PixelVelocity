class car():
    def __init__(self, speed, name, color, boost):
        self.speed = speed
        self.name = name
        self.color = color
        self.boost = boost 
    def accelerate(self):
        self.speed += self.boost

