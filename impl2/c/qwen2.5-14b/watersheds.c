#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double marker_threshold = 0.2 + 0.3 * a;
    const double epsilon = 1e-6; // 小数点以下の誤差を吸収するための閾値

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // マーカーの検出
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            if (in[idx] < marker_threshold) {
                out[idx] = 1.0;
            }
        }
    }

    // 分水嶺セグメンテーションの適用
    // ここでは、単純なマーカーを基に境界線を抽出する処理を想定しています。
    // 実際のアルゴリズムはより複雑で、隣接するピクセルとの関係を考慮する必要があります。
    // 本実装では、マーカーが存在する領域の境界を1.0として出力します。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            if (out[idx] == 1.0) {
                // マーカーの隣接ピクセルをチェック
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        if (dy == 0 && dx == 0) continue; // 自身はスキップ
                        int nx = x + dx, ny = y + dy;
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            int nidx = ny * w + nx;
                            if (out[nidx] == 0.0) {
                                out[idx] = 1.0; // 隣接する0.0のピクセルがあれば境界線としてマーク
                            }
                        }
                    }
                }
            }
        }
    }

    // 出力画像の境界線を明確にするための後処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            if (out[idx] > 0.5 + epsilon) {
                out[idx] = 1.0;
            } else {
                out[idx] = 0.0;
            }
        }
    }
}
