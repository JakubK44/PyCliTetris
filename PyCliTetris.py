'''
Tetris in Python running in a command line.
'''

from blessed import Terminal
from keyboard import is_pressed
from random import randrange
from time import sleep, perf_counter

class Vector:
    '''
    Represents a 2D vector starting a origin.
    '''

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def add_xy(self, dx: int, dy: int) -> 'Vector':
        return Vector(self.x + dx, self.y + dy)

    def add_vector(self, vector: 'Vector')  -> 'Vector':
        return self.add_xy(vector.x, vector.y)

    def add_x(self, dx: int) -> 'Vector':
        return self.add_xy(dx, 0)

    def add_y(self, dy: int) -> 'Vector':
        return self.add_xy(0, dy)

    def rotate90(self, anchor: 'Vector') -> 'Vector':
        xRotated  = self.x - anchor.x
        yRotated  = self.y - anchor.y

        xRotated, yRotated = -yRotated, xRotated

        xRotated = xRotated + anchor.x
        yRotated = yRotated + anchor.y

        return Vector(xRotated, yRotated)

    def scale(self, xScale: int, yScale) -> 'Vector':
        x = self.x * xScale
        y = self.y * yScale

        return Vector(x, y)

class Vectors:
    '''
    A collection of vectors. Contains helper methods that allow group manipulation of all contained vectors.
    '''

    def __init__(self, vectors: list[Vector]):
        self.vectors = vectors

    def translate_all(self, translation: Vector):
        new_vectors = []
        for vector in self.vectors:
            new_vectors.append(vector.add_vector(translation))
        self.vectors = new_vectors

    def get_rotated90_around_anchor(self) -> 'Vectors':
        anchor = False
        new_vectors = []
        for vector in self.vectors:
            if not anchor:
                anchor = vector
                new_vectors.append(anchor)
            else:
                rotatedVector = vector.rotate90(anchor)
                new_vectors.append(rotatedVector)

        return Vectors(new_vectors)

class Color:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def shift_to_gray(self):
        avg = int((self.r + self.g + self.b) / 3)
        shift = min(255, avg + 25)
        self.r = int(self.r / 2 + shift / 2)
        self.g = int(self.g / 2 + shift / 2)
        self.b = int(self.b / 2 + shift / 2)

class ColorChar:
    def __init__(self, char, fgColor: Color, bgColor: Color):
        self.char = char
        self.fgColor = fgColor
        self.bgColor = bgColor

    def shift_to_gray(self):
        self.fgColor.shift_to_gray()
        self.bgColor.shift_to_gray()

class GameTimer:
    '''
    Controls the time-base events, like gravity and sleep between frames.
    '''

    def __init__(self, gravityIntervalSeconds: float, sleepDelaySeconds: float):
        self._gravityIntervalSeconds = gravityIntervalSeconds
        self._sleepDelaySeconds = sleepDelaySeconds
        self._then = perf_counter()

    def sleep(self):
        sleep(self._sleepDelaySeconds)

    def should_do_gravity(self) -> bool:
        now = perf_counter()
        if self._then + self._gravityIntervalSeconds < now:
            self._then = now
            return True
        else:
            return False

class Screen:
    '''
    Abstraction of a back-buffered screen that accepts single chars and strings at arbitrary locations.
    '''

    mask = False

    def __init__(self, terminal):
        self._term = terminal;
        self.size = Vector(self._term.width, self._term.height - 1)
        create_screen_buffer = lambda width, height: [[self.mask for x in range(width)] for y in range(height)]
        self._backbuffer = create_screen_buffer(self.size.x, self.size.y)
        print(self._term.clear)

    def set_char(self, location: Vector, char: str):
        self.set_color_char(location, ColorChar(char, Color(255, 255, 255), Color(0, 0, 0)))

    def set_color_char(self, location: Vector, color_char: ColorChar):
        self._backbuffer[location.y][location.x] = color_char

    def set_string(self, location: Vector, string: str):
        for index, char in enumerate(string):
            self.set_char(location.add_x(index), char)

    def draw(self):
        print(self._term.home, end = '')
        for line in self._backbuffer:
            for colorChar in line:
                if (colorChar):
                    print(self._term.color_rgb(colorChar.fgColor.r, colorChar.fgColor.g, colorChar.fgColor.b), end = '')
                    print(self._term.on_color_rgb(colorChar.bgColor.r, colorChar.bgColor.g, colorChar.bgColor.b), end = '')
                    print(colorChar.char, end = '')
                else:
                    print(self._term.on_black(' '), end = '')
            print('')

    def clear(self):
        for y, line in enumerate(self._backbuffer):
            for x, _ in enumerate(line):
                self._backbuffer[y][x] = self.mask

