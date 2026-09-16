#include <stdlib.h>
#include <string.h>

typedef struct {
    double x;
    double y;
} FsPoint;

static int fs_point_compare(const void *pa, const void *pb)
{
    const FsPoint *a = (const FsPoint *)pa;
    const FsPoint *b = (const FsPoint *)pb;

    if (a->x < b->x) return -1;
    if (a->x > b->x) return 1;
    if (a->y < b->y) return -1;
    if (a->y > b->y) return 1;
    return 0;
}

static double fs_cross(FsPoint o, FsPoint a, FsPoint b)
{
    return (a.x - o.x) * (b.y - o.y)
         - (a.y - o.y) * (b.x - o.x);
}

void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    size_t height = (size_t)h;
    size_t width = (size_t)w;
    size_t pixels;
    size_t foreground = 0;
    size_t point_count;
    size_t i, x, y, k;
    FsPoint *points;
    FsPoint *hull;
    size_t hull_count;

    (void)a;
    (void)b;

    if (width != 0 && height > (size_t)-1 / width)
        return;

    pixels = height * width;

    for (i = 0; i < pixels; ++i) {
        if (in[i] != 0.0)
            ++foreground;
    }

    if (foreground == 0) {
        memset(out, 0, pixels * sizeof(*out));
        return;
    }

    if (foreground > (size_t)-1 / (4U * sizeof(*points))) {
        /* Allocation-impossible fallback chosen for unspecified resource failure:
           preserve the input region as a binary output. */
        for (i = 0; i < pixels; ++i)
            out[i] = in[i] != 0.0 ? 1.0 : 0.0;
        return;
    }

    point_count = foreground * 4U;
    points = (FsPoint *)malloc(point_count * sizeof(*points));
    hull = (FsPoint *)malloc((point_count + 1U) * sizeof(*hull));

    if (points == NULL || hull == NULL) {
        free(points);
        free(hull);
        for (i = 0; i < pixels; ++i)
            out[i] = in[i] != 0.0 ? 1.0 : 0.0;
        return;
    }

    /*
     * Pixel geometry choice: each foreground pixel is treated as its closed
     * unit square [x-0.5,x+0.5] x [y-0.5,y+0.5]. Output pixels whose centers
     * lie on or inside the convex hull of those squares are selected.
     */
    k = 0;
    for (y = 0; y < height; ++y) {
        for (x = 0; x < width; ++x) {
            if (in[y * width + x] != 0.0) {
                double xd = (double)x;
                double yd = (double)y;

                points[k++] = (FsPoint){xd - 0.5, yd - 0.5};
                points[k++] = (FsPoint){xd + 0.5, yd - 0.5};
                points[k++] = (FsPoint){xd + 0.5, yd + 0.5};
                points[k++] = (FsPoint){xd - 0.5, yd + 0.5};
            }
        }
    }

    qsort(points, point_count, sizeof(*points), fs_point_compare);

    k = 0;
    for (i = 0; i < point_count; ++i) {
        if (i != 0 &&
            points[i].x == points[i - 1].x &&
            points[i].y == points[i - 1].y)
            continue;

        while (k >= 2 &&
               fs_cross(hull[k - 2], hull[k - 1], points[i]) <= 0.0)
            --k;

        hull[k++] = points[i];
    }

    hull_count = k;
    k = hull_count + 1U;

    for (i = point_count; i-- > 0;) {
        if (i + 1U < point_count &&
            points[i].x == points[i + 1U].x &&
            points[i].y == points[i + 1U].y)
            continue;

        while (k >= hull_count + 2U &&
               fs_cross(hull[k - 2], hull[k - 1], points[i]) <= 0.0)
            --k;

        hull[k++] = points[i];
    }

    hull_count = k > 1U ? k - 1U : k;

    for (y = 0; y < height; ++y) {
        for (x = 0; x < width; ++x) {
            FsPoint p = {(double)x, (double)y};
            int inside = 1;

            for (i = 0; i < hull_count; ++i) {
                FsPoint p0 = hull[i];
                FsPoint p1 = hull[(i + 1U) % hull_count];

                if (fs_cross(p0, p1, p) < 0.0) {
                    inside = 0;
                    break;
                }
            }

            out[y * width + x] = inside ? 1.0 : 0.0;
        }
    }

    free(hull);
    free(points);
}
