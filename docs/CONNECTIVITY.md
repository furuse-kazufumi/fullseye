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

## 画像取り込み (acquire) (9)

| source | kind | あり | pip | 説明 |
|---|---|---|---|---|
| callable | native | ✓ | — | a user-supplied fn() -> frame |
| dir | native | ✓ | — | a folder / glob of images (offline & tests) |
| basler | optional | — | pypylon | Basler cameras |
| genicam | optional | — | harvesters | GigE/USB3 Vision via GenTL (industrial) |
| kinect | optional | — | pyk4a | Azure Kinect DK depth |
| oak | optional | — | depthai | Luxonis OAK-D depth camera |
| opencv | optional | ✓ | opencv-python | USB/UVC webcam, IP/RTSP stream, video file |
| realsense | optional | — | pyrealsense2 | Intel RealSense RGB-D (Physical AI) |
| zed | optional | — | pyzed | Stereolabs ZED stereo depth |

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
