# Euphoric · Alien Tunnel 梦核版

基于 Shadertoy [X3ySRc《Alien Tunnel》](https://www.shadertoy.com/view/X3ySRc)
（Leonid Zaides, MIT License）的本地复刻与梦核改造。本文件夹只包含这一项目的文件。

## 目录结构

```
Euphoric/
├── index.html                  ★ 最新完整版（自包含单文件，双击即可运行）
├── 启动梦境隧道.command         双击启动本地服务器（端口 8940）并打开浏览器
├── git提交新版本.command        每次更新后双击：自动提交版本（已连 GitHub 则同时推送）
├── .gitignore                  git 忽略清单
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
- **实时调节面板** —— 右上角滑块即时调整：色相 / 饱和度 / 色温 / 亮度 / 对比度 /
  泛光 / 整体速度 / 转动速度；点 `－` 或按 `C` 收起面板，「重置默认」一键还原

**快捷键：** `空格` 暂停 · `R` 重置 · `F` 全屏 · `H` 手部检测开关 · `C` 调节面板 ·
`-`/`=` 调速（默认 ×2.5，与面板滑块同步）

## 运行

- 只看画面：双击 `index.html`
- 用摄像头手部交互 / 频闪：双击 `启动梦境隧道.command`
  （浏览器要求摄像头必须经 `http://localhost` 访问，`file://` 直开时手部功能不可用，
  其余一切正常）
- 手动起服务：`python3 -m http.server 8940` 后访问 `http://localhost:8940`

**隐私：摄像头影像仅在本地浏览器内处理，不上传任何数据。**

## Git 版本管理

本文件夹已初始化 git 仓库。每做一次更新就存一个可随时回退的版本：

1. **首次准备（只需一次）**：打开「终端」，执行
   ```bash
   chmod +x ~/Desktop/Euphoric/*.command
   ```
2. 之后每次更新后，双击 `git提交新版本.command`（或终端运行
   `bash git提交新版本.command "本次改了什么"`），它会自动提交所有改动为新版本、
   已连接 GitHub 时同时推送，并显示最近 10 个版本历史

### 连接 GitHub（首次，二选一）

- **方法 A（推荐，需安装 GitHub CLI）：**
  ```bash
  gh auth login
  gh repo create Euphoric --private --source=. --push
  ```
- **方法 B（手动）：** 在 github.com 新建一个空仓库，然后
  ```bash
  git remote add origin <你的仓库地址>
  git push -u origin main
  ```

### 查看与回退

```bash
git log --oneline                       # 查看所有版本
git diff HEAD~1                         # 对比上一版改了什么
git checkout <提交号> -- index.html     # 把某文件恢复到指定版本
```

## 重新生成 index.html

```bash
cd build
python3 build_alien_tunnel.py
```

生成器从 `build/` 目录读取两个 JSON 数据文件（原始 GLSL 源码 + 贴图），
组装出上级目录的 `index.html`。**调节面板**相关代码同样在生成器里
（`html_head` 的面板样式 / `runtime_js` 的 `sliderDefs` 与 DREAM 着色器），
改完需重新运行本脚本生成 `index.html`。想调整效果，还可以改：

- 泛光强度：运行时直接拖面板「泛光」滑块（默认值 1.45 在 `sliderDefs` 里）
- 色彩流速 / 风暴频率：DREAM 着色器里的 `t1 = iTime * 0.10`、`t2 = iTime * 0.043`
- 旋转不规律度：JS 端 `advanceTime()` 里的 `spinPhase` 调制波形
- 频闪强度与间隔：JS 端 `triggerFlash()` / `updateFlash()`

## 许可

原着色器 *Alien Tunnel* © Leonid Zaides，MIT License（版权声明保留于源码头部）。
本项目改造部分同样以 MIT 发布。