class ScaledScreenAdapter(Screen):
    '''
    Allows to transparently scale object drawn to the backing screen.
    '''
    def __init__(self, screen: Screen, xScale: int, yScale: int):
        self._screen = screen
        self._xScale = xScale
        self._yScale = yScale

    def set_color_char(self, location: Vector, color_char: ColorChar):
        scaledLocation = location.scale(self._xScale, self._yScale)
        self._screen.set_color_char(scaledLocation, color_char)

        for x in range(1, self._xScale):
            self._screen.set_color_char(scaledLocation.add_x(x), color_char)

        for y in range(1, self._yScale):
            self._screen.set_color_char(scaledLocation.add_y(y), color_char)

    def draw(self):
        self._screen.draw()

    def clear(self):
        self._screen.clear()

class InputController:
    def __init__(self):
        self._keys = {
            "left": 0,
            "right": 0,
            "up": 0,
            "down": 0
        }

    def update(self):
        for key in self._keys:
            if is_pressed(key) and self._keys[key] == 0:
                self._keys[key] = 1

        for key in self._keys:
            if (not is_pressed(key)) and self._keys[key] == 2:
                self._keys[key] = 0

    def take_dx(self) -> int:
        dx = 0

        if self._keys["left"] == 1:
            dx -= 1
            self._keys["left"] = 2

        if self._keys["right"] == 1:
            dx += 1
            self._keys["right"] = 2

        return dx

    def take_up(self) -> bool:
        if self._keys["up"] == 1:
            self._keys["up"] = 2
            return True

        return False

    def take_down(self) -> bool:
        if self._keys["down"] == 1:
            self._keys["down"] = 2
            return True

        return False

class Score:
    def __init__(self, screen: Screen):
        self._value = 0
        self._screen = screen

    def draw(self):
        self._screen.set_string(Vector(5, 3), f"Score: {self._value}")

    def add(self, lines: int):
        if lines == 4:
            self._value += 800
        elif lines == 3:
            self._value += 500
        elif lines == 2:
            self._value += 300
        elif lines == 1:
            self._value += 100
        elif lines == 0:
            pass
        else:
            raise ValueError("0 to 4 lines are only accepted values")

