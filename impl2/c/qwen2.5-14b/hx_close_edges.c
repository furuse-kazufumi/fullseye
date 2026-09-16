#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int max_it = 4; // 最大反復回数
    const int struct_elem_size = 3; // 構造要素のサイズ (3x3)
    
    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));
    
    // 二値化しきい値 a で二値化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            out[idx] = (in[idx] > a) ? 1.0 : 0.0;
        }
    }
    
    // 構造要素の反復回数 it の計算
    int it = 1 + (int)(b * 3);
    it = (it > max_it) ? max_it : it; // it の上限を設定
    
    // モルフォロジカルクロージングの実行
    for (int i = 0; i < it; i++) {
        // 膨張
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                int idx = y * w + x;
                double max_val = out[idx];
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int idx_neighbor = (y + dy) * w + (x + dx);
                        max_val = (out[idx_neighbor] > max_val) ? out[idx_neighbor] : max_val;
                    }
                }
                out[idx] = max_val;
            }
        }
        
        // 収縮
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                int idx = y * w + x;
                double min_val = out[idx];
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int idx_neighbor = (y + dy) * w + (x + dx);
                        min_val = (out[idx_neighbor] < min_val) ? out[idx_neighbor] : min_val;
                    }
                }
                out[idx] = min_val;
            }
        }
    }
}
