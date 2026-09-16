void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によると、入力は二値画像であり、1.0 が領域を表す。出力も同様に二値画像である。
    // つまみ b は未使用と指定されているため、無視する。
    // 面積のしきい値は (16 + a * 200) 画素と指定されている。

    // しきい値の計算
    int threshold_area = 16 + (int)(a * 200);

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 連結成分の面積を計算し、しきい値未満のものを除去
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] == 1.0) {
                // 連結成分の面積を計算
                int area = 0;
                // 連結成分の探索と面積の計算
                if (in[y * w + x] == 1.0) {
                    area++;
                    in[y * w + x] = 0.0; // 探索済みの画素を 0 に設定
                    // 4 方向に隣接する画素を探索
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; ++dx) {
                            if (abs(dx + dy) == 1 && y + dy >= 0 && y + dy < h && x + dx >= 0 && x + dx < w) {
                                if (in[(y + dy) * w + (x + dx)] == 1.0) {
                                    area++;
                                    in[(y + dy) * w + (x + dx)] = 0.0; // 探索済みの画素を 0 に設定
                                }
                            }
                        }
                    }
                }
                // 面積がしきい値以上であれば、出力画像に書き込む
                if (area >= threshold_area) {
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; ++dx) {
                            if (abs(dx + dy) == 1 && y + dy >= 0 && y + dy < h && x + dx >= 0 && x + dx < w) {
                                out[(y + dy) * w + (x + dx)] = 1.0;
                            }
                        }
                    }
                }
            }
        }
    }
}
