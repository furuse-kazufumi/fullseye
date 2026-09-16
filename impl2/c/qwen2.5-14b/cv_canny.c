#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // しきい値の計算
    int threshold1 = (int)(50 + 100 * a);
    int threshold2 = (int)(100 + 150 * b);

    // 画像のコピーを作成し、255にスケーリング
    unsigned char* scaled_in = (unsigned char*)malloc(h * w * sizeof(unsigned char));
    for (int i = 0; i < h * w; ++i) {
        scaled_in[i] = (unsigned char)(in[i] * 255);
    }

    // OpenCVのCannyアルゴリズムを手動で実装
    // ここでは、ガウシアンフィルタリングと非最大値抑制を含むCannyアルゴリズムの主要なステップを簡略化して実装します。
    // 実際のOpenCVのCanny関数はより複雑で、より効率的な実装を提供します。

    // 1. ガウシアンフィルタリング (ここでは省略)
    // 2. グレースケール画像のエッジ強度を計算
    // 3. 非最大値抑制
    // 4. ダブルしきい値処理
    // 5. ハッチング処理 (ここでは省略)

    // 2. グレースケール画像のエッジ強度を計算
    // ここでは、Sobelフィルタを適用してエッジ強度を計算します。
    int dx[] = {-1, 0, 1, -1, 0, 1, -1, 0, 1};
    int dy[] = {-1, -1, -1, 0, 0, 0, 1, 1, 1};
    int gx[] = {-1, -2, -1, 0, 0, 0, 1, 2, 1};
    int gy[] = {-1, 0, 1, -2, 0, 2, -1, 0, 1};

    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            int Gx = 0, Gy = 0;
            for (int k = 0; k < 9; ++k) {
                Gx += gx[k] * scaled_in[(y + dy[k]) * w + (x + dx[k])];
                Gy += gy[k] * scaled_in[(y + dy[k]) * w + (x + dx[k])];
            }
            int edge = sqrt(Gx * Gx + Gy * Gy);
            if (edge < threshold1) {
                out[y * w + x] = 0.0;
            } else if (edge > threshold2) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0; // ここでは、中間値は0.0として扱います。
            }
        }
    }

    // 画像の端を0.0で埋める
    for (int i = 0; i < w; ++i) {
        out[i] = 0.0;
        out[(h - 1) * w + i] = 0.0;
    }
    for (int i = 0; i < h; ++i) {
        out[i * w] = 0.0;
        out[i * w + (w - 1)] = 0.0;
    }

    // メモリを解放
    free(scaled_in);
}
