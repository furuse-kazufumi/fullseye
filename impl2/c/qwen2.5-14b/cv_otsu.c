#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像を8ビットに量子化
    unsigned char* img_u8 = (unsigned char*)malloc(h * w * sizeof(unsigned char));
    for (int i = 0; i < h * w; ++i) {
        img_u8[i] = (unsigned char)(255 * in[i]);
    }

    // 大津の二値化法を適用
    int hist[256] = {0};
    for (int i = 0; i < h * w; ++i) {
        hist[img_u8[i]]++;
    }

    int total = h * w;
    int sum = 0;
    int sumB = 0;
    int wB = 0;
    int wF = 0;
    double mB = 0;
    double mF = 0;
    double maxSigma = 0;
    int threshold = 0;

    for (int i = 0; i < 256; ++i) {
        wB += hist[i];
        if (wB == 0) continue;
        sumB += (double)(i * hist[i]);
        mB = (double)sumB / wB;
        wF = total - wB;
        if (wF == 0) break;
        mF = (double)(sum - sumB) / wF;
        double sigma = wB * wF * (mB - mF) * (mB - mF);
        if (sigma > maxSigma) {
            maxSigma = sigma;
            threshold = i;
        }
    }

    // 二値化結果を出力画像に格納
    for (int i = 0; i < h * w; ++i) {
        out[i] = (img_u8[i] > threshold) ? 1.0 : 0.0;
    }

    // メモリを解放
    free(img_u8);
}
