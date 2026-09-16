void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際の境界値を決定。ここでは、境界値を0とし、内部のピクセル値をそのまま使用する。
    // これは、境界値が入力画像の範囲外の値である可能性があるため、安全な選択である。
    const double boundary_value = 0.0;

    // ディファージェントの計算に必要な隣接ピクセルのインデックスを定義
    int dx[] = {-1, 0, 1, -1, 1, -1, 0, 1}; // x方向の移動
    int dy[] = {-1, -1, -1, 0, 0, 1, 1, 1}; // y方向の移動

    // 出力画像の各ピクセルに対して計算を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double I_xx = 0.0, I_yy = 0.0, I_xy = 0.0, I_x = 0.0, I_y = 0.0;
            double grad_I_squared = 0.0;

            // 各ピクセルの2階微分と1階微分を計算
            for (int i = 0; i < 8; ++i) {
                int nx = x + dx[i];
                int ny = y + dy[i];
                if (nx < 0 || nx >= w || ny < 0 || ny >= h) {
                    nx = (nx < 0) ? 0 : (nx >= w) ? w - 1 : nx;
                    ny = (ny < 0) ? 0 : (ny >= h) ? h - 1 : ny;
                    I_xx += (in[ny * w + nx] - in[y * w + x]) * (dx[i] == 0 ? 1 : 0);
                    I_yy += (in[ny * w + nx] - in[y * w + x]) * (dy[i] == 0 ? 1 : 0);
                    I_xy += (in[ny * w + nx] - in[y * w + x]) * (dx[i] != 0) * (dy[i] != 0);
                } else {
                    I_xx += (in[ny * w + nx] - in[y * w + x]) * (dx[i] == 0 ? 1 : 0);
                    I_yy += (in[ny * w + nx] - in[y * w + x]) * (dy[i] == 0 ? 1 : 0);
                    I_xy += (in[ny * w + nx] - in[y * w + x]) * (dx[i] != 0) * (dy[i] != 0);
                }
                I_x += (in[(ny + dy[i]) * w + (nx + dx[i])] - in[y * w + x]) * (dx[i] != 0);
                I_y += (in[(ny + dy[i]) * w + (nx + dx[i])] - in[y * w + x]) * (dy[i] != 0);
            }

            // 1階微分の平方を計算
            grad_I_squared = I_x * I_x + I_y * I_y;

            // 平均曲率運動の計算
            double numerator = I_xx * I_y * I_y + I_yy * I_x * I_x - 2 * I_x * I_y * I_xy;
            double denominator = grad_I_squared + 1e-6; // eps を追加して安定性を確保
            double curvature_motion = numerator / denominator;

            // 出力画像に結果を書き込む
            out[y * w + x] = in[y * w + x] + a * curvature_motion;
        }
    }
}
