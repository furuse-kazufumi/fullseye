#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int min_radius = 4;
    const int max_radius = 19;
    const int radius_step = 3;
    const int num_radii = (max_radius - min_radius) / radius_step + 1;
    const double threshold = a; // エッジ抽出の閾値
    const int max_radius_search = round(4 + 32 * b); // 探索する最大半径

    // Hough 変換の結果を格納する配列
    double hough_results[h * w];

    // エッジ抽出
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double edge_strength = 0.0;
            // 3x3 のマスクを使用してエッジ強度を計算
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int nx = x + dx;
                    int ny = y + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        double diff = fabs(in[ny * w + nx] - in[y * w + x]);
                        edge_strength += diff;
                    }
                }
            }
            // エッジ強度を閾値でスケーリング
            edge_strength /= 9.0;
            if (edge_strength > threshold) {
                edge_strength = 1.0;
            } else {
                edge_strength = 0.0;
            }
            hough_results[y * w + x] = edge_strength;
        }
    }

    // Hough 変換
    for (int radius = min_radius; radius <= max_radius_search && radius <= max_radius; radius += radius_step) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (hough_results[y * w + x] > 0.0) {
                    // 半径 r の円の中心座標を計算
                    for (int theta = 0; theta < 360; theta++) {
                        double rad_theta = theta * M_PI / 180.0;
                        int cx = x + radius * cos(rad_theta);
                        int cy = y + radius * sin(rad_theta);
                        if (cx >= 0 && cx < w && cy >= 0 && cy < h) {
                            // Hough 変換の累積和を計算
                            hough_results[cy * w + cx] += hough_results[y * w + x];
                        }
                    }
                }
            }
        }
    }

    // 最大応答を正規化
    double max_response = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (hough_results[i] > max_response) {
            max_response = hough_results[i];
        }
    }
    if (max_response > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] = hough_results[i] / max_response;
        }
    } else {
        for (int i = 0; i < h * w; i++) {
            out[i] = 0.0;
        }
    }
}
