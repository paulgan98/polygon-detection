from math import atan2, pi

# Based on an algorithm developed by Fan and Chang (1991)
# Implemented by Paul Gan

class Graph:
    def __init__(self, g):
        self.graph = g # undirected graph of Point objects {Point_0 : [point_1, Point_2...]}
        # sorted by vi as primary key and theta as secondary key
        self.vertexAngles = [] # [((vi, vj), theta), ...]
        self.wedges = []
        self.regions = []

    # find angle of line formed by 2 Point objects with respect to the horizontal
    # P1 will be the point of the angle
    def findAngle(self, P1, P2):
        y = P1.coord[1] - P2.coord[1]
        x = P2.coord[0] - P1.coord[0]
        if y == 0 and x == 0: return 0
        res = atan2(y, x) * 180 / pi
        return res if res >= 0 else (360+res)

    # helper function to get all ind values of Point objs in a wedge
    # returns a tuple (i1, i2, i3)
    def wedgeToIndices(self, wedge):
        return (wedge[0].ind, wedge[1].ind, wedge[2].ind)

    # binary search algorithm for finding next wedge from sorted wedge list
    # using v1 and v2 as primary and secondary search keys
    def searchWedge(self, v1, v2):
        l, r = 0, len(self.wedges)
        while l < r:
            m = (l+r) // 2
            # if middle element is what we are looking for, return the wedge
            if self.wedges[m][0].ind == v1 and self.wedges[m][1].ind == v2:
                return self.wedges[m]
            # else if middle element > v1, shrink right bound
            elif self.wedges[m][0].ind > v1: r = m
            # else if middle element < v1, shrink left bound
            elif self.wedges[m][0].ind < v1: l = m
            # else v1 matches but v2 doesn't, we adjust bound based on v2
            else:
                if self.wedges[m][1].ind > v2: r = m
                else: l = m
        
        # if we reach here -> element not found, return None
        return None

    def buildVertexAngles(self):
        for vi, edges in self.graph.items():
            for vj in edges:
                # Step 1: duplicate each undirected edge to form two directed edges
                e1, e2 = (vi, vj), (vj, vi)

                # Step 2: Complement each directed edge w/ angle theta of (vi, vj) 
                # w/ respect to horizontal line passing through vi. Add to list
                self.vertexAngles.extend([(e1, self.findAngle(e1[0], e1[1])), 
                                          (e2, self.findAngle(e2[0], e2[1]))])

        # Step 3: Sort list ascending by index and theta as primary and secondary keys
        self.vertexAngles = sorted(self.vertexAngles, 
                            key=lambda x: (x[0][0].ind, x[1]))

    def buildWedges(self):
        # Step 4: Combine consecutive entries in each group into a wedge
        firstInd = 0
        for i in range(1, len(self.vertexAngles)):
            if self.vertexAngles[i][0][0].ind == self.vertexAngles[i-1][0][0].ind:
                tup = (self.vertexAngles[i][0][1], self.vertexAngles[i][0][0], self.vertexAngles[i-1][0][1])
                self.wedges.append(tup)

            # last entry in group, add wedge
            if (i+1 >= len(self.vertexAngles)) or (self.vertexAngles[i+1][0][0].ind != self.vertexAngles[i][0][0].ind):
                tup = (self.vertexAngles[firstInd][0][1], self.vertexAngles[i][0][0], self.vertexAngles[i][0][1])
                # tup = (self.vertexAngles[i][0][1], self.vertexAngles[i][0][0], self.vertexAngles[firstInd][0][1])
                self.wedges.append(tup)
                firstInd = i + 1

    # this will return all faces of our planar graph
    def buildRegions(self):
        def findUnused():
            for k, v in self.used.items():
                if v == 0:
                    return k
            return None

        # Step 5: Sort wedge list using vi and vj as primary and secondary key
        self.wedges = sorted(self.wedges, key=lambda x: (x[0].ind, x[1].ind))

        # Step 6: Mark all wedges as unused
        self.used = {w:0 for w in self.wedges}

        # Step 7: Find unused wedge W0 = (v1, v2, v3)
        w0 = findUnused() # initial wedge: w0
        self.used[w0] = 1 # set w0 to used
        ind0 = self.wedgeToIndices(w0)
        nextFirst, nextSecond = ind0[1], ind0[2]
        wedgeList = [ind0]

        # Step 8: Search for next wedge wi = (v2, v3, vn)
        while self.used:
            wi = self.searchWedge(nextFirst, nextSecond) # O(logn) binary search
            self.used[wi] = 1 # set wi to used
            ind = self.wedgeToIndices(wi)
            nextFirst, nextSecond = ind[1], ind[2]
            wedgeList.append(self.wedgeToIndices(wi))

            # keep searching for next wedge until w(i+1) and w(1) are contiguous
            if (nextFirst != ind0[0]) and (nextSecond != ind0[1]): continue
            else: # contiguous region found
                region = [x[1] for x in wedgeList]
                # if region contains no repeating elements
                if len(region) > 2 and len(region) == len(set(region)): 

                    # _ = [print(x) for x in wedgeList]
                    # print()

                    self.regions.append(region) # store region
                
                wedgeList = [] # clear list

                # Back to Step 7: Find next unused wedge
                w0 = findUnused() # initial wedge: w0
                if not w0: break
                self.used[w0] = 1 # set w0 to used
                ind0 = self.wedgeToIndices(w0)
                nextFirst, nextSecond = ind0[1], ind0[2]
                wedgeList.append(ind0)
        
        # remove exterior face from our regions. (remove the longest list)
        toRemove, longest = None, 0
        for r in self.regions:
            if len(r) > longest:
                longest = len(r)
                toRemove = r
        self.regions.remove(toRemove)

    # this function sequentially calls all functions in our pipeline
    def solve(self):
        self.buildVertexAngles()
        self.buildWedges()
        self.buildRegions()
        return self.regions