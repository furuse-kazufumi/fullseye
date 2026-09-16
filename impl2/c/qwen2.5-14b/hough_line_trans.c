#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、つまみ b は無視します。つまみ a はエッジ抽出の閾値として使用します。
    // つまみ a の値域は [0.2, 0.6] と仮定しますが、範囲外の値も受け入れます。
    // 画像のエッジ検出には Sobel オペレータを使用します。
    // Hough 変換の実装には、角度と距離の分解能を固定値に設定します。
    // 出力画像は入力画像と同じサイズで、Hough 変換の結果を正規化して格納します。

    // Sobel オペレータのカーネル
    const double sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    const double sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    // Hough 変換の角度と距離の分解能
    const int theta_steps = 180; // 0°から180°まで
    const double rho_max = hypot(h, w); // 最大距離
    const int rho_steps = (int)rho_max + 1;

    // Hough 変換のアキュムレータ
    double accumulator[theta_steps][rho_steps];
    memset(accumulator, 0, sizeof(accumulator));

    // エッジ検出
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double gx = 0, gy = 0;
            for (int ky = 0; ky < 3; ++ky) {
                for (int kx = 0; kx < 3; ++kx) {
                    gx += sobel_x[ky][kx] * in[(y + ky - 1) * w + (x + kx - 1)];
                    gy += sobel_y[ky][kx] * in[(y + ky - 1) * w + (x + kx - 1)];
                }
            }
            double edge_strength = sqrt(gx * gx + gy * gy);
            if (edge_strength > a) {
                // Hough 変換
                for (int theta = 0; theta < theta_steps; ++theta) {
                    double rad_theta = theta * M_PI / 180.0;
                    double rho = x * cos(rad_theta) + y * sin(rad_theta);
                    int rho_index = (int)rho;
                    if (rho_index >= 0 && rho_index < rho_steps) {
                        accumulator[theta][rho_index]++;
                    }
                }
            }
        }
    }

    // アキュムレータの正規化
    double max_value = 0;
    for (int theta = 0; theta < theta_steps; ++theta) {
        for (int rho = 0; rho < rho_steps; ++rho) {
            if (accumulator[theta][rho] > max_value) {
                max_value = accumulator[theta][rho];
            }
        }
    }
    if (max_value > 0) {
        for (int theta = 0; theta < theta_steps; ++theta) {
            for (int rho = 0; rho < rho_steps; ++rho) {
                accumulator[theta][rho] /= max_value;
            }
        }
    }

    // アキュムレータを画像サイズにリサイズ
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double rho = x * cos(M_PI / 2) + y * sin(M_PI / 2);
            int rho_index = (int)rho;
            if (rho_index >= 0 && rho_index < rho_steps) {
                out[y * w + x] = accumulator[theta_steps / 2][rho_index];
            } else {
                out[y * w + x] = 0;
            }
        }
    }
}
