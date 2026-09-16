#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、a と b のパラメータは直接使用せず、代わりに内部のしきい値と比率を計算します。
    // a は非最大値抑制のしきい値を決定し、b は直線性のしきい値を決定します。
    const double threshold_a = a * 0.3; // 非最大値抑制のしきい値
    const double min_ratio = 3 + b * 12; // 直線性のしきい値

    // 画像の各画素に対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 画素の座標を計算
            int index = y * w + x;

            // 画素値がしきい値を超える場合のみ処理を実行
            if (in[index] > threshold_a) {
                // 画素の近傍画素を取得
                double sum = 0.0;
                int count = 0;
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        if (dy == 0 && dx == 0) continue; // 自身を除く
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            sum += in[ny * w + nx];
                            ++count;
                        }
                    }
                }
                // 画素の近傍画素の平均値を計算
                double avg = sum / count;

                // 画素の近傍画素の共分散行列を計算
                double cov[2][2] = {{0.0, 0.0}, {0.0, 0.0}};
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        if (dy == 0 && dx == 0) continue; // 自身を除く
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            double diff_y = in[ny * w + nx] - avg;
                            double diff_x = in[(ny + 1) * w + (nx + 1)] - avg;
                            cov[0][0] += diff_y * diff_y;
                            cov[0][1] += diff_y * diff_x;
                            cov[1][0] += diff_x * diff_y;
                            cov[1][1] += diff_x * diff_x;
                        }
                    }
                }

                // 共分散行列の固有値を計算
                double eigenvalues[2];
                if (cov[0][0] == 0 && cov[0][1] == 0 && cov[1][0] == 0 && cov[1][1] == 0) {
                    eigenvalues[0] = 0.0;
                    eigenvalues[1] = 0.0;
                } else {
                    double det = cov[0][0] * cov[1][1] - cov[0][1] * cov[1][0];
                    double trace = cov[0][0] + cov[1][1];
                    double discriminant = trace * trace - 4 * det;
                    eigenvalues[0] = (trace + sqrt(discriminant)) / 2;
                    eigenvalues[1] = (trace - sqrt(discriminant)) / 2;
                }

                // 固有値の比率を計算
                double ratio = eigenvalues[0] / eigenvalues[1];
                if (eigenvalues[1] == 0) ratio = INFINITY;

                // 固有値の比率が直線性のしきい値を超える場合のみ、出力画像に 1 を設定
                if (ratio >= min_ratio) {
                    out[index] = 1.0;
                } else {
                    out[index] = 0.0;
                }
            } else {
                out[index] = 0.0;
            }
        }
    }
}
