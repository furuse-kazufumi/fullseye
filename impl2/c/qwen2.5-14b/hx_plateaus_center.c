void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double epsilon = 1e-6; // 小数点以下の誤差を防ぐための閾値
    const double max_grad = 1.0; // 勾配の最大値を仮定 (後で計算される)
    const double grad_threshold = (0.01 + 0.1 * a) * max_grad; // 平坦域の勾配閾値

    // 勾配画像の初期化
    double gmag[h * w]; // 勾配画像
    for (int i = 0; i < h * w; ++i) {
        gmag[i] = 0.0;
    }

    // Sobel オペレータを用いて勾配画像を計算
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // Sobel オペレータのマスク
            double Gx = -in[(y - 1) * w + (x - 1)] + in[(y - 1) * w + (x + 1)] - 2 * in[y * w + (x - 1)] + 2 * in[y * w + (x + 1)] - in[(y + 1) * w + (x - 1)] + in[(y + 1) * w + (x + 1)];
            double Gy = in[(y - 1) * w + (x - 1)] - 2 * in[(y - 1) * w + x] + in[(y - 1) * w + (x + 1)] - in[(y + 1) * w + (x - 1)] + 2 * in[(y + 1) * w + x] - in[(y + 1) * w + (x + 1)];
            gmag[y * w + x] = sqrt(Gx * Gx + Gy * Gy);
        }
    }

    // 勾配画像の最大値を計算
    double max_gmag = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (gmag[i] > max_gmag) {
            max_gmag = gmag[i];
        }
    }

    // 平坦域の検出
    for (int i = 0; i < h * w; ++i) {
        gmag[i] = gmag[i] / max_gmag; // 勾配を最大勾配で正規化
    }

    // 平坦域の中心を計算
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            if (gmag[y * w + x] < grad_threshold) {
                // 8近傍の勾配をチェック
                bool is_flat = true;
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (gmag[(y + dy) * w + (x + dx)] >= grad_threshold) {
                            is_flat = false;
                            break;
                        }
                    }
                    if (!is_flat) break;
                }
                if (is_flat) {
                    // 重心を計算
                    double sum_x = 0.0, sum_y = 0.0, count = 0.0;
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; dx++) {
                            if (gmag[(y + dy) * w + (x + dx)] < grad_threshold) {
                                sum_x += (x + dx);
                                sum_y += (y + dy);
                                count += 1.0;
                            }
                        }
                    }
                    int center_x = round(sum_x / count);
                    int center_y = round(sum_y / count);
                    if (center_x >= 0 && center_x < w && center_y >= 0 && center_y < h) {
                        out[center_y * w + center_x] = 1.0;
                    }
                }
            }
        }
    }
}
