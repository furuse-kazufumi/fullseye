#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理: 端画素を重複させて折り返す
    // これは仕様書で指定されている方法であり、端の値を計算するための補間や推定は行わない。
    // 画像の端を処理するための補助関数
    double get_pixel(const double* img, int h, int w, int y, int x) {
        if (y < 0) y = -y - 1;
        if (y >= h) y = 2 * h - y - 2;
        if (x < 0) x = -x - 1;
        if (x >= w) x = 2 * w - x - 2;
        return img[y * w + x];
    }

    // 高周波成分を計算するための補助関数
    double high_pass(const double* img, int h, int w, int y, int x) {
        double center = get_pixel(img, h, w, y, x);
        double sum = 0.0;
        int count = 0;
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                if (dy == 0 && dx == 0) continue;
                sum += get_pixel(img, h, w, y + dy, x + dx);
                count++;
            }
        }
        return center - sum / count;
    }

    // ガウシアンぼかしを計算するための補助関数
    double gaussian_blur(const double* img, int h, int w, int y, int x) {
        double sum = 0.0;
        int count = 0;
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                sum += get_pixel(img, h, w, y + dy, x + dx);
                count++;
            }
        }
        return sum / count;
    }

    // 迭代回数と各回の量を計算
    int n = 1 + (int)round(a * 5);
    double amt = 0.4 + b;

    // 出力画像を初期化
    for (int i = 0; i < h * w; i++) {
        out[i] = in[i];
    }

    // 迭代処理
    for (int i = 0; i < n; i++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double high = high_pass(out, h, w, y, x);
                double blur = gaussian_blur(out, h, w, y, x);
                temp[y * w + x] = out[y * w + x] + amt * (high - blur);
            }
        }
        // 一時的な画像を出力画像にコピー
        for (int i = 0; i < h * w; i++) {
            out[i] = temp[i];
        }
        free(temp);
    }
}
