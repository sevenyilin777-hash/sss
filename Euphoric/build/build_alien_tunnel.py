#!/usr/bin/env python3
"""Build the local replica of Shadertoy X3ySRc ("Alien Tunnel"):
dreamcore grade + bloom + 2.5x speed + webcam hand-disturbance rotation.
(Pre star-pointer version.)"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "shadertoy_X3ySRc_data.json")) as f:
    data = json.load(f)
with open(os.path.join(HERE, "shadertoy_X3ySRc_tex.json")) as f:
    tex = json.load(f)

src = {p["name"]: p["source"] for p in data["passes"]}

# --- hand-disturbance rotation injection into Buffer B (view-space perturbation) ---
bufb = src["Buffer B"]
_anchor = "        d = camera(o, d, 0.75*target, view);"
assert _anchor in bufb, "camera call anchor not found"
bufb = bufb.replace(_anchor, _anchor + "\n        d = uHand * d;", 1)

# --- 不规律旋转: 相机轨道时钟替换为 JS 端驱动的不规则时间源 ---
o_call = "    vec3 o = getOrigin(0.75*iTime - 1., iChannel1, 1.);"
t_call = "    vec3 target = getOrigin(0.75*iTime - 2., iChannel1, 1.);"
assert o_call in bufb and t_call in bufb, "getOrigin calls not found"
bufb = bufb.replace(o_call, "    vec3 o = getOrigin(uSpinT, iChannel1, 1.);", 1)
bufb = bufb.replace(t_call, "    vec3 target = getOrigin(uSpinT - 1., iChannel1, 1.);", 1)

payload = {
    "shaderId": data["shaderID"],
    "title": "Alien Tunnel",
    "author": "Leonid Zaides (3d) — shadertoy.com/view/X3ySRc, MIT license",
    "common": src["Common"],
    "image": src["Image"],
    "bufA": src["Buffer A"],
    "bufB": bufb,
    "noise": tex["dataUrl"],
}

html_head = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alien Tunnel — 本地复刻 (Shadertoy X3ySRc)</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
  #glcanvas { width: 100vw; height: 100vh; display: block; }
  #hud {
    position: fixed; left: 10px; top: 10px; z-index: 2;
    font: 12px/1.5 -apple-system, "SF Mono", Menlo, monospace;
    color: #cfd8dc; background: rgba(0,0,0,.45); padding: 8px 10px;
    border-radius: 6px; pointer-events: none; white-space: pre;
  }
  #hud a { color: #80cbc4; }
  #err {
    position: fixed; inset: 0; display: none; overflow: auto;
    color: #ff8a80; background: #111; font: 13px/1.6 Menlo, monospace;
    padding: 20px; white-space: pre-wrap;
  }
  #panel {
    position: fixed; right: 10px; top: 10px; z-index: 3;
    width: 240px; padding: 8px 12px 10px;
    font: 12px/1.6 -apple-system, "SF Mono", Menlo, monospace;
    color: #cfd8dc; background: rgba(8,10,14,.60);
    border: 1px solid rgba(255,255,255,.09); border-radius: 10px;
    backdrop-filter: blur(8px); user-select: none;
  }
  #panel h3 {
    margin: 0 0 4px; font-size: 12px; font-weight: 600; letter-spacing: 3px;
    color: #80cbc4; display: flex; align-items: center; justify-content: space-between;
  }
  #panel .row { display: flex; align-items: center; gap: 8px; margin: 2px 0; }
  #panel .row label { flex: none; width: 58px; color: #b0bec5; }
  #panel .row .val { flex: none; width: 44px; text-align: right;
    color: #9fb8c8; font-variant-numeric: tabular-nums; }
  #panel input[type=range] {
    flex: 1 1 auto; min-width: 0; margin: 0; accent-color: #80cbc4; cursor: pointer; }
  #panel .foot { display: flex; justify-content: flex-end; margin-top: 4px; }
  #panel button {
    font: 11px/1.6 -apple-system, "SF Mono", Menlo, monospace;
    color: #cfd8dc; background: rgba(255,255,255,.10);
    border: 0; border-radius: 5px; padding: 1px 10px; cursor: pointer; }
  #panel button:hover { background: rgba(255,255,255,.22); }
</style>
</head>
<body>
<canvas id="glcanvas"></canvas>
<video id="cam" playsinline style="display:none"></video>
<div id="hud">Alien Tunnel — Leonid Zaides (MIT)
Shadertoy X3ySRc 本地复刻 | <span id="fps">--</span> fps
[空格] 暂停  [R] 重置  [F] 全屏  [-/=] 速度 ×<span id="spd">2.5</span>  [C] 面板
✋ <span id="hand">手部: 启动中…</span>  [H] 开/关</div>
<div id="panel">
  <h3>调节器<button id="panelFold" title="收起 / 展开 (C)">－</button></h3>
  <div id="panelBody"></div>
</div>
<pre id="err"></pre>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.min.js"></script>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
"""

