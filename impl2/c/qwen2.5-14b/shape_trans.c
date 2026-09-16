void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。ここでは無視する。
    (void)a;
    (void)b;

    // 凸包を計算するためのワーク領域
    int* work = (int*)malloc(h * w * sizeof(int));
    if (work == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 入力画像をワーク領域にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            work[y * w + x] = (int)(in[y * w + x] + 0.5); // 0.5 で丸める
        }
    }

    // 凸包を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (work[y * w + x] == 1) {
                // 画素が 1 の場合、その位置を凸包に含める
                out[y * w + x] = 1.0;
                // 上下左右の隣接画素もチェック
                if (y > 0 && work[(y - 1) * w + x] == 0) out[(y - 1) * w + x] = 1.0;
                if (y < h - 1 && work[(y + 1) * w + x] == 0) out[(y + 1) * w + x] = 1.0;
                if (x > 0 && work[y * w + x - 1] == 0) out[y * w + x - 1] = 1.0;
                if (x < w - 1 && work[y * w + x + 1] == 0) out[y * w + x + 1] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // ワーク領域の解放
    free(work);
}
