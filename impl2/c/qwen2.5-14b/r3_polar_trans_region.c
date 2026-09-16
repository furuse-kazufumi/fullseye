#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書では具体的な半径と角度の計算方法が明示されていないため、
    // 半径は最大距離の0.25 + 0.75*a、角度は2*pi*(0.25 + 0.75*b)と定義する。
    double rmax = 0.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] > 0.5) {
                double dist = sqrt((x - w / 2) * (x - w / 2) + (y - h / 2) * (y - h / 2));
                if (dist > rmax) {
                    rmax = dist;
                }
            }
        }
    }
    rmax *= (0.25 + 0.75 * a);

    double angle_end = 2 * M_PI * (0.25 + 0.75 * b);
    int out_h = (int)ceil(rmax);
    int out_w = (int)ceil(angle_end / M_PI * out_h);

    // 出力画像の初期化
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            out[y * out_w + x] = 0.0;
        }
    }

    // 入力画像から出力画像への変換
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] > 0.5) {
                double dist = sqrt((x - w / 2) * (x - w / 2) + (y - h / 2) * (y - h / 2));
                if (dist <= rmax) {
                    double angle = atan2(y - h / 2, x - w / 2);
                    if (angle < 0) {
                        angle += 2 * M_PI;
                    }
                    int out_y = (int)floor(dist);
                    int out_x = (int)floor(angle / M_PI * out_h / 2);
                    out[out_y * out_w + out_x] = 1.0;
                }
            }
        }
    }
}
