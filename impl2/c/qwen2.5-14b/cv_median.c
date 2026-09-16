void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の画素を複製して埋めるためのパディング
    int padded_h = h + 2;
    int padded_w = w + 2;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) {
        return; // メモリ確保失敗
    }

    // 入力画像をパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }

    // 端の画素を複製
    for (int x = 0; x < padded_w; x++) {
        padded_in[x] = padded_in[x + 1];
        padded_in[(padded_h - 1) * padded_w + x] = padded_in[(padded_h - 2) * padded_w + x];
    }
    for (int y = 0; y < padded_h; y++) {
        padded_in[y * padded_w] = padded_in[y * padded_w + 1];
        padded_in[y * padded_w + (padded_w - 1)] = padded_in[y * padded_w + (padded_w - 2)];
    }

    // メディアンフィルタ適用
    int ksize = 3 + 2 * (int)(a * 3); // カーネルサイズ
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double values[ksize * ksize];
            int index = 0;
            for (int ky = -ksize / 2; ky <= ksize / 2; ky++) {
                for (int kx = -ksize / 2; kx <= ksize / 2; kx++) {
                    values[index++] = padded_in[(y + ky + 1) * padded_w + (x + kx + 1)];
                }
            }
            // メディアン計算
            qsort(values, ksize * ksize, sizeof(double), compare);
            out[y * w + x] = values[ksize * ksize / 2];
        }
    }

    free(padded_in);
}

// qsort の比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a > *(double*)b) - (*(double*)a < *(double*)b);
}
