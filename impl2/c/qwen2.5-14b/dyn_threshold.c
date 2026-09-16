void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int k = (int)(a * (w < h ? w : h)); // 窓の一辺の長さ
    if (k <= 0) k = 1; // 窓サイズが0以下の場合、最小値1を設定

    // オフセットの計算
    double offset = (b - 0.5) * 0.4;

    // 局所平均の計算としきい値処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            int count = 0;
            // 窓内のピクセルを走査
            for (int dy = -k; dy <= k; ++dy) {
                for (int dx = -k; dx <= k; ++dx) {
                    int nx = x + dx;
                    int ny = y + dy;
                    // 窓内のピクセルが画像内にあるかチェック
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += in[ny * w + nx];
                        ++count;
                    }
                }
            }
            // 局所平均を計算
            double local_mean = sum / count;
            // しきい値を計算
            double threshold = local_mean + offset;
            // しきい値処理
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }
}
