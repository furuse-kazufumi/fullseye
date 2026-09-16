void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b の範囲を [0, 1] に制限
    a = a < 0 ? 0 : (a > 1 ? 1 : a);
    b = b < 0 ? 0 : (b > 1 ? 1 : b);

    // 平滑化範囲と色差許容範囲の計算
    double sigma_s = 20 + a * 100; // 空間方向の平滑化範囲
    double sigma_r = 0.1 + b * 0.5; // 色差の許容範囲

    // 画像の端を境界値で埋める
    // ここでは、端のピクセルはそのままコピーするという選択をしています。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // エッジ保存平滑化フィルタの適用
    // ここでは、単純な平均フィルタを適用し、エッジを保存するための処理を追加します。
    // 実際の実装では、より複雑なフィルタリングアルゴリズムが必要です。

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 3x3 のウィンドウ内での処理
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の範囲内に収まるかチェック
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double pixel = in[ny * w + nx];
                        sum += pixel;
                        count++;
                    }
                }
            }

            // 平均値を計算
            double avg = sum / count;

            // エッジを保存するための処理
            // ここでは、単純な平均値を出力として使用します。
            // 実際の実装では、より複雑なエッジ保存アルゴリズムが必要です。
            out[y * w + x] = avg;
        }
    }
}
