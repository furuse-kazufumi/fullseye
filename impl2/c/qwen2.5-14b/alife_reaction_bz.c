void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int thr = 1 + (int)(3 * a); // 閾値
    const int step_count = 1 + (int)(20 * b); // ステップ数
    const int state_rest = 0; // 休息状態
    const int state_excited = 1; // 兴奮状態
    const int state_refractory = 2; // 休息不能状態

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int state = (int)(in[y * w + x] * 3); // 初期状態の設定
            out[y * w + x] = state / 2.0; // 出力画像の初期化
        }
    }

    // ステップ数分繰り返す
    for (int step = 0; step < step_count; step++) {
        double* temp = (double*)malloc(h * w * sizeof(double)); // 一時的な状態を保存する配列
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int excited_neighbours = 0;
                // 8近傍のセルをチェック
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dx == 0 && dy == 0) continue; // 自分自身は除く
                        int ny = (y + dy + h) % h; // 周期的境界条件
                        int nx = (x + dx + w) % w;
                        if (out[ny * w + nx] == state_excited) {
                            excited_neighbours++;
                        }
                    }
                }
                // 状態の更新
                if (out[y * w + x] == state_excited) {
                    temp[y * w + x] = state_refractory;
                } else if (out[y * w + x] == state_refractory) {
                    temp[y * w + x] = state_rest;
                } else if (excited_neighbours >= thr) {
                    temp[y * w + x] = state_excited;
                } else {
                    temp[y * w + x] = out[y * w + x];
                }
            }
        }
        // 一時的な状態を出力画像にコピー
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] = temp[y * w + x];
            }
        }
        free(temp); // 一時的な状態を保存する配列の解放
    }
}