class Playfield:
    '''
    The matrix that represents the playable portion of the game. Includes methods related to drawing self and arrays of vectors onto self (e.g. tetrominos)
    '''

    upperLeftCornerColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 255, 0))
    upperRightCornerColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 255, 0))
    lowerLeftCornerColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 255, 0))
    lowerRightCornerColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 255, 0))
    horizontalEdgeColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 255, 0))
    verticalEdgeColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 255, 0))
    playfieldContentColorChar = ColorChar(' ', Color(0, 0, 0), Color(0, 0, 255))

    def __init__(self, screen: Screen, score: Score, location: Vector, size: Vector):
        self._screen = screen
        self._location = location
        self._score = score
        self.size = size
        self.playfieldContent = (lambda width, height: [[False for x in range(width)] for y in range(height)])(self.size.x, self.size.y)
        self.topped_out = False

    def draw(self):
        self._screen.set_color_char(self._location, self.upperLeftCornerColorChar)

        for top_edge_char_index in range(1, self.size.x + 1):
            self._screen.set_color_char(self._location.add_x(top_edge_char_index), self.horizontalEdgeColorChar)

        self._screen.set_color_char(self._location.add_x(self.size.x + 1), self.upperRightCornerColorChar)

        for row in range(1, self.size.y + 1):
            self._screen.set_color_char(self._location.add_y(row), self.verticalEdgeColorChar)
            self._screen.set_color_char(self._location.add_xy(self.size.x + 1, row), self.verticalEdgeColorChar)

        self._screen.set_color_char(self._location.add_y(self.size.y + 1), self.lowerLeftCornerColorChar)

        for bottom_edge_char_index in range(1, self.size.x + 1):
            self._screen.set_color_char(self._location.add_xy(bottom_edge_char_index, self.size.y + 1), self.horizontalEdgeColorChar)

        self._screen.set_color_char(self._location.add_vector(self.size).add_xy(1, 1), self.lowerRightCornerColorChar)

        for y, row in enumerate(self.playfieldContent):
            for x, cell in enumerate(row):
                if cell:
                    self.draw_vector(Vector(x, y), cell)

    def draw_vector(self, vector: Vector, colorChar: ColorChar):
        self._screen.set_color_char(self._location.add_vector(vector).add_xy(1, 1), colorChar)

    def draw_vectors(self, vectors: list[Vector], colorChar: ColorChar):
        for vector in vectors:
            self.draw_vector(vector, colorChar)

    def land(self, vectors: list[Vector], colorChar: ColorChar):
        colorChar.shift_to_gray()
        rowsToScan = []
        for vector in vectors:
            self.playfieldContent[vector.y][vector.x] = colorChar
            if not (vector.y in rowsToScan):
                rowsToScan.append(vector.y)

        rowsToScan.sort()
        rowsToRemove = []
        for rowToScan in rowsToScan:
            hitCount = 0
            for cell in self.playfieldContent[rowToScan]:
                if cell:
                    hitCount += 1

            if (hitCount >= self.size.x):
                rowsToRemove.append(rowToScan)

        emptyRowGenerator = lambda: [False for x in range(self.size.x)]
        for rowToRemove in rowsToRemove[::-1]:
            self.playfieldContent.pop(rowToRemove)

        for rowToRemove in rowsToRemove:
            self.playfieldContent.insert(0, emptyRowGenerator())

        for topRowCell in self.playfieldContent[0]:
            if topRowCell:
                self.topped_out = True

        self._score.add(len(rowsToRemove))

    def floor(self, x: int) -> int:
        for y, _ in enumerate(self.playfieldContent):
            if self.playfieldContent[y][x]:
                return y

        return self.size.y

class Tetromino:
    '''
    Base class for all the tetrominos (pieces).
    '''

    def __init__(self, playfield: Playfield):
        self._position = Vectors([])
        self._playfield = playfield
        self.landed = False

    def process(self, should_do_gravity: bool, inputController: InputController):
        if self.landed:
            return

        self._move_horizontally(inputController.take_dx())

        if inputController.take_up():
            self._rotate()

        if inputController.take_down():
            self._drop()
            return

        if should_do_gravity:
            self._do_gravity()

    def _move_horizontally(self, dx: int):
        for block in self._position.vectors:
            xNew = block.x + dx
            if (xNew >= self._playfield.size.x) or (xNew < 0) or (self._playfield.playfieldContent[block.y][xNew]):
                return

        self._position.translate_all(Vector(dx, 0))

    def _rotate(self):
        rotated = self._position.get_rotated90_around_anchor()
        for block in rotated.vectors:
            if (block.x >= self._playfield.size.x) or (block.x < 0) or (self._playfield.playfieldContent[block.y][block.x]):
                return

        self._position = rotated

    def _drop(self):
        while not self.landed:
            self._do_gravity()

    def _do_gravity(self):
        if self.landed:
            return

        for block in self._position.vectors:
            if (block.y + 1 >= self._playfield.size.y) or self._playfield.playfieldContent[block.y + 1][block.x]:
                self.landed = True
                self._playfield.land(self._position.vectors, self.color_char())
                return

        self._position.translate_all(Vector(0, 1))

    def draw(self):
        if self.landed:
            return

        self._playfield.draw_vectors(self._position.vectors, self.color_char())

    def color_char(self):
        return ColorChar(' ', Color(0, 0, 0), Color(255, 0, 0))

