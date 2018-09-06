import copy

from qtpy import QtGui

import labelme.utils


# TODO(unknown):
# - [opt] Store paths instead of creating new ones at each paint.


DEFAULT_LINE_COLOR = QtGui.QColor(0, 255, 0, 128)       #green
DEFAULT_FILL_COLOR = QtGui.QColor(255, 0, 0, 128)       #red
DEFAULT_SELECT_LINE_COLOR = QtGui.QColor(255, 255, 255)     #white
DEFAULT_SELECT_FILL_COLOR = QtGui.QColor(0, 128, 255, 155)  #blue
DEFAULT_VERTEX_FILL_COLOR = QtGui.QColor(0, 255, 0, 255)    #green
DEFAULT_HVERTEX_FILL_COLOR = QtGui.QColor(255, 0, 0)        #red


class Shape(object):

    P_SQUARE, P_ROUND = 0, 1

    MOVE_VERTEX, NEAR_VERTEX = 0, 1

    # The following class variables influence the drawing of all shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8
    scale = 1.0

    #Mod by Minming Qian, add the type to shape, to tell the line
    def __init__(self, label=None, line_color=None, type=None):
        self.label = label
        self.points = []
        self.fill = False
        self.selected = False
        self.type = type
        self.setLineColor()
        self.setFillColor()
    #End mod

        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False

        if line_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.line_color = line_color

    def close(self):
        self._closed = True

    def addPoint(self, point):
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def popPoint(self):
        if self.points:
            return self.points.pop()
        return None

    def insertPoint(self, i, point):
        self.points.insert(i, point)

    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False

    #Add by Minming qian, set the default color for different label
    def onebyte_hash(self, s):
        return (ord(s) - 97) * 10 % 256

    def setLineColor(self):
        if self.label == None:
            self.line_color = DEFAULT_LINE_COLOR
        else:
            r = self.onebyte_hash(self.label[0])
            if len(self.label) > 1:
                g = self.onebyte_hash(self.label[1])
            else:
                g = 128
            b = self.onebyte_hash(self.label[-1])
            self.line_color = QtGui.QColor(r, g, b, 200)

    def setFillColor(self):
        if self.label == None:
            self.fill_color = DEFAULT_FILL_COLOR
        else:
            r = self.onebyte_hash(self.label[-1])
            if len(self.label) > 1:
                g = self.onebyte_hash(self.label[1])
            else:
                g = 128
            b = self.onebyte_hash(self.label[0])
            self.fill_color = QtGui.QColor(r, g, b, 200)
    #End add


    def paint(self, painter):
        #Start Add by Minming Qian
        self.setLineColor()
        self.setFillColor()
        #End add

        if self.points:
            color = self.select_line_color \
                if self.selected else self.line_color
            pen = QtGui.QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            painter.setPen(pen)

            line_path = QtGui.QPainterPath()
            vrtx_path = QtGui.QPainterPath()

            line_path.moveTo(self.points[0])
            # Uncommenting the following line will draw 2 paths
            # for the 1st vertex, and make it non-filled, which
            # may be desirable.
            # self.drawVertex(vrtx_path, 0)


            for i, p in enumerate(self.points):
                line_path.lineTo(p)
                self.drawVertex(vrtx_path, i)
            #Mod by Minming Qian, line should not close, to avoid close for the line
            if self.isClosed() and self.type != "line":
                line_path.lineTo(self.points[0])
            #End mod

            painter.drawPath(line_path)
            painter.drawPath(vrtx_path)
            painter.fillPath(vrtx_path, self.vertex_fill_color)
            if self.fill:
                color = self.select_fill_color \
                    if self.selected else self.fill_color
                painter.fillPath(line_path, color)

    def drawVertex(self, path, i):
        d = self.point_size / self.scale
        shape = self.point_type
        point = self.points[i]
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Shape.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    def nearestVertex(self, point, epsilon):
        min_distance = float('inf')
        min_i = None
        for i, p in enumerate(self.points):
            dist = labelme.utils.distance(p - point)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                min_i = i
        return min_i

    def nearestEdge(self, point, epsilon):
        min_distance = float('inf')
        post_i = None
        for i in range(len(self.points)):
            line = [self.points[i - 1], self.points[i]]
            dist = labelme.utils.distancetoline(point, line)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i

    def containsPoint(self, point):
        return self.makePath().contains(point)

    def makePath(self):
        path = QtGui.QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        self._highlightIndex = None

    def copy(self):
        #Mod by Minming Qian, should be fine with the type,
        shape = Shape(self.label, self.type)
        shape.type = self.type
        #End mod
        shape.points = [copy.deepcopy(p) for p in self.points]
        shape.fill = self.fill
        shape.selected = self.selected
        shape._closed = self._closed
        shape.line_color = copy.deepcopy(self.line_color)
        shape.fill_color = copy.deepcopy(self.fill_color)
        return shape

    # Added by Minming Qian 30-08-2018, check the shape is rectangle or not
    def isRectangle(self):
        if len(self.points) != 4:
            return False

        if self.points[0].y() == self.points[1].y() and \
            self.points[1].x() == self.points[2].x() and \
            self.points[2].y() == self.points[3].y() and \
            self.points[3].x() == self.points[0].x():
            return True

        return False

    def __len__(self):
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value
