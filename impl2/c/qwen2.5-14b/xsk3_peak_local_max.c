void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int min_distance = 2 + (int)(a * 8); // 最小距離の計算
    const int half_distance = min_distance / 2; // 半分の距離

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 局所極大点の検出
    for (int y = half_distance; y < h - half_distance; ++y) {
        for (int x = half_distance; x < w - half_distance; ++x) {
            double center = in[y * w + x];
            int flag = 1;
            for (int dy = -half_distance; dy <= half_distance; ++dy) {
                for (int dx = -half_distance; dx <= half_distance; ++dx) {
                    if (dy == 0 && dx == 0) continue; // 中心画素はスキップ
                    if (in[(y + dy) * w + (x + dx)] >= center) {
                        flag = 0; // 中心画素が周囲の画素よりも小さければフラグを0に
                        break;
                    }
                }
                if (flag == 0) break; // 一度フラグが0になったらループを終了
            }
            if (flag == 1) out[y * w + x] = 1.0; // 局所極大点の場合、出力画像に1を設定
        }
    }
}
