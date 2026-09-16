void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double THRESHOLD = 0.5; // 二値化の閾値
    const double MIN_A = 0.0; // a の最小値
    const double MAX_A = 1.0; // a の最大値
    const double MIN_B = 0.0; // b の最小値
    const double MAX_B = 1.0; // b の最大値

    // a, b の範囲チェック
    if (a < MIN_A || a > MAX_A || b < MIN_B || b > MAX_B) {
        return; // a, b の範囲外の値が与えられた場合は何もしないで終了
    }

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0; // 初期値を 0 に設定
        }
    }

    // 台形歪みのパラメータ計算
    double scale_x = (1.0 - a) * (1.0 - b) + a * b;
    double scale_y = (1.0 - a) * (1.0 - b) + a * b;

    // 台形歪みの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像の画素を取得
            double input_value = in[y * w + x];

            // 台形歪みの適用
            double new_x = (x - w / 2.0) * scale_x + w / 2.0;
            double new_y = (y - h / 2.0) * scale_y + h / 2.0;

            // 新しい座標が画像の範囲内にあるかチェック
            if (new_x >= 0 && new_x < w && new_y >= 0 && new_y < h) {
                // 新しい座標の画素値を取得
                double new_value = in[(int)new_y * w + (int)new_x];

                // 二値化
                if (new_value > THRESHOLD) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
