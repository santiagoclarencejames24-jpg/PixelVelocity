class car():
    def __init__(self, speed, name, color, boost):
        self.speed = speed
        self.name = name
        self.color = color
        self.boost = boost 
    def __str__(self):
        return f"{self.name} is a {self.color} car with a speed of {self.speed} and a boost of {self.boost}"

def colors():
    red = (255, 0, 0)
    blue = (0, 0, 255)
    black = (0, 0, 0)
    white = (255, 255, 255)
    return red, blue, black, white

