# Fullseye connectivity — devices, cameras & industrial protocols

Fullseye は vision に加え **デバイス制御・産業通信** を扱う(HALCON に無い差別化)。
下表は  が返す実カタログ(この doc は自動生成)。

- **native** = 標準ライブラリのみで**すぐ動く**(uniform な API)
- **optional** =  で有効化
- **scaffold** = 特殊ハード/リアルタイム/native SDK が必要(文書化・best-effort)

## 通信プロトコル (comm) (23)

| protocol | kind | あり | pip | 説明 |
|---|---|---|---|---|
| http | native | ✓ | — | HTTP/REST client |
| modbus-tcp | native | ✓ | — | Modbus TCP client (PLC / I-O; built-in, no deps) |
| tcp | native | ✓ | — | raw TCP client socket |
| udp | native | ✓ | — | UDP socket |
| bacnet | optional | — | BAC0 | BACnet/IP (building automation) |
| can | optional | — | python-can | raw CAN bus |
| ethernet-ip | optional | — | pycomm3 | EtherNet/IP + CIP (Allen-Bradley Logix) |
| fins | optional | — | fins-driver | Omron FINS (CIO/DM areas) |
| modbus-rtu | optional | — | pymodbus | Modbus RTU (serial) via pymodbus |
| mqtt | optional | — | paho-mqtt | MQTT pub/sub (IIoT broker) |
| opcua | optional | — | asyncua | OPC-UA client (industrial servers) |
| s7 | optional | — | python-snap7 | Siemens S7 (S7comm) — DB/Merker/I/O |
| serial | optional | — | pyserial | RS-232/485 serial port (send/receive) |
| slmp | optional | — | pymcprotocol | Mitsubishi MC protocol / SLMP (MELSEC) |
| sparkplug | optional | — | pysparkplug | Sparkplug B over MQTT |
| websocket | optional | — | websocket-client | WebSocket client |
| zmq | optional | — | pyzmq | ZeroMQ messaging |
| cclink | scaffold | — | — | CC-Link IE (no pure-python master; reach via SLMP) |
| dnp3 | scaffold | — | pydnp3 | DNP3 / IEEE 1815 (SCADA/utility) |
| ethercat | scaffold | — | pysoem | EtherCAT master (RT NIC + slaves; the motion bus) |
| iec61850 | scaffold | — | pyiec61850-ng | IEC 61850 MMS/GOOSE (substation) |
| profibus | scaffold | — | pyprofibus | PROFIBUS DP (RS-485 PHY, GSD) |
| profinet | scaffold | — | pnio-dcp | PROFINET DCP commissioning (RT via gateway) |

## 画像取り込み (acquire) (10)

`unit` = `grab()` が返す量。`normalised` = [0,1] の画像 / `m` = **メートルの距離**(深度は計測値なので [0,1] に正規化しない)。
`開く` = opener が在るか。★`見つける` = **装置一覧に出るか** —— 別の問いなので別の列にしてある。2026-09-25 まで zed と kinect は開けるのに一覧に出てこず、1 列にまとめていたせいで表からは見えなかった。`—` は装置を持たない合成 backend(`acquire.NOT_ENUMERABLE` に理由つき)。`あり` = その SDK がこの環境で import できるか ——**別の問いなので別の列**にしてある(申告だけして開けない行が在った)。

| source | kind | unit | 開く | **見つける** | あり | pip | 説明 |
|---|---|---|---|---|---|---|---|
| callable | native | normalised | ✓ | — | ✓ | — | a user-supplied fn() -> frame |
| dir | native | normalised | ✓ | — | ✓ | — | a folder / glob of images (offline & tests) |
| basler | optional | normalised | ✓ | ✓ | — | pypylon | Basler cameras (pypylon) |
| genicam | optional | normalised | ✓ | ✓ | — | harvesters | GigE/USB3 Vision via GenTL (industrial) |
| opencv | optional | normalised | ✓ | ✓ | ✓ | opencv-python | USB/UVC webcam, IP/RTSP stream, video file |
| vimba | optional | normalised | ✓ | ✓ | — | vmbpy | Allied Vision Vimba X (vmbpy) |
| kinect | optional | m | ✓ | ✓ | — | pyk4a | Azure Kinect DK depth (discontinued; Orbbec is the successor) |
| oak | optional | m | ✓ | ✓ | — | depthai | Luxonis OAK-D stereo depth (depth in metres) |
| realsense | optional | m | ✓ | ✓ | — | pyrealsense2 | Intel RealSense RGB-D (depth in metres) |
| zed | optional | m | ✓ | ✓ | — | pyzed | Stereolabs ZED stereo depth (depth in metres) |

