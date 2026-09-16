void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない
    (void)a;
    (void)b;

    // 画像の端を埋める際、境界外の画素は近傍の画素値を使用する
    // これは、インペイント処理の範囲を超えた場合の処理方法を定義する

    // 画像の各画素について処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 画素のインデックス
            int idx = y * w + x;

            // 輝度が 235 超または 20 未満の画素をインペイント対象とする
            if (in[idx] > 235.0 / 255.0 || in[idx] < 20.0 / 255.0) {
                // 半径 3px の範囲内の画素の平均値を計算
                double sum = 0.0;
                int count = 0;
                for (int dy = -3; dy <= 3; ++dy) {
                    for (int dx = -3; dx <= 3; ++dx) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の範囲内に収まるか確認
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            sum += in[ny * w + nx];
                            ++count;
                        }
                    }
                }
                // 平均値を計算
                double avg = sum / count;
                // 出力画像に平均値を設定
                out[idx] = avg;
            } else {
                // 通常の画素はそのままコピー
                out[idx] = in[idx];
            }
        }
    }
}
