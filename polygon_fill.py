from tkinter import *
from graph import Graph
import functools
import time
import random

# set to 1 to see edge and point labels
# self.demo = 0

TIME = 0

WIDTH, HEIGHT = 1300, 700

## DEBUG FUNCTIONS
# function to determine execution time of func
def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        tic = time.perf_counter()
        value = func(*args, **kwargs)
        toc = time.perf_counter()
        elapsed_time = toc - tic
        if TIME:
            print(f"{func.__name__}: {elapsed_time:0.4f} seconds")
        return value
    return wrapper_timer

def printDict(di):
    for k, v in di.items():
        print(k, ':', v)

# generates a random color
def generateColor():
    rand = lambda: random.randint(50, 200)
    return '#%02X%02X%02X' % (rand(), rand(), rand())

class Point:
    def __init__(self, coord, ind):
        self.ind = ind
        self.coord = coord

class Paint:
    def __init__(self, root):
        self.canvas = Canvas(root, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        # variables needed for drawing
        self.x, self.y = None, None
        self.draw = False
        self.guideLine = None

        # store all demo label ids
        self.demoLabels = []
        self.demo = 0

        # event listeners for drawing
        # self.canvas.bind("<ButtonPress-1>", self.onLeftButton)
        # self.canvas.bind("<ButtonPress-2>", self.onRightButton)
        # self.canvas.bind("<Motion>", self.onMouseMove)
        # self.canvas.bind("<space>", self.toggleDemo)
        
        # Below, we store all necessary data
        self.currLineIndex = 0 # increment after every line drawn
        self.currPointIndex = 0 # increment after every point of intersection is found

        # Stores all lines and the lines they intersect with by their index
        # {line0 : [(line1, line2), (line3, line4)... ], ...}
        self.lines = {}

        # Store all line ids in a list. When we need to remove lines, this is useful.
        self.lineIds = []
        
        # An adjacency list to store all vertices and edges of our directed graph
        self.graph = {}

        # Stores all points of intersection
        # {line0 : [P1, P2, ... ]} where P1, P2, etc. are Point objects defined in the Point class
        self.intersects = {}

        # Maps line intersect coords to pos coords
        # {(lineIndex0, lineIndex1) : (x, y)}
        self.lineToPosCoords = {}

        # Maps point index to position coordinates
        self.pointToPosCoords = {}

        # Maps point position coordinates to indices
        self.posCoordsToPoints = {}

        # Stores all polygons and their ids
        # {[p1,p2,...pn] : id, ...}
        self.polygons = {}

        # self.drawLine([(225, 152), (529, 483)])
        # self.drawLine([(360, 460), (718, 41)])
        # self.drawLine([(184, 154), (726, 140)])
        # self.drawLine([(339, 62), (671, 373)])

        # self.drawLine([(100,200),(100,400)])
        # self.drawLine([(100,400),(200,600)])
        # self.drawLine([(200,600),(100,200)])

    # Return true if line segments AB and CD intersect.
    # This will be used in the findIntersects method
    def hasIntersect(self, A, B, C, D):
        def ccw(A,B,C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

    # Every time a line segment is drawn, we will call this function on that line segment
    # For each line that the new line intersects, we will append the intersect coord (x, y) to 
    # the values (lists) of both lines in self.intersects
    # Return all intersects between line and all stored lines as a list of 2D points
    @timer
    def findIntersects(self, line):
        # helper function to find intersection between 2 lines
        def getIntersect(line1, line2):

            xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
            ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

            def det(a, b):
                return a[0] * b[1] - a[1] * b[0]

            div = det(xdiff, ydiff)
            if div == 0:
                return None

            d = (det(*line1), det(*line2))
            x = det(d, xdiff) / div
            y = det(d, ydiff) / div
            return (x, y)

        # loop through all stored lines, check intersect between line and each line l2 in list
        for lineNum, l2 in self.lines.items():
            if self.hasIntersect(line[0], line[1], l2[0], l2[1]) == False:
                continue
            p = getIntersect(line, l2)
            if p is not None: # if line and l2 intersecting
                self.lineToPosCoords[(lineNum, self.currLineIndex)] = p
                self.pointToPosCoords[self.currPointIndex] = p
                self.posCoordsToPoints[p] = self.currPointIndex

                # update self.intersects dict
                self.intersects.setdefault(lineNum, []).append(Point(p, self.currPointIndex))
                self.intersects.setdefault(self.currLineIndex, []).append(Point(p, self.currPointIndex))
                
                # sort lists in self.intersects
                self.intersects[lineNum] = sorted(self.intersects[lineNum], key=lambda x : x.coord)
                self.intersects[self.currLineIndex] = sorted(self.intersects[self.currLineIndex], key=lambda x : x.coord)

                self.currPointIndex += 1

    # Function to update self.graph after new shapes are drawn onto canvas
    @timer
    def updateEdges(self):
        self.graph = {} # clear the graph

        # identify all points that are not involved in a cycle
        self.toExclude = set()
        for points in self.intersects.values():
            if len(points) == 1:
                self.toExclude.add(points[0].ind)

        for _list in self.intersects.values():
            if len(_list) < 2: continue
            for i in range(len(_list)-1):
                u, v = _list[i], _list[i+1]
                if (u.ind not in self.toExclude) and (v.ind not in self.toExclude):
                    self.graph.setdefault(u, []).append(v)

    # draws a red dot at specified point
    def drawDot(self, point):
        r = 6
        id = self.canvas.create_oval(point[0]-r//2, point[1]-r//2, point[0]+r//2, point[1]+r//2,
                                fill="#FF0000", outline="#FF0000")
        return id

    # function to find all new polygons since last shape drawn
    def findNewPolygons(self):
        def printPolygon(p):
            for point in p:
                print(self.posCoordsToPoints[point], end=' ')
            print()

        # if graph contains only 1 undirected edge, there are no polygons
        if len(self.graph) <= 2:
            return None

        g = Graph(self.graph)
        regions = g.solve() # list of sublists containing point indices (0 - n)
        
        polygons = set()

        # for each polygon
        for r in regions:
            # convert point index to position coords
            polygon = [self.pointToPosCoords[p] for p in r] 

            # reorder polygon vertices while preserving edge relationships
            # we want the top-left-most vertex as the first item
            forwardList = polygon + polygon
            left = forwardList.index(min(polygon, key=lambda x: x))
            if forwardList[left][0] > forwardList[left + 1][0]:
                forwardList.reverse() 
                left = forwardList.index(min(polygon, key=lambda x: x))
            polygon = forwardList[left:left+len(polygon)]
            polygons.add(tuple(polygon))

        newPolygons = polygons - set(self.polygons.keys())
        expiredPolygons = set(self.polygons.keys()) - polygons # polygons that have been split into smaller ones

        # # remove all expired polygons
        for polygon in expiredPolygons:
            self.canvas.delete(self.polygons[polygon]) # remove from canvas
            del self.polygons[polygon] # remove from dictionary

        # if polygon is new
        for polygon in newPolygons:
            for curr in self.polygons.keys():
                if set(curr) == set(polygon): continue
            color = generateColor()
            id = self.canvas.create_polygon(polygon, fill=color, outline="black", width=0.5)
            self.polygons[polygon] = id # add new polygon to list

    # redraw all lines
    def drawLines(self):
        # remove all current lines
        for id in self.lineIds:
            self.canvas.delete(id)
        
        self.lineIds = []
        
        # draw all lines
        for line in self.lines.values():
            id = self.canvas.create_line(line, width=0.5)
            self.lineIds.append(id)

    # function to extend line by a factor of d. 
    # this is useful for intersection detection
    def extendLine(self, line, d):
        p1, p2 = line[0], line[1]
        mag = ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2) ** (1/2) # magnitude
        
        # new coords
        x1 = p1[0] - d * (p2[0]-p1[0]) / mag
        y1 = p1[1] - d * (p2[1]-p1[1]) / mag
        x2 = p2[0] + d * (p2[0]-p1[0]) / mag
        y2 = p2[1] + d * (p2[1]-p1[1]) / mag
        
        return [(x1, y1), (x2, y2)]

    # draw line onto canvas, update data
    def drawLine(self, line):
        # increase line length slightly
        line = self.extendLine(line, 3)

        # sort line endpoints
        # if line is already in list, don't do anything
        line = sorted(line)
        if line in self.lines.values():
            print("line already drawn")
            return

        # find intersects between new line and all existing lines
        self.findIntersects(line)

        # update edges
        self.updateEdges()

        # add new line to lines dict
        self.lines[self.currLineIndex] = line

        # increment current line number
        self.currLineIndex += 1

        # find all polygons and fill them
        self.findNewPolygons()

        # draw all lines onto canvas
        self.drawLines()

        if self.demo:
            self.drawDemoLabels()

        print(len(self.polygons), "polygon(s) found")

    @timer
    def drawDemoLabels(self):
        for id in self.demoLabels:
            self.canvas.delete(id)
        self.demoLabels = []

        # draw polygon outlines
        # for polygon in self.polygons.keys():
        #     id = self.drawDot(polygon[0])
        #     self.demoLabels.append(id)
        #     for i in range(1, len(polygon)):
        #         id = self.canvas.create_line((polygon[i-1], polygon[i]), width=2, fill="blue", arrow='last')
        #         self.demoLabels.append(id)
        #         if i != len(polygon) - 1: continue
        #         id = self.canvas.create_line((polygon[i], polygon[0]), width=2, fill="blue", arrow='last')
        #         self.demoLabels.append(id)

        # draw edges
        for u in self.graph:
            for v in self.graph[u]:
                id = self.canvas.create_line((*u.coord, *v.coord), width=2, fill="blue", arrow='last')
                self.demoLabels.append(id)

        # draw point numbers
        for point, coord in self.pointToPosCoords.items():
            id = self.canvas.create_text(coord[0], coord[1] + 14, text=f"{point}")
            self.demoLabels.append(id)

        # draw points
        for point in self.lineToPosCoords.values():
            id = self.drawDot(point)
            self.demoLabels.append(id)

    # callback for left click
    def onLeftButton(self, event):
        if self.draw:
            self.drawLine([(self.x, self.y), (event.x, event.y)])
            self.draw = False
            self.x, self.y = None, None
        else:
            self.x, self.y = event.x, event.y
            self.draw = True

    # callback for right click
    def onRightButton(self, event):
        if self.draw:
            self.canvas.delete(self.guideLine)
            self.draw = False
            self.x, self.y = None, None

    # callback for mouse move
    def onMouseMove(self, event):
        # redraw guideline
        self.canvas.delete(self.guideLine)
        if self.x is not None and self.y is not None:
            self.guideLine = self.canvas.create_line((self.x, self.y, event.x, event.y), fill="red")

    def toggleDemo(self, event):
        if not self.demo:
            self.drawDemoLabels()
            self.demo = 1
        else:
            for id in self.demoLabels:
                self.canvas.delete(id)
            self.demoLabels = []
            self.demo = 0

def main():
    root = Tk()
    root.title("Paint Program with Polygon Detection")
    root.resizable(False, False)
    paint = Paint(root)

    root.bind("<ButtonPress-1>", paint.onLeftButton)
    root.bind("<ButtonPress-2>", paint.onRightButton)
    root.bind("<Motion>", paint.onMouseMove)
    root.bind("<space>", paint.toggleDemo)

    root.mainloop()

if __name__ == "__main__":
    main()