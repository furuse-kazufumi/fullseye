#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、境界外のピクセルは近傍のピクセル値を用いる。
    // ここでは、境界外のピクセルは0と仮定する。

    // 陰影効果を適用するための光源の方位角と仰角を計算
    double az = a * 2 * M_PI; // 方位角
    double el = (0.2 + 0.7 * b) * M_PI / 2; // 仰角

    // 光源の方向ベクトルを計算
    double lx = cos(az);
    double ly = sin(az);
    double lz = sin(el);

    // 出力画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // ピクセルの高さを取得
            double v = in[y * w + x];

            // 周囲のピクセルの高さを取得
            double v_up = (y > 0) ? in[(y - 1) * w + x] : v; // 上
            double v_down = (y < h - 1) ? in[(y + 1) * w + x] : v; // 下
            double v_left = (x > 0) ? in[y * w + x - 1] : v; // 左
            double v_right = (x < w - 1) ? in[y * w + x + 1] : v; // 右

            // 勾配を計算
            double gy = (v_down - v_up) / 2.0;
            double gx = (v_right - v_left) / 2.0;

            // 法線ベクトルを計算
            double norm = sqrt(gx * gx + gy * gy + 1);
            double nx = -gx / norm;
            double ny = -gy / norm;
            double nz = 1 / norm;

            // 光源方向ベクトルと法線ベクトルの内積を計算
            double intensity = (nx * lx + ny * ly + nz * lz);

            // 内積が0以下の場合、0にクリップ
            intensity = fmax(intensity, 0);

            // 出力画像に結果を格納
            out[y * w + x] = intensity;
        }
    }

    // 最小値と最大値を計算
    double min_val = out[0];
    double max_val = out[0];
    for (int i = 1; i < h * w; i++) {
        if (out[i] < min_val) min_val = out[i];
        if (out[i] > max_val) max_val = out[i];
    }

    // 最小値と最大値で正規化
    if (max_val > min_val) {
        for (int i = 0; i < h * w; i++) {
            out[i] = (out[i] - min_val) / (max_val - min_val);
        }
    }
}
