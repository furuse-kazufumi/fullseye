void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double height_threshold = 0.05 + 0.3 * a;
    
    // 局所極大の探索と高さのしきい値によるフィルタリング
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double center = in[y * w + x];
            double max_neighbor = 0.0;
            
            // 8近傍の最大値を求める
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (dx == 0 && dy == 0) continue;
                    int nx = x + dx;
                    int ny = y + dy;
                    max_neighbor = (in[ny * w + nx] > max_neighbor) ? in[ny * w + nx] : max_neighbor;
                }
            }
            
            // 局所極大かつ高さのしきい値を超える場合、出力画像に1を設定
            if (center > max_neighbor && center - max_neighbor >= height_threshold) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
    
    // 画像の端の処理
    // ここでは端のピクセルは常に0を出力するようにする。
    for (int y = 0; y < h; y++) {
        out[y * w] = 0.0;
        out[y * w + w - 1] = 0.0;
    }
    for (int x = 0; x < w; x++) {
        out[x] = 0.0;
        out[(h - 1) * w + x] = 0.0;
    }
}
