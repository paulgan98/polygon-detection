from tkinter import *
from random import choice
from graph import Graph
import functools
import time

DEMO = 0
WIDTH, HEIGHT = 1500, 800

## DEBUG FUNCTIONS
# function to determine execution time of func
def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        tic = time.perf_counter()
        value = func(*args, **kwargs)
        toc = time.perf_counter()
        elapsed_time = toc - tic
        # print(f"{func.__name__}: {elapsed_time:0.4f} seconds")
        return value
    return wrapper_timer

def printDict(di):
    for k, v in di.items():
        print(k, ':', v)

# generates a random hex color code
def generateColor():
    chars = "ABCDEF0123456789"
    color = "#"
    for _ in range(6):
        color += choice(chars)
    return color

class Point:
    def __init__(self, coord, ind):
        self.ind = ind
        self.coord = coord

class Paint:
    def __init__(self, root):
        self.canvas = Canvas(root, width=WIDTH, height=HEIGHT)
        self.x, self.y = 0, 0
        self.draw = False

        self.canvas.bind("<ButtonPress-1>", self.onButtonDown)

        self.currLineNum = 0 # increment after every line drawn
        self.currPointNum = 0 # increment after every point of intersection is found

        # Stores all lines and the lines they intersect with
        # {lineIndex : [(x0, y0), (x1, y1)], 
        #  lineIndex : [(x2, y2), (x3, y3)]...}
        self.lines = {}

        # Store all line ids in a list
        self.lineIds = []
        
        # Stores all vertices and edges in a dict
        self.graph = {}

        # Stores all points of intersection
        # {l0 : [l1, l2, ... ]}
        self.intersects = {}

        # Maps line intersect coords to pos coords
        self.lineToPosCoords = {}

        # Maps point index to position coordinates
        self.pointToPosCoords = {}

        # Stores all polygons with vertices sorted
        # {(p1,p2,...pn) : color1, (p1,p2,...pn) : color2, ...}
        self.polygons = {}

        self.polygonIds = {}

        self.canvas.pack()

        # self.drawLine([(225, 152), (529, 483)])
        # self.drawLine([(360, 460), (718, 41)])
        # self.drawLine([(184, 154), (726, 140)])
        # self.drawLine([(339, 62), (671, 373)])

        # self.drawLine([(100,200),(100,400)])
        # self.drawLine([(100,200),(100,600)])

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
            # return (round(x), round(y))
            return (x, y)

        # loop through all stored lines, check intersect between line and each line l2 in list
        for lineNum, l2 in self.lines.items():
            if self.hasIntersect(line[0], line[1], l2[0], l2[1]) == False:
                continue
            p = getIntersect(line, l2)
            if p is not None: # if line and l2 intersecting
                self.lineToPosCoords[(lineNum, self.currLineNum)] = p
                self.pointToPosCoords[self.currPointNum] = p

                # update self.intersects dict
                self.intersects.setdefault(lineNum, []).append(Point(p, self.currPointNum))
                self.intersects.setdefault(self.currLineNum, []).append(Point(p, self.currPointNum))
                
                # sort lists in self.intersects
                self.intersects[lineNum] = sorted(self.intersects[lineNum], key=lambda x : x.coord)
                self.intersects[self.currLineNum] = sorted(self.intersects[self.currLineNum], key=lambda x : x.coord)

                self.currPointNum += 1

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
        self.canvas.create_oval(point[0]-r//2, point[1]-r//2, point[0]+r//2, point[1]+r//2,
                                fill="#FF0000", outline="#FF0000")

    # function to find all new polygons since last shape drawn
    def findNewPolygons(self):
        # if graph contains only 1 undirected edge, there are no polygons
        if len(self.graph) <= 2:
            return None

        g = Graph(self.graph)
        regions = g.solve() # list of sublists containing point indices (0 - n)
        
        # fill each new polygon with random color
        for r in regions:
            polygon = [self.pointToPosCoords[p] for p in r]
            if polygon not in self.polygons.values():
                color = generateColor()
                id = self.canvas.create_polygon(polygon, fill=color, outline=color)
                self.polygons[id] = polygon # add new polygon to list

    # remove all current lines, and draw new lines
    def drawLines(self):
        # remove all current lines
        for id in self.lineIds:
            self.canvas.delete(id)
        
        self.lineIds = []
        
        # draw all lines
        for line in self.lines.values():
            id = self.canvas.create_line(line)
            self.lineIds.append(id)
            id = self.canvas.create_line(line)
            self.lineIds.append(id)

    # draw line onto canvas, update lists
    def drawLine(self, line):
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
        self.lines[self.currLineNum] = line

        # increment current line number
        self.currLineNum += 1

        # find all polygons and fill them
        self.findNewPolygons()

        # draw all lines onto canvas
        self.drawLines()

        # draw demo labels
        if DEMO:
            self.drawDemoMarks()

    @timer
    def drawDemoMarks(self):
        # draw edges
        for u in self.graph:
            for v in self.graph[u]:
                # if (u not in self.toExclude) and (v not in self.toExclude):
                self.canvas.create_line((*u.coord, *v.coord), width=1.5, fill="blue", arrow='last')
        # draw points
        for point in self.lineToPosCoords.values():
            self.drawDot(point)
        # draw point numbers
        for point, coord in self.pointToPosCoords.items():
            self.canvas.create_text(coord[0], coord[1] + 14, text=f"{point}")

    # callback for button down
    def onButtonDown(self, event):
        if self.draw:
            self.drawLine([(self.x, self.y), (event.x, event.y)])
            self.draw = False
        else:
            self.x, self.y = event.x, event.y
            self.draw = True

def main():
    root = Tk()
    root.title("Paint Program with Polygon Detection")
    paint = Paint(root)
    root.mainloop()

if __name__ == "__main__":
    main()