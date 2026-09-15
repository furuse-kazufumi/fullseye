#include <math.h>
#include <stdlib.h>

// Mersenne Twister による乱数生成器の定義
#define MT_N 624
#define MT_M 397
#define MT_MATRIX_A 0x9908b0df
#define MT_UPPER_MASK 0x80000000
#define MT_LOWER_MASK 0x7fffffff

static unsigned long mt[MT_N];
static int mti = MT_N + 1;

void init_genrand(unsigned long s) {
    mt[0] = s & 0xffffffffUL;
    for (mti = 1; mti < MT_N; mti++) {
        mt[mti] = (1812433253UL * (mt[mti - 1] ^ (mt[mti - 1] >> 30)) + mti);
        mt[mti] &= 0xffffffffUL;
    }
}

double genrand_res53() {
    unsigned long a = genrand_int32() >> 5, b = genrand_int32() >> 6;
    return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0);
}

unsigned long genrand_int32() {
    unsigned long y;
    static unsigned long mag01[2] = {0x0UL, MT_MATRIX_A};
    if (mti >= MT_N) {
        int kk;
        if (mti == MT_N + 1) init_genrand(5489UL);
        for (kk = 0; kk < MT_N - MT_M; kk++) {
            y = (mt[kk] & MT_UPPER_MASK) | (mt[kk + 1] & MT_LOWER_MASK);
            mt[kk] = mt[kk + MT_M] ^ (y >> 1) ^ mag01[y & 1];
        }
        for (; kk < MT_N - 1; kk++) {
            y = (mt[kk] & MT_UPPER_MASK) | (mt[kk + 1] & MT_LOWER_MASK);
            mt[kk] = mt[kk + (MT_M - MT_N)] ^ (y >> 1) ^ mag01[y & 1];
        }
        y = (mt[MT_N - 1] & MT_UPPER_MASK) | (mt[0] & MT_LOWER_MASK);
        mt[MT_N - 1] = mt[MT_M - 1] ^ (y >> 1) ^ mag01[y & 1];
        mti = 0;
    }
    y = mt[mti++];
    y ^= (y >> 11);
    y ^= (y << 7) & 0x9d2c5680UL;
    y ^= (y << 15) & 0xefc60000UL;
    y ^= (y >> 18);
    return y;
}

double box_muller() {
    double u1 = genrand_res53();
    double u2 = genrand_res53();
    return sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 乱数シードの設定
    unsigned long seed = (unsigned long)(a * 997) + 7;
    init_genrand(seed);

    // ノイズの標準偏差の計算
    double stddev = 0.02 + 0.2 * b;

    // 各ピクセルに対してガウスノイズを加える
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double noise = box_muller() * stddev;
            double value = in[y * w + x] + noise;
            // 値域を [0, 1] にクリッピング
            if (value < 0.0) value = 0.0;
            if (value > 1.0) value = 1.0;
            out[y * w + x] = value;
        }
    }
}
