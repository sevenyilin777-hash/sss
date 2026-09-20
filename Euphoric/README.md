# Euphoric · Alien Tunnel 梦核版

基于 Shadertoy [X3ySRc《Alien Tunnel》](https://www.shadertoy.com/view/X3ySRc)
（Leonid Zaides, MIT License）的本地复刻与梦核改造。本文件夹只包含这一项目的文件。

## 目录结构

```
Euphoric/
├── index.html                  ★ 最新完整版（自包含单文件，双击即可运行）
├── 启动梦境隧道.command         双击启动本地服务器（端口 8940）并打开浏览器
└── build/                      构建工具链
    ├── build_alien_tunnel.py        生成器（便携版：从本目录读取数据）
    ├── shadertoy_X3ySRc_data.json   从 Shadertoy 提取的 4 个 Pass GLSL 源码
    └── shadertoy_X3ySRc_tex.json    256×256 灰噪声贴图（base64 data URL）
```

## 当前版本功能

在原版《Alien Tunnel》基础上增加：

- **梦核动态调色** —— 乳白/淡紫/灰紫/淡粉/青绿/荧光绿/蓝紫；多频互质时钟 +
  域扭曲双层噪声场驱动，前/中/远景各自演化，永不循环、从不同步
- **色彩风暴** —— 稀疏噪声阈值触发的局部色彩骤变，伴随自发光与 Bloom 增强
- **染色泛光 / 荧光溢出** —— Bloom 随局部色彩漂移，柔和过曝
- **手部扰动旋转** —— MediaPipe Hands 摄像头检测手掌位置，手移动速度转化为
  空间旋转的角速度冲量（带惯性，停止后平滑恢复原状）
- **频闪过载** —— 手部扰动期间随机触发 150–250ms 的短促闪光
  （整体提亮 + 局部过曝 + 梦核色偏，含随机回闪），无固定频率
- **不规律高速旋转** —— 轨道时钟经多频非线性调制，忽快忽慢、永不循环
- **慢速色彩流动** —— 颜色变化刻意比主体运动慢一档，保持梦境般的漂移感

## 运行

- 只看画面：双击 `index.html`
- 用摄像头手部交互 / 频闪：双击 `启动梦境隧道.command`
  （浏览器要求摄像头必须经 `http://localhost` 访问，`file://` 直开时手部
  功能不可用，其余一切正常）
- 手动起服务：`python3 -m http.server 8940` 后访问 `http://localhost:8940`

**快捷键：** `空格` 暂停 · `R` 重置 · `F` 全屏 · `H` 手部检测开关 · `-`/`=` 调速（默认 ×2.5）

**隐私：摄像头影像仅在本地浏览器内处理，不上传任何数据。**

## 重新生成 index.html

```bash
cd build
python3 build_alien_tunnel.py
```

生成器从 `build/` 目录读取两个 JSON 数据文件（原始 GLSL 源码 + 贴图），
组装出上级目录的 `index.html`。想调整效果，在生成器里改：

- 泛光强度：`uGlow`（当前 1.45）
- 色彩流速 / 风暴频率：DREAM 着色器里的 `t1 = iTime * 0.10`、`t2 = iTime * 0.043`
- 旋转不规律度：JS 端 `advanceTime()` 里的 `spinPhase` 调制波形
- 频闪强度与间隔：JS 端 `triggerFlash()` / `updateFlash()`

## 许可

原着色器 *Alien Tunnel* © Leonid Zaides，MIT License（版权声明保留于源码头部）。
本项目改造部分同样以 MIT 发布。
