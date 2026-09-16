#include <math.h>
#include <stdlib.h>
#include <string.h>

// 定義: 画素の最大値
#define MAX_PIXEL_VALUE 1.0

// 定義: 画素の最小値
#define MIN_PIXEL_VALUE 0.0

// 定義: 画素の閾値
#define THRESHOLD 0.5

// 定義: 画素の境界値
#define BOUNDARY_VALUE 0.0

// 定義: 画素の内部値
#define INSIDE_VALUE 1.0

// 定義: 反復回数の最大値
#define MAX_ITERATIONS 100

// 定義: 画素の隣接画素のインデックス
#define NEIGHBOR_OFFSETS {-1, 0, 1, -w, 1, -w-1, -w, -w, -w}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 出力画像を入力画像と同じ値で初期化
    memcpy(out, in, h * w * sizeof(double));

    // 反復処理
    for (int iter = 0; iter < MAX_ITERATIONS; iter++) {
        // 一時的な出力画像を用意
        double* temp = (double*)malloc(h * w * sizeof(double));
        memcpy(temp, out, h * w * sizeof(double));

        // 画像の各画素に対して処理
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 画素が領域内かどうかを判定
                if (out[y * w + x] == INSIDE_VALUE) {
                    // 画素の隣接画素をチェック
                    int count = 0;
                    for (int i = 0; i < 8; i++) {
                        int ny = y + NEIGHBOR_OFFSETS[i];
                        int nx = x + NEIGHBOR_OFFSETS[i + 1];
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w && out[ny * w + nx] == INSIDE_VALUE) {
                            count++;
                        }
                    }

                    // 画素が細線化の条件を満たすかどうかを判定
                    if (count >= 2 && count <= 6) {
                        int p2 = out[(y - 1) * w + x];
                        int p3 = out[(y - 1) * w + (x + 1)];
                        int p4 = out[y * w + (x + 1)];
                        int p5 = out[(y + 1) * w + (x + 1)];
                        int p6 = out[(y + 1) * w + x];
                        int p7 = out[(y + 1) * w + (x - 1)];
                        int p8 = out[y * w + (x - 1)];
                        int p9 = out[(y - 1) * w + (x - 1)];

                        int A = ((p2 == INSIDE_VALUE) && (p3 == BOUNDARY_VALUE)) ? 1 : 0;
                        int B = ((p3 == INSIDE_VALUE) && (p4 == BOUNDARY_VALUE)) ? 1 : 0;
                        int C = ((p4 == INSIDE_VALUE) && (p5 == BOUNDARY_VALUE)) ? 1 : 0;
                        int D = ((p5 == INSIDE_VALUE) && (p6 == BOUNDARY_VALUE)) ? 1 : 0;
                        int E = ((p6 == INSIDE_VALUE) && (p7 == BOUNDARY_VALUE)) ? 1 : 0;
                        int F = ((p7 == INSIDE_VALUE) && (p8 == BOUNDARY_VALUE)) ? 1 : 0;
                        int G = ((p8 == INSIDE_VALUE) && (p9 == BOUNDARY_VALUE)) ? 1 : 0;
                        int H = ((p9 == INSIDE_VALUE) && (p2 == BOUNDARY_VALUE)) ? 1 : 0;

                        int m1 = (A && !(B && H)) ? 1 : 0;
                        int m2 = (B && !(C && A)) ? 1 : 0;
                        int m3 = (C && !(D && B)) ? 1 : 0;
                        int m4 = (D && !(E && C)) ? 1 : 0;
                        int m5 = (E && !(F && D)) ? 1 : 0;
                        int m6 = (F && !(G && E)) ? 1 : 0;
                        int m7 = (G && !(H && F)) ? 1 : 0;
                        int m8 = (H && !(A && G)) ? 1 : 0;

                        int n1 = (m1 && m2) ? 1 : 0;
                        int n2 = (m2 && m3) ? 1 : 0;
                        int n3 = (m3 && m4) ? 1 : 0;
                        int n4 = (m4 && m5) ? 1 : 0;
                        int n5 = (m5 && m6) ? 1 : 0;
                        int n6 = (m6 && m7) ? 1 : 0;
                        int n7 = (m7 && m8) ? 1 : 0;
                        int n8 = (m8 && m1) ? 1 : 0;

                        if (n1 + n2 + n3 + n4 + n5 + n6 + n7 + n8 == 1) {
                            temp[y * w + x] = BOUNDARY_VALUE;
                        }
                    }
                }
            }
        }

        // 一時的な出力画像を正式な出力画像にコピー
        memcpy(out, temp, h * w * sizeof(double));

        // 一時的な出力画像を解放
        free(temp);

        // 出力画像が変化しなければ終了
        int changed = 0;
        for (int i = 0; i < h * w; i++) {
            if (out[i] != temp[i]) {
                changed = 1;
                break;
            }
        }
        if (!changed) {
            break;
        }
    }
}
