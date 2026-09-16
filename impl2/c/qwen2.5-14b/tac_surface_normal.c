#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a は勾配ゲインを調整します。つまみ b は前平滑化のシグマを調整します。
    // つまみが使われない場合は、デフォルト値 (a=0.5, b=0.5) を使用します。
    // 画像の端の処理については、境界外のピクセルは近傍のピクセルを使用して補間します。

    // 勾配ゲインと前平滑化のシグマを計算
    double gain = a * 20.0 + 1.0; // つまみ a は 1 から 21 の範囲に変換
    double sigma = b * 3.0;       // つまみ b は 0 から 3 の範囲に変換

    // 前平滑化 (ガウシアンフィルタ)
    double* smoothed = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }
            smoothed[y * w + x] = sum / count;
        }
    }

    // 勾配計算
    double* gx = (double*)malloc(h * w * sizeof(double));
    double* gy = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum_x = 0.0;
            double sum_y = 0.0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double diff_x = smoothed[ny * w + nx] - smoothed[(ny - 1) * w + nx];
                        double diff_y = smoothed[ny * w + nx] - smoothed[ny * w + (nx - 1)];
                        sum_x += diff_x;
                        sum_y += diff_y;
                    }
                }
            }
            gx[y * w + x] = sum_x / (gain * 9.0);
            gy[y * w + x] = sum_y / (gain * 9.0);
        }
    }

    // 法線の z 成分を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double p = gx[y * w + x];
            double q = gy[y * w + x];
            out[y * w + x] = 1.0 / sqrt(1.0 + p * p + q * q);
        }
    }

    // 動的確保メモリを解放
    free(smoothed);
    free(gx);
    free(gy);
}
