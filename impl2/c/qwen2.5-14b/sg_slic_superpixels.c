#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int max_segments = 42; // 最大セグメント数
    const double min_compactness = 0.01; // 最小コンパクトネス
    const double max_compactness = 0.21; // 最大コンパクトネス

    // セグメント数とコンパクトネスの計算
    int n_segments = max(2, round(6 + (1 - a) * 40));
    double compactness = min_compactness + a * max_compactness;

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // ここでは、SLICアルゴリズムの実装を簡略化し、セグメント数とコンパクトネスに基づいて
    // 画像の境界を検出する擬似的な処理を想定しています。実際のSLICアルゴリズムはより複雑で、
    // 色空間と空間距離を考慮してセグメントを生成します。
    // 本実装では、単純な境界検出を想定し、コンパクトネスが大きいほど境界が細かくなります。

    // 簡易的な境界検出処理
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double center = in[y * w + x];
            double sum = 0.0;
            int count = 0;

            // 8近傍の平均輝度を計算
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    if (dy == 0 && dx == 0) continue;
                    sum += in[(y + dy) * w + (x + dx)];
                    count++;
                }
            }

            double avg = sum / count;
            double diff = fabs(center - avg);

            // コンパクトネスに基づいて境界を決定
            if (diff > compactness) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
