void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の外側は背景（0）とみなす
    // これは仕様書で明示的に指定されている処理方法です。

    // マスクの作成
    int mask[9];
    for (int i = 0; i < 9; ++i) {
        mask[i] = 0;
    }

    // 画像の各画素に対して処理を行う
    int changed;
    do {
        changed = 0;
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                // 画素の値を取得
                int pixel = (int)in[y * w + x];

                // 画素が前景（1）でない場合はスキップ
                if (pixel == 0) {
                    out[y * w + x] = 0;
                    continue;
                }

                // 画素の近傍をマスクに格納
                mask[0] = (y > 0 && x > 0) ? (int)in[(y - 1) * w + (x - 1)] : 0;
                mask[1] = (y > 0) ? (int)in[(y - 1) * w + x] : 0;
                mask[2] = (y > 0 && x < w - 1) ? (int)in[(y - 1) * w + (x + 1)] : 0;
                mask[3] = (x > 0) ? (int)in[y * w + (x - 1)] : 0;
                mask[4] = pixel;
                mask[5] = (x < w - 1) ? (int)in[y * w + (x + 1)] : 0;
                mask[6] = (y < h - 1 && x > 0) ? (int)in[(y + 1) * w + (x - 1)] : 0;
                mask[7] = (y < h - 1) ? (int)in[(y + 1) * w + x] : 0;
                mask[8] = (y < h - 1 && x < w - 1) ? (int)in[(y + 1) * w + (x + 1)] : 0;

                // 簡単な単純点の判定
                int simple = 0;
                int count = 0;
                for (int i = 0; i < 9; ++i) {
                    if (mask[i] == 0) {
                        count++;
                    }
                    if (count == 1) {
                        simple = 1;
                        break;
                    }
                }

                // 完璧な単純点の判定
                int perfect = 0;
                if (simple) {
                    for (int i = 0; i < 4; ++i) {
                        int dir = (i * 2) % 8;
                        int opp = (dir + 4) % 8;
                        if (mask[dir] == 1 && mask[opp] == 0) {
                            perfect = 1;
                            break;
                        }
                    }
                }

                // 簡単で完璧な単純点を削除
                if (simple && perfect) {
                    out[y * w + x] = 0;
                    changed = 1;
                } else {
                    out[y * w + x] = 1;
                }
            }
        }
    } while (changed);

    // 出力画像を更新
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            in[y * w + x] = out[y * w + x];
        }
    }
}
