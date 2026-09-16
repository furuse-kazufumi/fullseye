void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double THRESHOLD_HIGH = 0.92;
    const double THRESHOLD_LOW = 0.08;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 欠損領域のマスク作成
    int mask[h * w];
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > THRESHOLD_HIGH || in[y * w + x] < THRESHOLD_LOW) {
                mask[y * w + x] = 1; // 欠損領域
            } else {
                mask[y * w + x] = 0; // 正常領域
            }
        }
    }

    // 欠損領域の修復
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (mask[y * w + x] == 1) {
                // 欠損領域の修復処理をここに実装する
                // ここでは、周囲の画素の平均値で欠損領域を埋める
                double sum = 0.0;
                int count = 0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            sum += in[ny * w + nx];
                            count++;
                        }
                    }
                }
                out[y * w + x] = sum / count;
            }
        }
    }
}