## 画素形式 (単板 59 形式)

分母は **EMVA が公表している綴りの全数**(GenICam Pixel Format Names and Values、無償)であって、こちらが知っている綴りの数ではない。**自分の表から数えると、そもそも知らない形式は永遠に見つからない** —— 実際この分母に替えて 10 bit 非詰めの Bayer 4 形式が抜けているのが出た。台帳は `examples/data/pfnc_single_plane.json`。

| 群 | 規格 | 対応 | 理由つきで外した | 対応率(外した分を除く) |
|---|--:|--:|--:|--:|
| Mono | 15 | 10 | 5 | 100% |
| Bayer | 44 | 40 | 4 | 100% |

外したものは `acquire.NOT_CARRIED` に理由つきで並ぶ(8 bit 未満 / 符号つき / 32 bit)。**黙って知らないままにはしない**のが要点で、「対応率」は 「外した理由が書いてある」ことと一緒でなければ意味がない。

**詰め形式**(`Mono12p` など 25 形式)は `acquire.unpack()` が展開する。詰めたままのバッファを `2**bits - 1` で割ると、**例外を出さずに画像に見える別のもの**が出るので、`_coerce` は uint8 の詰めバッファを拒否する。

## カメラの機能名 (SFNC 31 機能)

`ExposureTime` も `TriggerMode` も `PixelFormat` も、**GenICam SFNC が綴りを決めた規格の名前**であってベンダの名前ではない。だから **1 本の語彙表で GenTL を出す全ベンダを覆える** —— ベンダ SDK を 1 本足しても覆えるのは 1 社。台帳は `examples/data/sfnc_acquire_vocabulary.json`(SFNC v2.8 から)。

| | 数 |
|---|--:|
| 規格が**必須**と決めている機能 | 22 |
| 任意の機能 | 9 |

```python
cam = acquire.Camera(0, backend="genicam", cti=["/path/to/producer.cti"])
cam.configure(ExposureTime=5000.0, TriggerMode="Off")   # us は SFNC 1.2 が決めた単位
cam.missing_required_features()                         # 規格に足りない機能があれば出る
```

★`configure()` は**装置が実際に取った値**を読み直して返す。カメラは clamp する(上限 33000 us の機に 100000 を頼めば 33000 になる)ので、要求値を返すのは小さな嘘になり、そのまま露光の取り違えになる。

★単位は推測しない。`ExposureTime` は **us**、`AcquisitionFrameRate` は **Hz**、`PayloadSize` は **B**、`TimestampLatchValue` は **ns**。**`Gain` に単位の規定は無い**(`dB` は §1.2 の一覧に載っているだけ)ので、この層は Gain を dB と呼ばない。

## webcam の機能名 (UVC 49 制御)

`opencv` backend が開いているのは **USB Video Class (UVC) 1.5** の装置で、この規格も
GenICam SFNC と同じように制御の名前を決めている。台帳は `examples/data/uvc_controls.json`
(UVC 1.5 の本文から)。

| | 数 |
|---|--:|
| Camera Terminal `CT_*` | 21 |
| Processing Unit `PU_*` | 19 |
| Video Streaming `VS_*` | 9 |

```python
acquire.uvc_to_sfnc("CT_EXPOSURE_TIME_ABSOLUTE_CONTROL", 5000)   # -> ("ExposureTime", 500000.0)
acquire.sfnc_to_uvc("ExposureTime", 500000.0)                    # -> (..., 5000)
```

