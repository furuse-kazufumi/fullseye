#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double THRESHOLD = 0.25 + 0.5 * a; // しきい値
    const int N_ITERATIONS = 100; // EM アルゴリズムの反復回数
    const double TOLERANCE = 1e-6; // 収束判定の許容誤差

    // 画像のパーセンタイルを計算
    double* sorted = (double*)malloc(h * w * sizeof(double));
    memcpy(sorted, in, h * w * sizeof(double));
    qsort(sorted, h * w, sizeof(double), (int (*)(const void *, const void *))compare);

    double percentile25 = sorted[(int)(h * w * 0.25)];
    double percentile75 = sorted[(int)(h * w * 0.75)];
    free(sorted);

    // 初期化
    double mu1 = percentile25;
    double mu2 = percentile75;
    double sigma1 = 0.1;
    double sigma2 = 0.1;
    double pi1 = 0.5;
    double pi2 = 0.5;

    // EM アルゴリズムの実行
    for (int i = 0; i < N_ITERATIONS; i++) {
        double new_pi1 = 0.0;
        double new_pi2 = 0.0;
        double new_mu1 = 0.0;
        double new_mu2 = 0.0;
        double new_sigma1 = 0.0;
        double new_sigma2 = 0.0;

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double px = in[y * w + x];
                double p1 = pi1 * exp(-(px - mu1) * (px - mu1) / (2 * sigma1 * sigma1)) / (sqrt(2 * M_PI) * sigma1);
                double p2 = pi2 * exp(-(px - mu2) * (px - mu2) / (2 * sigma2 * sigma2)) / (sqrt(2 * M_PI) * sigma2);
                double p = p1 + p2;
                double t1 = p1 / p;
                double t2 = p2 / p;

                new_pi1 += t1;
                new_pi2 += t2;
                new_mu1 += t1 * px;
                new_mu2 += t2 * px;
                new_sigma1 += t1 * (px - mu1) * (px - mu1);
                new_sigma2 += t2 * (px - mu2) * (px - mu2);
            }
        }

        new_pi1 /= (h * w);
        new_pi2 /= (h * w);
        new_mu1 /= (h * w);
        new_mu2 /= (h * w);
        new_sigma1 = sqrt(new_sigma1 / (h * w));
        new_sigma2 = sqrt(new_sigma2 / (h * w));

        if (fabs(new_pi1 - pi1) < TOLERANCE && fabs(new_pi2 - pi2) < TOLERANCE &&
            fabs(new_mu1 - mu1) < TOLERANCE && fabs(new_mu2 - mu2) < TOLERANCE &&
            fabs(new_sigma1 - sigma1) < TOLERANCE && fabs(new_sigma2 - sigma2) < TOLERANCE) {
            break;
        }

        pi1 = new_pi1;
        pi2 = new_pi2;
        mu1 = new_mu1;
        mu2 = new_mu2;
        sigma1 = new_sigma1;
        sigma2 = new_sigma2;
    }

    // しきい値を用いて出力画像を生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double px = in[y * w + x];
            double p1 = pi1 * exp(-(px - mu1) * (px - mu1) / (2 * sigma1 * sigma1)) / (sqrt(2 * M_PI) * sigma1);
            double p2 = pi2 * exp(-(px - mu2) * (px - mu2) / (2 * sigma2 * sigma2)) / (sqrt(2 * M_PI) * sigma2);
            double p = p1 + p2;
            double t1 = p1 / p;
            double t2 = p2 / p;

            if (t1 > THRESHOLD) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    free(sorted);
}

// ソート用比較関数
int compare(const void *a, const void *b) {
    return (*(double*)a - *(double*)b);
}
