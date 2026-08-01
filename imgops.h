/* imgevolve C runtime — image ops on a float* buffer (HxW, row-major, values in [0,1]).
 * The subset the codegen currently targets for the C backend. All ops operate
 * in place. Boundary handling mirrors scipy's 'reflect' where it matters.
 */
#ifndef IMGOPS_H
#define IMGOPS_H

void gaussian(float* buf, int w, int h, float sigma);
void box(float* buf, int w, int h, int k);
void gamma_op(float* buf, int w, int h, float g);
void threshold(float* buf, int w, int h, float t);
void sharpen(float* buf, int w, int h, float amount, float sigma);
void sobel_mag(float* buf, int w, int h);

#endif /* IMGOPS_H */
