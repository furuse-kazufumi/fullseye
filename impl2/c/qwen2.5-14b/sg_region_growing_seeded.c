void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 初期化
    int seed_x = w / 2;
    int seed_y = h / 2;
    double seed_value = in[seed_y * w + seed_x];
    int connectivity = (b > 0.5) ? 8 : 4;

    // マスクの初期化
    int* mask = (int*)malloc(h * w * sizeof(int));
    for (int i = 0; i < h * w; i++) {
        mask[i] = 0;
    }

    // シードのマスク設定
    mask[seed_y * w + seed_x] = 1;

    // シードグローワイング
    int changed = 1;
    while (changed) {
        changed = 0;
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (mask[y * w + x]) {
                    double value = in[y * w + x];
                    int dx[] = {-1, 0, 1, 0};
                    int dy[] = {0, -1, 0, 1};
                    if (connectivity == 8) {
                        dy[4] = -1;
                        dx[4] = -1;
                        dy[5] = -1;
                        dx[5] = 1;
                        dy[6] = 1;
                        dx[6] = 1;
                        dy[7] = 1;
                        dx[7] = -1;
                    }
                    for (int k = 0; k < connectivity; k++) {
                        int nx = x + dx[k];
                        int ny = y + dy[k];
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            double neighbor_value = in[ny * w + nx];
                            if (!mask[ny * w + nx] && fabs(value - neighbor_value) <= a) {
                                mask[ny * w + nx] = 1;
                                changed = 1;
                            }
                        }
                    }
                }
            }
        }
    }

    // マスクを出力にコピー
    for (int i = 0; i < h * w; i++) {
        out[i] = mask[i] ? 1.0 : 0.0;
    }

    // メモリ解放
    free(mask);
}