class Tetromino_I(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 2)
        self._position = Vectors([anchor, anchor.add_xy(0, -2), anchor.add_xy(0, -1), anchor.add_xy(0, 1)])

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(173, 216, 230)) # light blue

class Tetromino_J(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 0)
        self._position = Vectors([anchor, anchor.add_xy(-1, 0), anchor.add_xy(1, 0), anchor.add_xy(1, 1)])

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(0, 0, 139)) # dark blue

class Tetromino_L(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 1)
        self._position = Vectors([anchor, anchor.add_xy(-1, 0), anchor.add_xy(1, 0), anchor.add_xy(1, -1)])

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(255, 165, 0)) # orange

class Tetromino_O(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 0)
        self._position = Vectors([anchor, anchor.add_xy(1, 0), anchor.add_xy(0, 1), anchor.add_xy(1, 1)])

    def _rotate(self):
        pass # this one does not rotate

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(255, 255, 0)) # yellow

class Tetromino_S(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 0)
        self._position = Vectors([anchor, anchor.add_xy(-1, 1), anchor.add_xy(0, 1), anchor.add_xy(1, 0)])

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(0, 173, 67)) # green

class Tetromino_Z(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 0)
        self._position = Vectors([anchor, anchor.add_xy(-1, 0), anchor.add_xy(0, 1), anchor.add_xy(1, 1)])

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(255, 0, 0)) # red

class Tetromino_T(Tetromino):
    def __init__(self, playfield: Playfield):
        Tetromino.__init__(self, playfield)
        anchor = Vector(int(playfield.size.x / 2), 1)
        self._position = Vectors([anchor, anchor.add_xy(-1, 0), anchor.add_xy(0, -1), anchor.add_xy(1, 0)])

    def color_char(self) -> ColorChar:
        return ColorChar(' ', Color(255, 255, 255), Color(208, 65, 126)) # magenta

class SevenBag:
        def __init__(self, playfield: Playfield):
            self._playfield = playfield
            self._new_bag()

        def _new_bag(self):
            self._bag = [Tetromino_I(self._playfield), Tetromino_J(self._playfield), Tetromino_L(self._playfield),
                         Tetromino_O(self._playfield), Tetromino_S(self._playfield), Tetromino_Z(self._playfield),
                         Tetromino_T(self._playfield)]

        def get_tetromino(self) -> Tetromino:
            tetrominoIndex = randrange(0, len(self._bag))
            tetromino = self._bag.pop(tetrominoIndex)

            if not self._bag:
                self._new_bag()

            return tetromino

def main():
    term = Terminal()

    if term.width < 80 or term.height < 24:
        print("Terminal size too small; minimum 80x24 required. Exiting")
        return

    with term.hidden_cursor():
        gameTimer = GameTimer(.5, .0)
        inputController = InputController()
        screen = Screen(term)
        score = Score(screen)
        playfield = Playfield(ScaledScreenAdapter(screen, 2, 1), score, Vector(20, 0), Vector(10, 20))
        bag = SevenBag(playfield)
        tetromino = bag.get_tetromino()

        while True:
            # drawing
            screen.clear()
            playfield.draw()
            tetromino.draw()
            score.draw()
            screen.draw()

            # processing
            tetromino.process(gameTimer.should_do_gravity(), inputController)
            if (tetromino.landed):
                if playfield.topped_out:
                    break
                else:
                    tetromino = bag.get_tetromino()

            # input
            inputController.update()

            # all done, sleep to slow down
            gameTimer.sleep()

        gameOver = "Game Over"
        screen.set_string(Vector(int((screen.size.x - len(gameOver)) / 2), int(screen.size.y / 2) - 1), gameOver)
        screen.draw()
        while True:
            pass

if __name__ == '__main__':
    main()
