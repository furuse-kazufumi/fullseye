void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Wiener deconvolution parameters
    const double WIENER_SIGMA_MAX = 1.0;
    const double NOISE_TO_SIGNAL_RATIO_MIN = 1e-3;
    const double NOISE_TO_SIGNAL_RATIO_MAX = 1e-3 + 0.15;

    // Compute blur sigma and noise-to-signal ratio
    double blur_sigma = a * WIENER_SIGMA_MAX;
    double noise_to_signal_ratio = NOISE_TO_SIGNAL_RATIO_MIN + b * 0.15;

    // Apply Wiener deconvolution
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Compute spatial frequency response
            double spatial_frequency_response = 1.0 / (1.0 + noise_to_signal_ratio * pow(blur_sigma, 2));

            // Compute output pixel value
            int idx = y * w + x;
            int idx_left = (x - 1 + w) % w;
            int idx_right = (x + 1) % w;
            int idx_top = (y - 1 + h) % h;
            int idx_bottom = (y + 1) % h;

            double output_value = in[idx] + spatial_frequency_response * (in[idx_left] + in[idx_right] + in[idx_top] + in[idx_bottom] - 4 * in[idx]);

            // Ensure output value is within [0, 1]
            out[idx] = (output_value < 0.0) ? 0.0 : (output_value > 1.0) ? 1.0 : output_value;
        }
    }
}
