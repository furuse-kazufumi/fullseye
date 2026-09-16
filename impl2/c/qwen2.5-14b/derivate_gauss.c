#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理: 入力画像の端を重複させて折り返す
    // この実装では、ガウスフィルタの適用範囲を考慮して、適切な境界を確保する。
    // ガウスフィルタのシグマは a によって制御され、フィルタのサイズはシグマの 3 倍程度と仮定する。
    int filter_size = (int)(3 * a * 3.0 + 0.5); // 3σの近似
    int pad_h = filter_size, pad_w = filter_size;
    int padded_h = h + 2 * pad_h, padded_w = w + 2 * pad_w;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) {
        return; // メモリ確保失敗
    }

    // 入力画像をパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + pad_h) * padded_w + (x + pad_w)] = in[y * w + x];
        }
    }

    // 端の処理: 入力画像の端を重複させて折り返す
    for (int y = 0; y < pad_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            padded_in[y * padded_w + x] = padded_in[(2 * pad_h - y) * padded_w + x];
            padded_in[(padded_h - y - 1) * padded_w + x] = padded_in[(padded_h - 2 * pad_h + y) * padded_w + x];
        }
    }
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < pad_w; x++) {
            padded_in[y * padded_w + x] = padded_in[y * padded_w + (2 * pad_w - x)];
            padded_in[y * padded_w + (padded_w - x - 1)] = padded_in[y * padded_w + (padded_w - 2 * pad_w + x)];
        }
    }

    // ガウスフィルタの生成
    double sigma = a * 1.5 + 0.5; // a は 0.5 から 1.0 の範囲で、σは 0.5 から 3.0 の範囲
    double sum = 0.0;
    int filter_half_size = filter_size / 2;
    double* filter = (double*)malloc((filter_size + 1) * sizeof(double));
    if (filter == NULL) {
        free(padded_in);
        return; // メモリ確保失敗
    }
    for (int i = -filter_half_size; i <= filter_half_size; i++) {
        filter[i + filter_half_size] = exp(-0.5 * (i * i) / (sigma * sigma));
        sum += filter[i + filter_half_size];
    }
    for (int i = -filter_half_size; i <= filter_half_size; i++) {
        filter[i + filter_half_size] /= sum;
    }

    // ガウスフィルタの適用
    double* dx = (double*)malloc(h * w * sizeof(double));
    double* dy = (double*)malloc(h * w * sizeof(double));
    if (dx == NULL || dy == NULL) {
        free(padded_in);
        free(filter);
        return; // メモリ確保失敗
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum_x = 0.0, sum_y = 0.0;
            for (int i = -filter_half_size; i <= filter_half_size; i++) {
                sum_x += filter[i + filter_half_size] * padded_in[(y + i + pad_h) * padded_w + (x + pad_w)];
                sum_y += filter[i + filter_half_size] * padded_in[(y + pad_h) * padded_w + (x + i + pad_w)];
            }
            dx[y * w + x] = sum_x;
            dy[y * w + x] = sum_y;
        }
    }

    // 勾配強度の計算
    double max_val = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double gradient = hypot(dx[y * w + x], dy[y * w + x]);
            out[y * w + x] = gradient;
            if (gradient > max_val) {
                max_val = gradient;
            }
        }
    }

    // 正規化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] /= max_val;
        }
    }

    // メモリ解放
    free(padded_in);
    free(filter);
    free(dx);
    free(dy);
}