html_tail = """
</script>
</body>
</html>
"""

runtime_js = r"""
"use strict";
(function () {
  const payload = JSON.parse(document.getElementById("payload").textContent);
  const errBox = document.getElementById("err");
  const fpsEl = document.getElementById("fps");
  function fail(msg) { errBox.style.display = "block"; errBox.textContent += msg + "\n\n"; }
  window.addEventListener("error", (e) => fail("JS error: " + e.message));

  const canvas = document.getElementById("glcanvas");
  const gl = canvas.getContext("webgl2", { antialias: false, alpha: false });
  if (!gl) { fail("需要 WebGL2 支持"); return; }

  // ---- Shadertoy-style header (GLSL ES 3.00) ----
  const HEADER = `#version 300 es
precision highp float;
precision highp int;
precision highp sampler2D;

uniform vec3      iResolution;           // viewport resolution (pixels)
uniform float     iTime;                 // shader playback time (s)
uniform float     iTimeDelta;            // render time (s)
uniform float     iFrameRate;            // average fps
uniform int       iFrame;                // frame counter
uniform float     iChannelTime[4];       // channel playback time
uniform vec3      iChannelResolution[4]; // channel resolution
uniform vec4      iMouse;                // mouse drag pixels
uniform vec4      iDate;                 // y, m, d, s
uniform float     iSampleRate;           // 44100
uniform sampler2D iChannel0;
uniform sampler2D iChannel1;
uniform sampler2D iChannel2;
uniform sampler2D iChannel3;

layout(location = 0) out highp vec4 fragColor;
`;

  const WRAPPER = "\nvoid main() { mainImage(fragColor, gl_FragCoord.xy); }\n";

  // ---- dreamcore post pipeline: bright extract + gaussian blur + flowing grade ----
  const BRIGHT = HEADER + `
uniform float uThresh;
void main() {
  vec2 uv = gl_FragCoord.xy / iResolution.xy;
  vec3 c = texture(iChannel0, uv).rgb;
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float k = smoothstep(uThresh, uThresh + 0.35, l);
  fragColor = vec4(c * k, 1.0);
}`;

  const BLUR = HEADER + `
uniform vec2 uDir;
void main() {
  vec2 uv = gl_FragCoord.xy / iResolution.xy;
  vec3 s = texture(iChannel0, uv).rgb * 0.227027;
  s += (texture(iChannel0, uv + uDir * 1.3846).rgb +
        texture(iChannel0, uv - uDir * 1.3846).rgb) * 0.3162162;
  s += (texture(iChannel0, uv + uDir * 3.2308).rgb +
        texture(iChannel0, uv - uDir * 3.2308).rgb) * 0.0702703;
  fragColor = vec4(s, 1.0);
}`;

  // 梦核调色: 乳白/淡紫/灰紫/淡粉/青绿/荧光绿/蓝紫, 随 iTime 缓慢流动
  const DREAM = HEADER + `
uniform float uGlow;
uniform float uFlash;      // 频闪包络 0..1 (JS 端随机触发, 快速衰减)
uniform float uFlashSeed;  // 每次频闪的随机种子: 决定位置/色偏方向
uniform float uHue;        // 用户滑块: 色相偏移 (弧度)
uniform float uSat;        // 用户滑块: 饱和度倍率
uniform float uTemp;       // 用户滑块: 色温 (-1 冷 .. +1 暖)
uniform float uBright;     // 用户滑块: 亮度倍率
uniform float uContrast;   // 用户滑块: 对比度倍率
const vec3 W = vec3(0.2126, 0.7152, 0.0722);

float hash11(float n) { return fract(sin(n) * 43758.5453123); }
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash12(i);
  float b = hash12(i + vec2(1.0, 0.0));
  float c = hash12(i + vec2(0.0, 1.0));
  float d = hash12(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fnoise(vec2 p) {
  return vnoise(p) * 0.65 + vnoise(p * 2.13 + 7.7) * 0.35;
}
vec3 hueRotate(vec3 c, float a) {
  // 绕灰轴 (1,1,1)/sqrt(3) 旋转色相
  const vec3 k = vec3(0.57735027);
  float ca = cos(a), sa = sin(a);
  return c * ca + cross(k, c) * sa + k * dot(k, c) * (1.0 - ca);
}

void main() {
  vec2 uv = gl_FragCoord.xy / iResolution.xy;
  vec3 scene = texture(iChannel0, uv).rgb;
  vec3 bloom = texture(iChannel1, uv).rgb;

  // 提亮: 原始 Image 输出偏暗 (pow 1.6), 先拉回梦核的乳白亮度域
  scene = min(scene * 1.85 + 0.015, 3.0);

  // 动态色彩时钟: 两组互质频率 + 慢速相位, 永不形成固定循环
  float t1 = iTime * 0.10;
  float t2 = iTime * 0.043;
  float cT = iTime * 0.06;
  float luma = max(dot(scene, W), 0.0);
  float tn = 1.0 - exp(-luma * 1.15);

  // 流动雾气场: 域扭曲双层噪声 — 前景/中景/远景各自演化, 永不同步
  float nA = fnoise(uv * 2.1 + vec2(t1 * 0.34, -t1 * 0.21));
  float nB = fnoise(uv * 4.6 + vec2(-t2 * 0.52, t2 * 0.30) + 5.7);
  float nC = fnoise(uv * 1.2 + vec2(t2 * 0.20, t1 * 0.11) + 13.1);
  float n = mix(nA, nB, 0.35 + 0.30 * sin(t1 * 0.63 + nC * 4.0));

  // 频闪瞬间: 色相相位短暂偏移, 随后完全恢复
  float fShift = uFlash * (hash11(uFlashSeed) - 0.5) * 2.4;

  // 三组互不同步的漂移权重: 淡紫 / 青绿荧光 / 粉紫 / 乳白 随机重组
  float wp = 0.5 + 0.5 * sin(t1 * 1.65 + n * 6.2832 + uv.y * 2.2 + tn * 2.4 + fShift);
  float wg = 0.5 + 0.5 * sin(t2 * 2.35 + nB * 5.6 - uv.x * 1.8 + 2.1 + tn * 1.6 - fShift * 0.8);
  float wk = 0.5 + 0.5 * sin(t1 * 1.05 + nC * 4.6 - nA * 3.2 + 4.0 + fShift * 0.5);

  // 色彩风暴: 稀疏噪声阈值 — 局部色彩突然明显偏转 (连续渐变, 无跳色)
  float surge = smoothstep(0.60, 0.86, fnoise(uv * 1.35 + vec2(t1 * 0.16, -t2 * 0.10))) *
                smoothstep(0.30, 0.65, tn);
  wg += surge * 0.45 * sin(t1 * 2.6 + n * 7.0);
  wp += surge * 0.30 * sin(t2 * 2.1 + nA * 6.5);
  float wgc = clamp(wg, 0.0, 1.0), wpc = clamp(wp, 0.0, 1.0);

  // 亮度梯度 (各色标自身也在漂移): 深蓝紫/深青 -> 灰紫/青绿/淡紫/粉紫 -> 乳白/淡粉白
  vec3 deep = mix(vec3(0.050, 0.040, 0.150), vec3(0.024, 0.100, 0.115), wgc);
  deep = mix(deep, vec3(0.090, 0.050, 0.130), wpc * 0.4);
  vec3 mid = mix(mix(vec3(0.400, 0.360, 0.600), vec3(0.340, 0.560, 0.500), wgc),
                 mix(vec3(0.620, 0.520, 0.800), vec3(0.950, 0.800, 0.880), wpc),
                 0.30 + 0.65 * wk);
  vec3 hi = mix(vec3(0.965, 0.940, 0.995), vec3(0.880, 0.965, 0.935), wgc * 0.7);
  hi = mix(hi, vec3(1.000, 0.905, 0.945), wpc * 0.45);

  vec3 grad = mix(deep, mid, smoothstep(0.03, 0.48, tn));
  grad = mix(grad, hi, smoothstep(0.40, 0.90, tn));

  // 保留原画面明暗起伏作为结构, 抑制原色相
  vec3 chroma = scene - luma;
  vec3 col = grad + chroma * 0.42;

  // 荧光溢出: 强度与偏向随风暴/相位波动
  float acc = smoothstep(0.22, 0.85, tn) *
              (0.30 + 0.70 * (0.5 + 0.5 * sin(cT * 1.55 + nA * 5.2 + surge * 3.0)));
  col += vec3(0.06, 0.30, 0.14) * acc * wgc;
  col += vec3(0.24, 0.09, 0.21) * acc * (1.0 - wgc) * 0.85;

  // 色彩风暴区: 变化最剧烈处自发光增强
  col += (mid * 0.5 + 0.22) * surge * tn * 0.40;

  // 低饱和梦核基调 (饱和度轻微呼吸)
  float satV = 0.86 + 0.10 * sin(t1 * 0.9 + nB * 3.0);
  col = mix(vec3(dot(col, W)), col, satV);

  // 泛光: 染色 bloom, 风暴区明显增强, 色调跟随局部色彩
  vec3 bTint = mix(vec3(0.72, 1.00, 0.85), vec3(1.00, 0.82, 0.92), wpc);
  bTint = mix(bTint, vec3(0.86, 0.84, 1.00), wgc * 0.5);
  bTint = mix(bTint, mid * 1.25, surge * 0.45);
  col += bloom * uGlow * (1.0 + surge * 0.8) * bTint;

  // 微弱呼吸
  col *= 1.0 + 0.025 * sin(iTime * 0.35 + n * 2.0);

  // 频闪: 梦境过载 —— 手部扰动触发, 瞬间提亮 + 局部过曝 + 梦核色偏, 快速消退
  if (uFlash > 0.004) {
    vec2 fc = vec2(hash11(uFlashSeed + 1.0), hash11(uFlashSeed + 2.0));
    vec2 dd = (uv - fc) * vec2(iResolution.x / iResolution.y, 1.0);
    float local = uFlash * exp(-dot(dd, dd) * (4.0 + 7.0 * hash11(uFlashSeed + 3.0)));
    vec3 fshift = mix(vec3(1.08, 1.00, 1.14), vec3(0.94, 1.10, 1.04),
                      hash11(uFlashSeed + 4.0));
    col *= 1.0 + uFlash * 0.85 * fshift;                 // 全局瞬间提亮 + 冷暖色偏
    col += (bTint * 0.6 + 0.4) * local * uFlash * 1.5;   // 局部过曝光斑 (梦核染色)
    col += vec3(0.95, 0.93, 1.00) * local * uFlash * 0.30;
  }

  // 高光柔滚降: 过曝但不生硬
  col = col / (1.0 + max(col - vec3(0.80), vec3(0.0)) * 0.55);

  // 暗部底线: 深紫/深青, 不纯黑
  col = max(col, vec3(0.014, 0.011, 0.032));

  // 用户调节: 色温 / 亮度 / 对比度 / 饱和度 / 色相 (默认值下均不改变画面)
  col = max(col, vec3(0.0));
  col *= vec3(1.0 + 0.30 * uTemp, 1.0, 1.0 - 0.30 * uTemp);
  col *= uBright;
  col = (col - 0.5) * uContrast + 0.5;
  col = mix(vec3(dot(col, W)), max(col, vec3(0.0)), uSat);
  col = hueRotate(col, uHue);

  col += (hash12(gl_FragCoord.xy + fract(iTime) * 61.7) - 0.5) * (1.6 / 255.0);
  fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;

  const passes = {
    bufA: { src: HEADER + payload.common + payload.bufA + WRAPPER,  name: "Buffer A" },
    bufB: { src: HEADER + "uniform mat3 uHand;\nuniform float uSpinT;\n" + payload.common + payload.bufB + WRAPPER, name: "Buffer B" },
    image:{ src: HEADER + payload.common + payload.image + WRAPPER, name: "Image" },
    bright: { src: BRIGHT, name: "Bright" },
    blur: { src: BLUR, name: "Blur" },
    dream: { src: DREAM, name: "DreamGrade" },
  };

  function compile(type, srcStr, name) {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, srcStr);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      fail("=== " + name + " 编译失败 ===\n" + gl.getShaderInfoLog(sh));
      return null;
    }
    return sh;
  }
  function makeProgram(key) {
    const p = passes[key];
    const vs = compile(gl.VERTEX_SHADER, `#version 300 es
      void main() {
        vec2 v = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
        gl_Position = vec4(v * 2.0 - 1.0, 0.0, 1.0);
      }`, p.name + " vertex");
    const fs = compile(gl.FRAGMENT_SHADER, p.src, p.name);
    if (!vs || !fs) return null;
    const prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      fail("=== " + p.name + " 链接失败 ===\n" + gl.getProgramInfoLog(prog));
      return null;
    }
    const u = {};
    for (const n of ["iResolution","iTime","iTimeDelta","iFrameRate","iFrame",
                     "iMouse","iDate","iSampleRate","iChannel0","iChannel1",
                     "iChannel2","iChannel3","iChannelTime","iChannelResolution",
                     "uThresh","uDir","uGlow","uHand","uFlash","uFlashSeed","uSpinT",
                     "uHue","uSat","uTemp","uBright","uContrast"])
      u[n] = gl.getUniformLocation(prog, n);
    return { prog, u, name: p.name };
  }
  for (const k of Object.keys(passes)) { passes[k].impl = makeProgram(k); }
  if (Object.values(passes).some(p => !p.impl)) { fail("存在编译错误，已中止"); return; }

  // ---- full-screen VAO (gl_VertexID trick, no buffers) ----
  const vao = gl.createVertexArray();
  gl.bindVertexArray(vao);

  // ---- noise texture (embedded, 256x256 gray noise, mipmap + repeat, vflip) ----
  const noiseTex = gl.createTexture();
  const img = new Image();
  let noiseReady = false;
  img.onload = () => {
    gl.bindTexture(gl.TEXTURE_2D, noiseTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);   // sampler vflip = true
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    noiseReady = true;
  };
  img.src = payload.noise;

  // ---- 8-bit ping-pong buffers + float post targets ----
  const hasFloat = !!gl.getExtension("EXT_color_buffer_float");
  const IFMT = hasFloat ? gl.RGBA16F : gl.RGBA8;
  const ITYPE = hasFloat ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE;
  function makeTarget(w, h, float) {
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, float ? IFMT : gl.RGBA8, w, h, 0,
      gl.RGBA, float ? ITYPE : gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    return { tex, fbo, w, h };
  }
  const buffers = {
    bufA: { pair: null },
    bufB: { pair: null },
  };
  const rt = { scene: null, qA: null, qB: null };
  function ensureBuffers(w, h) {
    for (const k of Object.keys(buffers)) {
      const b = buffers[k];
      if (!b.pair || b.pair[0].w !== w || b.pair[0].h !== h) {
        if (b.pair) { b.pair.forEach(t => { gl.deleteTexture(t.tex); gl.deleteFramebuffer(t.fbo); }); }
        b.pair = [makeTarget(w, h, false), makeTarget(w, h, false)];
        b.i = 0;
      }
    }
    if (!rt.scene || rt.scene.w !== w || rt.scene.h !== h) {
      for (const k of ["scene", "qA", "qB"]) {
        if (rt[k]) { gl.deleteTexture(rt[k].tex); gl.deleteFramebuffer(rt[k].fbo); }
      }
      const qw = Math.max(1, w >> 2), qh = Math.max(1, h >> 2);
      rt.scene = makeTarget(w, h, true);
      rt.qA = makeTarget(qw, qh, true);
      rt.qB = makeTarget(qw, qh, true);
    }
  }

  // ---- sizing ----
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  function resize() {
    const w = Math.max(1, Math.floor(canvas.clientWidth * dpr));
    const h = Math.max(1, Math.floor(canvas.clientHeight * dpr));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w; canvas.height = h;
    }
    ensureBuffers(w, h);
  }
  window.addEventListener("resize", resize);
  resize();

  // ---- state ----
  let paused = false;
  let simTime = 0, spinPhase = 0, lastTick = performance.now();
  let speed = 2.5;   // 全局时间倍速: 相机飞行/旋转/光效相位统一加快
  let spinMul = 1.0; // 转动速度倍率: 仅作用于隧道旋转 (面板滑块可调)
  const params = { hue: 0, sat: 1, temp: 0, bright: 1, contrast: 1, glow: 1.45 }; // 面板可调参数
  let frame = 0;
  let mouse = [0, 0, 0, 0];
  canvas.addEventListener("mousedown", (e) => {
    const r = canvas.getBoundingClientRect();
    mouse = [e.clientX - r.left, canvas.clientHeight - (e.clientY - r.top), 0, 0];
    canvas.onmousemove = (e2) => {
      const r2 = canvas.getBoundingClientRect();
      mouse[2] = e2.clientX - r2.left;
      mouse[3] = canvas.clientHeight - (e2.clientY - r2.top);
    };
  });
  window.addEventListener("mouseup", () => { canvas.onmousemove = null; });
  window.addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLInputElement) return;   // 滑块聚焦时, 方向键留给面板
    if (e.code === "Space") {
      e.preventDefault();
      paused = !paused;
    } else if (e.key === "r" || e.key === "R") {
      simTime = 0; spinPhase = 0; lastTick = performance.now(); frame = 0; paused = false;
    } else if (e.key === "-" || e.key === "_") {
      speed = Math.max(0.5, speed - 0.5);
      syncSliders();
    } else if (e.key === "=" || e.key === "+") {
      speed = Math.min(8, speed + 0.5);
      syncSliders();
    } else if (e.key === "h" || e.key === "H") {
      handEnabled ? stopHand() : startHand();
    } else if (e.key === "c" || e.key === "C") {
      togglePanel();
    } else if (e.key === "f" || e.key === "F") {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen();
    }
  });

  // ---- 调节面板: 色彩 / 亮暗 / 速度 滑块 ----
  const spdEl = document.getElementById("spd");
  const panelBody = document.getElementById("panelBody");
  const sliderDefs = [
    { label: "色相",     min: -180, max: 180, step: 1,    def: 0,    fmt: v => (v > 0 ? "+" : "") + v.toFixed(0) + "°",
      get: () => params.hue,      set: v => params.hue = v },
    { label: "饱和度",   min: 0,    max: 2,   step: 0.01, def: 1,    fmt: v => v.toFixed(2),
      get: () => params.sat,      set: v => params.sat = v },
    { label: "色温",     min: -1,   max: 1,   step: 0.01, def: 0,    fmt: v => (v > 0 ? "+" : "") + v.toFixed(2),
      get: () => params.temp,     set: v => params.temp = v },
    { label: "亮度",     min: 0.2,  max: 2.5, step: 0.01, def: 1,    fmt: v => v.toFixed(2),
      get: () => params.bright,   set: v => params.bright = v },
    { label: "对比度",   min: 0.5,  max: 1.8, step: 0.01, def: 1,    fmt: v => v.toFixed(2),
      get: () => params.contrast, set: v => params.contrast = v },
    { label: "泛光",     min: 0,    max: 3,   step: 0.01, def: 1.45, fmt: v => v.toFixed(2),
      get: () => params.glow,     set: v => params.glow = v },
    { label: "整体速度", min: 0.5,  max: 8,   step: 0.1,  def: 2.5,  fmt: v => "×" + v.toFixed(1),
      get: () => speed,           set: v => speed = v },
    { label: "转动速度", min: 0,    max: 3,   step: 0.05, def: 1,    fmt: v => "×" + v.toFixed(2),
      get: () => spinMul,         set: v => spinMul = v },
  ];
  for (const d of sliderDefs) {
    const row = document.createElement("div"); row.className = "row";
    const lab = document.createElement("label"); lab.textContent = d.label;
    const inp = document.createElement("input");
    inp.type = "range"; inp.min = d.min; inp.max = d.max; inp.step = d.step; inp.value = d.def;
    inp.title = { "色相": "整体色相偏移", "饱和度": "色彩浓淡", "色温": "左冷右暖",
      "亮度": "画面明暗", "对比度": "明暗反差", "泛光": "辉光强度",
      "整体速度": "时间流速 (与 -/= 键同步)", "转动速度": "隧道旋转快慢" }[d.label] || "";
    const val = document.createElement("span"); val.className = "val"; val.textContent = d.fmt(d.def);
    inp.addEventListener("input", () => applySlider(d, +inp.value));
    row.append(lab, inp, val);
    panelBody.append(row);
    d.inp = inp; d.val = val;
  }
  const footRow = document.createElement("div"); footRow.className = "foot";
  const resetBtn = document.createElement("button"); resetBtn.textContent = "重置默认";
  resetBtn.addEventListener("click", () => {
    for (const d of sliderDefs) applySlider(d, d.def);
    resetBtn.blur();
  });
  footRow.append(resetBtn);
  panelBody.append(footRow);
  function applySlider(d, v) {
    d.set(v);
    d.inp.value = v;
    d.val.textContent = d.fmt(v);
    spdEl.textContent = speed.toFixed(1);
  }
  function syncSliders() {
    for (const d of sliderDefs) { d.inp.value = d.get(); d.val.textContent = d.fmt(d.get()); }
    spdEl.textContent = speed.toFixed(1);
  }
  const foldBtn = document.getElementById("panelFold");
  function togglePanel() {
    const hide = panelBody.style.display !== "none";
    panelBody.style.display = hide ? "none" : "";
    foldBtn.textContent = hide ? "＋" : "－";
  }
  foldBtn.addEventListener("click", () => { togglePanel(); foldBtn.blur(); });

  // ---- render ----
  let lastDt = 1 / 60;
  function advanceTime() {
    const now = performance.now();
    const dt = Math.min(0.1, (now - lastTick) / 1000);
    lastTick = now;
    lastDt = dt;
    if (!paused) {
      simTime += dt * speed;
      // 不规律转动: 多频非线性调制 — 忽快忽慢, 永不循环 (速率约 0.4x ~ 2.7x 附加波动)
      const w = 0.50 * Math.sin(simTime * 0.83) + 0.30 * Math.sin(simTime * 0.41 + 1.7)
              + 0.20 * Math.sin(simTime * 1.71 + 4.2) + 0.12 * Math.sin(simTime * 2.53 + 0.6);
      spinPhase += dt * speed * spinMul * (1.55 + w);
    }
    return simTime;
  }
  function shaderTime() { return simTime; }

  // ---- 手部扰动: 摄像头检测手的位置/移动, 干扰空间旋转 ----
  const camVideo = document.getElementById("cam");
  const handEl = document.getElementById("hand");
  const handMat = new Float32Array([1, 0, 0, 0, 1, 0, 0, 0, 1]);
  let handEnabled = false, handYaw = 0, handYawVel = 0;
  let handLastX = null, handLastSeen = -1e9;
  let handsSolver = null, handSendBusy = false, handLastSend = 0;
  function setHandMsg(m) { handEl.textContent = "手部: " + m; }

  function onHandResults(res) {
    const lms = res.multiHandLandmarks;
    const now = performance.now();
    if (lms && lms.length) {
      const lm = lms[0];
      let x = 0;
      for (const id of [0, 5, 9, 13, 17]) x += lm[id].x;   // 手掌中心
      x /= 5;
      if (handLastX !== null) {
        const dx = handLastX - x;            // 镜像直觉: 手向左移动为负
        handYawVel += dx * 11.0;             // 移动越快, 冲量越大
        handYawVel = Math.max(-1.2, Math.min(1.2, handYawVel));
      } else {
        triggerFlash();                      // 手出现在画面中的一瞬: 过载闪
      }
      handLastX = x; handLastSeen = now;
      setHandMsg("干扰中 ✋");
    } else {
      handLastX = null;
      setHandMsg(now - handLastSeen < 4000 ? "手离开…" : "未检测到手");
    }
  }

  async function startHand() {
    if (handEnabled) return;
    if (typeof Hands === "undefined") { setHandMsg("检测库未加载(需联网)"); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: "user" }
      });
      camVideo.srcObject = stream;
      await camVideo.play();
      handsSolver = new Hands({
        locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/${f}`
      });
      handsSolver.setOptions({ maxNumHands: 1, modelComplexity: 0,
        minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
      handsSolver.onResults(onHandResults);
      handEnabled = true;
      setHandMsg("等待手…");
      const pump = async () => {
        if (!handEnabled) return;
        const now = performance.now();
        if (!handSendBusy && camVideo.readyState >= 2 && now - handLastSend > 45) {
          handSendBusy = true; handLastSend = now;
          try { await handsSolver.send({ image: camVideo }); } catch (e) {}
          handSendBusy = false;
        }
        requestAnimationFrame(pump);
      };
      pump();
    } catch (e) {
      setHandMsg("摄像头不可用");
    }
  }
  function stopHand() {
    handEnabled = false;
    if (camVideo.srcObject) {
      camVideo.srcObject.getTracks().forEach(t => t.stop());
      camVideo.srcObject = null;
    }
    setHandMsg("已关闭");
  }

  function updateHand(dt) {
    // 惯性: 手停止后角速度衰减, 偏转缓慢归零, 平滑恢复原始旋转
    handYawVel *= Math.exp(-dt * 1.7);
    handYaw += handYawVel * dt;
    handYaw *= Math.exp(-dt * 0.55);
    handYaw = Math.max(-0.55, Math.min(0.55, handYaw));
    const c = Math.cos(handYaw), s = Math.sin(handYaw);
    handMat.set([c, 0, -s, 0, 1, 0, s, 0, c]);
  }

  // ---- 频闪: 手部扰动时随机触发的"梦境过载" ----
  let flash = 0, flashSeed = 0, flashNext = 1e9, flashEchoAt = 0, flashEchoAmp = 0;
  function triggerFlash() {
    flash = 0.55 + Math.random() * 0.45;      // 随机强度
    flashSeed = Math.random() * 100.0;        // 随机位置与色偏方向
  }
  function updateFlash(dt, now) {
    flash *= Math.exp(-dt * 13.0);            // 非常短的持续时间
    if (flash < 0.003) flash = 0;
    const seen = (now - handLastSeen) < 900;  // 只有手在画面中才可能触发
    if (seen) {
      if (flashNext > 1e8) flashNext = now + 700 + Math.random() * 2600;
      if (now >= flashNext) {
        triggerFlash();
        flashNext = now + 900 + Math.random() * 2600;   // 随机间隔, 无固定频率
        if (Math.random() < 0.35) {                     // 偶发更弱的回闪, 断续感
          flashEchoAt = now + 70 + Math.random() * 90;
          flashEchoAmp = flash * (0.35 + Math.random() * 0.3);
        }
      }
      if (flashEchoAt && now >= flashEchoAt) {
        flash = Math.max(flash, flashEchoAmp);
        flashEchoAt = 0;
      }
    } else {
      flashNext = 1e9; flashEchoAt = 0;
    }
  }
  startHand();   // 页面加载即请求摄像头权限; 拒绝或离线时优雅降级
  window.__HAND = {
    set vel(v) { handYawVel = v; },
    get vel() { return handYawVel; },
    get yaw() { return handYaw; },
    poke() { triggerFlash(); },   // 调试: 手动触发一次频闪
  };

  function runPass(p, target, units) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fbo : null);
    const w = target ? target.w : canvas.width;
    const h = target ? target.h : canvas.height;
    gl.viewport(0, 0, w, h);
    gl.useProgram(p.prog);
    const t = shaderTime();
    gl.uniform3f(p.u.iResolution, w, h, 1);
    gl.uniform1f(p.u.iTime, t);
    gl.uniform1f(p.u.iTimeDelta, 1 / 60);
    gl.uniform1f(p.u.iFrameRate, 60);
    gl.uniform1i(p.u.iFrame, frame);
    gl.uniform4fv(p.u.iMouse, mouse);
    const d = new Date();
    gl.uniform4f(p.u.iDate, d.getFullYear(), d.getMonth() + 1, d.getDate(),
      d.getHours() * 3600 + d.getMinutes() * 60 + d.getSeconds());
    gl.uniform1f(p.u.iSampleRate, 44100);
    if (p.u.iChannelTime) gl.uniform1fv(p.u.iChannelTime, [t, t, t, t]);
    if (p.u.iChannelResolution) gl.uniform3fv(p.u.iChannelResolution,
      [w, h, 1, 256, 256, 1, w, h, 1, w, h, 1]);

    for (let i = 0; i < 4; i++) {
      gl.activeTexture(gl.TEXTURE0 + i);
      gl.bindTexture(gl.TEXTURE_2D, units[i] ? units[i] : noiseTex);
      gl.uniform1i(p.u["iChannel" + i], i);
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  let fpsCount = 0, fpsLast = performance.now(), lastFrameAt = 0;
  function doFrame() {
    lastFrameAt = performance.now();
    fpsCount++;
    resize();
    const t = advanceTime();
    updateFlash(lastDt, performance.now());
    if (paused || !noiseReady) return;
    // Shadertoy order: buffers in list order (A -> B), then Image
    updateHand(lastDt);
    const A = buffers.bufA, B = buffers.bufB;
    A.i = 1 - A.i; runPass(passes.bufA.impl, A.pair[A.i], [null, null, null, null]);
    gl.useProgram(passes.bufB.impl.prog);
    gl.uniformMatrix3fv(passes.bufB.impl.u.uHand, false, handMat);
    gl.uniform1f(passes.bufB.impl.u.uSpinT, spinPhase - 1.0);
    B.i = 1 - B.i; runPass(passes.bufB.impl, B.pair[B.i],
      [null, noiseTex, null, A.pair[A.i].tex]);
    runPass(passes.image.impl, rt.scene, [B.pair[B.i].tex, null, null, null]);

    // dreamcore bloom: bright extract -> 1/4 res double gaussian
    const br = passes.bright.impl;
    gl.useProgram(br.prog);
    gl.uniform1f(br.u.uThresh, 0.34);
    runPass(br, rt.qA, [rt.scene.tex, null, null, null]);
    const bl = passes.blur.impl;
    gl.useProgram(bl.prog);
    const qw = rt.qA.w, qh = rt.qA.h;
    for (const r of [1.0, 2.0]) {
      gl.uniform2f(bl.u.uDir, 1.15 * r / qw, 0);
      runPass(bl, rt.qB, [rt.qA.tex, null, null, null]);
      gl.uniform2f(bl.u.uDir, 0, 1.15 * r / qh);
      runPass(bl, rt.qA, [rt.qB.tex, null, null, null]);
    }

    // flowing dreamcore grade + tinted glow
    const cp = passes.dream.impl;
    gl.useProgram(cp.prog);
    gl.uniform1f(cp.u.uGlow, params.glow);
    gl.uniform1f(cp.u.uHue, params.hue * Math.PI / 180);
    gl.uniform1f(cp.u.uSat, params.sat);
    gl.uniform1f(cp.u.uTemp, params.temp);
    gl.uniform1f(cp.u.uBright, params.bright);
    gl.uniform1f(cp.u.uContrast, params.contrast);
    gl.uniform1f(cp.u.uFlash, flash);
    gl.uniform1f(cp.u.uFlashSeed, flashSeed);
    runPass(cp, null, [rt.scene.tex, rt.qA.tex, null, null]);
    frame++;
  }
  function loop() { doFrame(); requestAnimationFrame(loop); }
  loop();
  // fallback: some hosts pause rAF even when visible (occluded webviews)
  setInterval(() => {
    if (performance.now() - lastFrameAt > 250) doFrame();
  }, 200);

  setInterval(() => {
    const now = performance.now();
    fpsEl.textContent = ((fpsCount * 1000) / (now - fpsLast)).toFixed(0);
    fpsCount = 0; fpsLast = now;
  }, 500);
})();
"""

html = html_head.replace("__PAYLOAD__", json.dumps(payload)) + runtime_js + html_tail

out = os.path.normpath(os.path.join(HERE, "..", "index.html"))
with open(out, "w") as f:
    f.write(html)
print("written", out, len(html), "chars")
