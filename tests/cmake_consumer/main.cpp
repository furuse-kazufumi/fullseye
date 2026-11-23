// Installed-package consumer gate / インストール済み Config package の利用門。
#include <fullseye.hpp>

int main(int argc, char **argv) {
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    if (argc > 1) {
        options.runtime_root = argv[1];
    }
    fullseye::Runtime runtime(options);
    return runtime.find_ops("{\"limit\":1}").empty() ? 1 : 0;
}
