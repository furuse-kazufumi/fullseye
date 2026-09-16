#include <math.h>
#include <stdlib.h>
#include <string.h>

// 定数定義
#define MAX_NEIGHBORS 8
#define MIN_SEGMENT_LENGTH 8

// ネイバーの方向ベクトル
static const int dx[MAX_NEIGHBORS] = {1, 1, 0, -1, -1, -1, 0, 1};
static const int dy[MAX_NEIGHBORS] = {0, 1, 1, 1, 0, -1, -1, -1};

// 画像の端を背景(0)とみなす
#define BOUNDARY_VALUE 0

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 入力画像の領域をコピー
    memcpy(out, in, h * w * sizeof(double));

    // スケルトンの線を分割
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] == 1.0) {
                int neighbor_count = 0;
                for (int i = 0; i < MAX_NEIGHBORS; i++) {
                    int nx = x + dx[i];
                    int ny = y + dy[i];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        if (out[ny * w + nx] == 1.0) {
                            neighbor_count++;
                        }
                    } else {
                        neighbor_count += BOUNDARY_VALUE; // 端の画素は背景とみなす
                    }
                }
                if (neighbor_count >= 3) {
                    // 結合点を検出
                    // 結合点は分割しない
                    continue;
                } else {
                    // 線分を分割
                    // 線分の長さが a*MIN_SEGMENT_LENGTH より短い場合は削除
                    int segment_length = 0;
                    for (int i = 0; i < MAX_NEIGHBORS; i++) {
                        int nx = x + dx[i];
                        int ny = y + dy[i];
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            if (out[ny * w + nx] == 1.0) {
                                segment_length++;
                            }
                        } else {
                            segment_length += BOUNDARY_VALUE; // 端の画素は背景とみなす
                        }
                    }
                    if (segment_length < a * MIN_SEGMENT_LENGTH) {
                        out[y * w + x] = 0.0;
                    }
                }
            }
        }
    }
}
