void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 空間窓半径と輝度レンジの計算
    int sp = 5 + 25 * a; // 空間窓半径
    int sr = 10 + 40 * b; // 輝度レンジ

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 平均値シフトフィルタリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 窓内のピクセルを処理
            for (int dy = -sp; dy <= sp; dy++) {
                for (int dx = -sp; dx <= sp; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓内のピクセルが画像の範囲内にあるか確認
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double pixel = in[ny * w + nx];
                        if (fabs(pixel - in[y * w + x]) <= sr) {
                            sum += pixel;
                            count++;
                        }
                    }
                }
            }

            // 平均値を計算
            if (count > 0) {
                out[y * w + x] = sum / count;
            }
        }
    }
}