★**2 つの規格で露光の単位が違う**。UVC の `dwExposureTimeAbsolute` は本文が
「1: 0.0001 sec … 100000: 10 sec」と定める **0.0001 秒(100 us)刻み**、SFNC の
`ExposureTime` は **us**。同じ `5000` が 5 ms と **0.5 秒**になる —— 100 倍で、例外は
出ず絵の明るさだけが変わる。だから換算は表に書き、門が往復で確かめる。

★単位は**本文が言っているものだけ**を運ぶ。焦点は **mm**、絞りは **f 値 × 100**、
パン・チルトは**秒角**。`Gain` は UVC も SFNC も単位を規定していないので、この層は
どちらの側でも `dB` と呼ばない。

## 取り込み層の 8 軸 (8/8)

公開されている 13 の Python SDK を採点したのと**同じ 8 軸**で、この層自身を採点する。違う物差しで測った数を並べると「SDK より厚い」が意味を失う。

★自己申告にしない。各軸は**どの入口で満たされているか**を実在する名前で名指しし、門がその名前を引く。改名や削除があれば落ちる —— **証拠が消えた「対応済み」は嘘になる**。

| 軸 | 充足 | 入口 |
|---|---|---|
| 列挙 | ✓ | `list_devices`・`_enumerate`・`gentl_producers` |
| 取得モード | ✓ | `Camera.grab`・`Camera.frames`・`Camera.stream`・`Camera.grab_frame` |
| バッファ | ✓ | `Camera._raw_grab` |
| 画素形式 | ✓ | `PIXEL_BITS`・`PACKED_FORMATS`・`NOT_CARRIED`・`unpack` |
| ビット深度 | ✓ | `bit_depth_of`・`_to01` |
| メタデータ | ✓ | `Frame`・`Camera.features` |
| 物理単位 | ✓ | `DEPTH_BACKENDS`・`SFNC_FEATURES` |
| 終了処理 | ✓ | `Camera.close` |

比較の相手は `C:/dev/docs/device_sdk_corpus/COVERAGE.md`(`pypylon` と `vmbpy` が 8/8、`ouster` / `pyrealsense2` / `zivid` が 7/8)。

## デバイス制御 (device) (12)

| driver | kind | 種別 | pip | 説明 |
|---|---|---|---|---|
| io-memory | native | io | — | in-process digital I/O (tests / dry-run) |
| io-modbus | native | io | — | digital I/O over Modbus coils (built-in) |
| canopen | optional | motion | canopen | CANopen CiA-402 motion drives |
| dynamixel | optional | servo | dynamixel-sdk | Robotis Dynamixel servos |
| feetech | optional | servo | feetech-servo-sdk | Feetech STS/SCS servos |
| gpio | optional | io | python-periphery | SBC GPIO — Raspberry Pi / Jetson (also RPi.GPIO / gpiod) |
| robotiq | optional | gripper | pyRobotiqGripper | Robotiq 2F / Hand-E grippers |
| ros | optional | middleware | rclpy | ROS 2 node bridge (rclpy) |
| ur-rtde | optional | robot | ur_rtde | Universal Robots RTDE / URScript |
| xarm | optional | robot | xArm-Python-SDK | UFACTORY xArm / Lite6 / 850 |
| franka | scaffold | robot | panda-python | Franka Panda / FR3 (libfranka + RT kernel) |
| kinova | scaffold | robot | — | Kinova Gen3 (off-PyPI kortex wheel) |

## 使い方(native はすぐ動く)

```python
import fullseye
# 検査 → PLC ハンドシェイク(ハード無しでも simulator でテスト可)
srv = fullseye.ModbusTcpServer(port=1502).start()          # 開発用シミュレータ
io  = fullseye.DigitalIO("modbus", host="127.0.0.1", port=1502)
ok  = fullseye.FullseyeEngine.from_ops("gaussian,otsu").run(frame).mean() > 0.5
fullseye.signal_result(io, ok)      # PASS/FAIL 出力を駆動
fullseye.pulse(io, pin=3, ms=50)    # リジェクト射出
```

カメラ: `with fullseye.Camera(0) as cam: frame = cam.grab()`(USB/UVC/IP/RTSP、深度は RealSense/OAK-D 等 optional)。
