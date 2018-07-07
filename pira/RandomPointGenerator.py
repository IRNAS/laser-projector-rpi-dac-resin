import matplotlib.pyplot as plt
import csv
import numpy as np
import random
import time

def generate_polygone(points_x, points_y):

    # Define number of angles
    n = len(points_x)
    corner_x = [int(points_x[i]/100) for i in xrange(n)]
    corner_y = [int(points_y[i]/100) for i in xrange(n)]
    contour_x = []
    contour_y = []

    size = int(2**16 / 100)
    M = np.zeros((size,size), dtype=np.int)

    print 'Generating poygone...'
    t = time.time()
    # Generate polygone
    for i in xrange(n):
        if corner_x[i] >= size:
            corner_x[i] = size-1
        if corner_y[i] >= size:
            corner_y[i] = size-1
        # Add corner
        M[int(corner_x[i]), int(corner_y[i])] = 1

        # Add points between previous corner and new one
        # Determine index of previous corner
        if i > 0:
            last_i = i-1
        else:
            last_i = n-1

        # Determine direction
        dx = corner_x[i] - corner_x[last_i]
        dy = corner_y[i] - corner_y[last_i]
        ax = 0 # Leading axis
        if abs(dx) > 0:
            dir = dx/abs(dx) # Direction of leading axes
            coeff = float(dy)/dx # Coefficient between axes
        else:
            dir = 0
            coeff = 0

        if abs(dx) < abs(dy):
            ax = 1
            dir = dy/abs(dy)
            coeff = float(dx)/dy

        # Add all the points between two corners
        if ax == 0:
            for j in xrange(abs(dx)):
                x = int(corner_x[last_i] + (j + 1) * dir)
                y = int(corner_y[last_i] + (j + 1) * dir * coeff)
                M[x][y] = 1
                contour_x.append(x*100)
                contour_y.append(y*100)
        else:
            for j in xrange(abs(dy)):
                x = int(corner_x[last_i] + (j + 1) * dir * coeff)
                y = int(corner_y[last_i] + (j + 1) * dir)
                M[x][y] = 1
                contour_x.append(x*100)
                contour_y.append(y*100)

    # Fill points inside polygon
    # Loop over rows
    for i in xrange(size):
        # Scan all entries
        j = 0
        while j < size - 1:
            # Find edge
            if M[i][j] == 1:
                k = j+1
                # Skip if there are consecutive edge points in a row
                if M[i][k] == 1:
                    j = k
                else:
                    # Locate all points between two edges
                    while M[i][k] == 0:
                        k += 1
                        if k == size -1:
                            if M[i][k] == 0:
                                k = j
                            break
                    # Mark all points between two edges
                    for l in range(j+1,k):
                        M[i][l] = 2

                    if k < size -1:
                        k += 1
                        # Skip all consecutive edge points
                        while M[i][k] == 1:
                            k += 1
                    j = k

            else:
                j += 1

    # Filter values - errors due to convex shapes
    # Loop over columns
    for j in xrange(size):
        # Scan elements in rows
        for i in range(1,size-1):
            # Case 1: Same values on both sides of the edge
            if M[i][j] == 1:
                if M[i-1][j] == M[i+1][j] and not M[i-1][j] == 1:
                    if i-2 >= 0:
                        if not M[i-1][j] == M[i-2][j] and not M[i-2][j] == 1:
                            M[i-1][j] = M[i-2][j]
                    if i+2 < size:
                        if not M[i+1][j] == M[i+2][j] and not M[i+2][j] == 1:
                            M[i+1][j] = M[i+2][j]
            # Case 2: wrong value inside or outside polygon
            else:
                if not M[i-1][j] == M[i][j] and not M[i][j] == M[i+1][j] and not M[i-1][j] == 1 and not M[i+1][j] == 1:
                    if M[i][j] == 2:
                        M[i][j] = 0
                    else:
                        M[i][j] = 2
                elif not M[i][j] == M[i+1][j] and not M[i+1][j] == 1:
                    k = i - 1
                    c0 = 0
                    c2 = 0
                    while k >=0 and not M[k][j] == 1:
                        if M[k][j] == 0:
                            c0 += 1
                        else:
                            c2 += 1
                        k -=1
                    k = i + 1
                    while k < size and not M[k][j] == 1:
                        if M[k][j] == 0:
                            c0 += 1
                        else:
                            c2 += 1
                        k +=1

                    if c0 > c2:
                        M[i][j] = 0
                        M[i+1][j] = 0
                    elif c2 > c0:
                        M[i][j] = 2
                        M[i+1][j] = 2

    # Generate path
    Run = 1
    Point = [corner_x[0], corner_y[0]]
    StartPoint = [corner_x[0], corner_y[0]]
    PX = []
    PY = []

    while Run < 1000:
        # Generate random point
        i = random.randrange(size)
        j = random.randrange(size)

        # Check if selected point is in the active area
        if not M[i][j] == 0:
            # Determine direction
            dx = i - StartPoint[0]
            dy = j - StartPoint[1]
            ax = 0 # Leading axis
            if abs(dx) > 0:
                dir = dx/abs(dx) # Direction of leading axes
                coeff = float(dy)/dx # Coefficient between axes
            else:
                dir = 0
                coeff = 0
            if abs(dx) < abs(dy):
                ax = 1
                dir = dy/abs(dy)
                coeff = float(dx)/dy

            # Add all the points between new point
            move = 1
            k = 0
            if ax == 0:
                while move == 1:
                    new_i = int(StartPoint[0] + (k + 1) * dir)
                    new_j = int(StartPoint[1] + (k + 1) * dir * coeff)
                    k += 1
                    if M[new_i][new_j] == 2:
                        Point = [new_i,new_j]
                        PX.append(Point[0]*100)
                        PY.append(Point[1]*100)
                    elif M[new_i][new_j] == 1:
                        Point = [new_i,new_j]
                        PX.append(Point[0]*100)
                        PY.append(Point[1]*100)
                        move = 0
                    else:
                        move = 0
            else:
                while move == 1:
                    new_i = int(StartPoint[0] + (k + 1) * dir * coeff)
                    new_j = int(StartPoint[1] + (k + 1) * dir)
                    k += 1
                    if M[new_i][new_j] == 2:
                        Point = [new_i,new_j]
                        PX.append(Point[0]*100)
                        PY.append(Point[1]*100)
                    elif M[new_i][new_j] == 1:
                        Point = [new_i,new_j]
                        PX.append(Point[0]*100)
                        PY.append(Point[1]*100)
                        move = 0
                    else:
                        move = 0
            i = Point[0]
            j = Point[1]
            StartPoint = [i,j]
            Run += 1

    with open('path.csv', 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(PX)
        writer.writerow(PY)

    with open('contour.csv', 'w') as csvfile2:
        writer = csv.writer(csvfile2)
        writer.writerow(points_x)
        writer.writerow(points_y)
        writer.writerow(contour_x)
        writer.writerow(contour_y)

    return PX, PY, contour_x, contour_y


