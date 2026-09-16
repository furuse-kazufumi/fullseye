void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int cell_size = 6 + 2 * (int)(a * 3); // セルサイズの計算
    const int block_size = 2; // ブロックサイズは固定
    const int num_orientations = 8; // 方向数は固定

    // 出力画像の高さと幅の計算
    int out_h = (h + cell_size - 1) / cell_size;
    int out_w = (w + cell_size - 1) / cell_size;

    // グラデーションの計算
    double* gradients = (double*)malloc(h * w * 2 * sizeof(double));
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // デリバティブの計算 (単純な差分)
            double dx = (x < w - 1) ? in[y * w + x + 1] - in[y * w + x] : 0;
            double dy = (y < h - 1) ? in[(y + 1) * w + x] - in[y * w + x] : 0;
            gradients[y * w * 2 + x * 2] = dx;
            gradients[y * w * 2 + x * 2 + 1] = dy;
        }
    }

    // HOG特徴量の計算
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            int cell_start_x = x * cell_size;
            int cell_start_y = y * cell_size;
            double cell_gradients[num_orientations] = {0};

            // セル内の勾配の計算
            for (int cy = cell_start_y; cy < cell_start_y + cell_size; ++cy) {
                for (int cx = cell_start_x; cx < cell_start_x + cell_size; ++cx) {
                    if (cx >= w || cy >= h) continue; // 画像の外側は無視
                    double dx = gradients[cy * w * 2 + cx * 2];
                    double dy = gradients[cy * w * 2 + cx * 2 + 1];
                    double mag = sqrt(dx * dx + dy * dy);
                    double angle = atan2(dy, dx) * (180.0 / M_PI); // 角度の計算
                    int bin = (int)((angle + 180) / (360.0 / num_orientations)) % num_orientations; // バイナリ化
                    cell_gradients[bin] += mag; // 方向別に累積
                }
            }

            // ブロック内の勾配の計算
            double block_gradients[num_orientations * block_size * block_size] = {0};
            for (int by = -1; by <= 0; ++by) {
                for (int bx = -1; bx <= 0; ++bx) {
                    int cy = y + by;
                    int cx = x + bx;
                    if (cy < 0 || cx < 0 || cy >= out_h || cx >= out_w) continue; // 画像の外側は無視
                    for (int i = 0; i < num_orientations; ++i) {
                        block_gradients[(by + 1) * block_size + (bx + 1) * num_orientations + i] = cell_gradients[i];
                    }
                }
            }

            // ブロック内の勾配の正規化
            double block_norm = 0;
            for (int i = 0; i < num_orientations * block_size * block_size; ++i) {
                block_norm += block_gradients[i] * block_gradients[i];
            }
            block_norm = sqrt(block_norm);

            // 正規化された勾配を出力画像に書き込む
            for (int i = 0; i < num_orientations * block_size * block_size; ++i) {
                int out_index = (y * out_w + x) * num_orientations * block_size * block_size + i;
                if (out_index < h * w) {
                    out[out_index] = block_gradients[i] / block_norm;
                }
            }
        }
    }

    // 出力画像の最大値で正規化
    double max_value = 0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }
    if (max_value > 0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_value;
        }
    }

    // メモリの解放
    free(gradients);
}
