void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    int radius = 2 + (int)(a * 6); // 半径の計算
    int s0 = 10 + (int)(40 * a);   // 下方許容幅の計算
    int s1 = 10 + (int)(40 * b);   // 上方許容幅の計算

    // 画像の各画素に対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 半径の範囲内で画素を処理
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の範囲内に収まるかチェック
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double pixel = in[ny * w + nx];
                        double center = in[y * w + x];
                        double diff = fabs(pixel - center);

                        // 許容範囲内であれば平均に加算
                        if (diff >= s0 && diff <= s1) {
                            sum += pixel;
                            count++;
                        }
                    }
                }
            }

            // 平均値を計算
            if (count > 0) {
                out[y * w + x] = sum / count;
            } else {
                // 周囲の画素が全て範囲外の場合、中心画素をそのまま出力
                out[y * w + x] = in[y * w + x];
            }
        }
    }
}
