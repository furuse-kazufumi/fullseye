-- fullseye_abi.h を LuaJIT の FFI から直接叩く見本。**バインディング層は無い。**
--
-- ★この例は **手元に LuaJIT が無いため未実行**(2026-09-14)。宣言は
--   `fullseye_abi.h` から機械的に書き写したもので、動作は確認していない。
--   「書いた」と「走った」を混ぜないために、ここに明記しておく。
--
-- 実行: luajit rust/fullseye_core/examples/luajit_ffi.lua
-- 先に: cd rust/fullseye_core && cargo build --release

local ffi = require("ffi")

ffi.cdef [[
typedef struct fs_image     fs_image_t;
typedef struct fs_region    fs_region_t;
typedef struct fs_objectset fs_objectset_t;

int  fs_abi_version(int32_t *major, int32_t *minor);
/* ★fs_dtype_t は契約の第 5 引数。ここが抜けていた(2026-09-14)——
   ヘッダは 8 引数、実装と 3 つの FFI 宣言は 7 引数だった。FFI で宣言を
   書き写す言語どうしを突き合わせても、全員が同じ写し間違いをしていれば
   一致してしまう。C から #include して初めて型検査が働く。 */
int  fs_image_create(const void *pixels, int32_t height, int32_t width,
                     int64_t row_stride_bytes, int32_t dtype,
                     double range_lo, double range_hi, fs_image_t **out);
int  fs_image_dtype(const fs_image_t *img, int32_t *out);
int  fs_threshold(const fs_image_t *img, double lo, double hi, fs_region_t **out);
int  fs_region_area(const fs_region_t *reg, int64_t *out);
int  fs_region_run_count(const fs_region_t *reg, int64_t *out);
int  fs_connection(const fs_region_t *reg, fs_objectset_t **out);
int  fs_objectset_count(const fs_objectset_t *objs, int64_t *out);
void fs_image_release(fs_image_t *img);
void fs_region_release(fs_region_t *reg);
void fs_objectset_release(fs_objectset_t *objs);
]]

local names = { Windows = "fullseye_core.dll", OSX = "libfullseye_core.dylib" }
local libname = names[ffi.os] or "libfullseye_core.so"
local here = (debug.getinfo(1, "S").source:sub(2):match("(.*[/\\])") or "./")
local fs = ffi.load(here .. "../target/release/" .. libname)

-- R-1: すべての関数が状態コードを返す。黙って代替値を使わない。
local function check(st, what)
  if st ~= 0 then error(("%s が status %d を返した"):format(what, st)) end
end

local maj, min = ffi.new("int32_t[1]"), ffi.new("int32_t[1]")
check(fs.fs_abi_version(maj, min), "fs_abi_version")
print(("ABI %d.%d"):format(maj[0], min[0]))

local N = 8
local px = ffi.new("double[?]", N * N)
for r = 0, N - 1 do
  for c = 0, N - 1 do
    px[r * N + c] = (r + c) % 2          -- 市松
  end
end

local img = ffi.new("fs_image_t*[1]")
check(fs.fs_image_create(px, N, N, N * 8, 0.0, 1.0, img), "fs_image_create")

-- lo/hi は 0..1 の相対値。画像が名乗る値域を通して解決される(R-3)。
local reg = ffi.new("fs_region_t*[1]")
check(fs.fs_threshold(img[0], 0.5, 1.0, reg), "fs_threshold")

local area, runs = ffi.new("int64_t[1]"), ffi.new("int64_t[1]")
check(fs.fs_region_area(reg[0], area), "fs_region_area")
check(fs.fs_region_run_count(reg[0], runs), "fs_region_run_count")

local objs = ffi.new("fs_objectset_t*[1]")
check(fs.fs_connection(reg[0], objs), "fs_connection")
local n = ffi.new("int64_t[1]")
check(fs.fs_objectset_count(objs[0], n), "fs_objectset_count")

print(("面積 %d / run %d / 物体 %d"):format(tonumber(area[0]), tonumber(runs[0]), tonumber(n[0])))
-- 契約は 8 連結なので市松は 1 個(4 連結なら 32 個)。
if tonumber(n[0]) == 1 and tonumber(area[0]) == 32 then
  print("契約どおり: 8x8 の市松は 8 連結で 1 個")
else
  print("★契約と違う")
end

-- 逆さの区間は「空」ではなく**失敗**(R-1)。
local bad = fs.fs_threshold(img[0], 0.8, 0.2, ffi.new("fs_region_t*[1]"))
print(bad ~= 0 and ("逆さの区間 lo>hi は status %d で拒まれた"):format(bad)
                or "★逆さの区間が通ってしまった")

fs.fs_objectset_release(objs[0])
fs.fs_region_release(reg[0])
fs.fs_image_release(img[0])
