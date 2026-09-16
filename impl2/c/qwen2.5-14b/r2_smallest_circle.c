#include <math.h>
#include <stdlib.h>
#include <string.h>

// Helper function to check if a point is inside a circle
static int point_in_circle(double x, double y, double cx, double cy, double r) {
    return (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r;
}

// Helper function to compute the smallest enclosing circle using Welzl's algorithm
static void welzl_algorithm(const double* points, int n, int* hull, int hull_size, double* circle) {
    if (n == 0 || hull_size == 3) {
        // Base case: compute the circle for the current hull
        double A = points[hull[1]] - points[hull[0]];
        double B = points[hull[2]] - points[hull[0]];
        double C = points[hull[1]] - points[hull[2]];
        double D = A * A + B * B;
        double E = A * C + B * D;
        double F = C * C + D;
        double G = E * E - D * F;
        circle[0] = (E * F - C * D) / G / 2;
        circle[1] = (E * D - A * F) / G / 2;
        circle[2] = sqrt(D + F - 2 * sqrt(G)) / 2;
        return;
    }

    int i, j;
    for (i = 0; i < hull_size; i++) {
        if (points[n] == points[hull[i]]) {
            break;
        }
    }
    if (i == hull_size) {
        hull[hull_size++] = n;
        welzl_algorithm(points, n - 1, hull, hull_size, circle);
        hull_size--;
    } else {
        welzl_algorithm(points, n - 1, hull, hull_size, circle);
    }
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Ensure a and b are within [0, 1]
    a = fmax(0.0, fmin(1.0, a));
    b = fmax(0.0, fmin(1.0, b));

    // Find the convex hull of the region
    int hull[1000]; // Assuming a maximum of 1000 points in the convex hull
    int hull_size = 0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                hull[hull_size++] = y * w + x;
            }
        }
    }

    // Compute the smallest enclosing circle
    double circle[3];
    welzl_algorithm(in, hull_size - 1, hull, 0, circle);

    // Inflate the radius
    double r_draw = (circle[2] + 0.75) * (1 + 0.4 * a);

    // Draw the circle as a mask
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = point_in_circle(x, y, circle[1] / w, circle[0] / h, r_draw) ? 1.0 : 0.0;
        }
    }
}
