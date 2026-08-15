<script lang="ts">
  import { onMount } from "svelte";

  type RenderState = "initializing" | "running" | "paused" | "static" | "unavailable" | "lost";

  let canvas: HTMLCanvasElement;
  let renderState: RenderState = $state("initializing");

  const frameIntervalMs = 500;

  const vertexShaderSource = `#version 300 es
precision mediump float;

in vec2 aPosition;

void main() {
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

  const fragmentShaderSource = `#version 300 es
precision highp float;

out vec4 outColor;

uniform vec2 uResolution;
uniform float uTime;

vec3 permute(vec3 value) {
  return mod(((value * 34.0) + 1.0) * value, 289.0);
}

float noise2D(vec2 value) {
  const vec4 C = vec4(
    0.211324865405187,
    0.366025403784439,
    -0.577350269189626,
    0.024390243902439
  );

  vec2 cell = floor(value + dot(value, C.yy));
  vec2 origin = value - cell + dot(cell, C.xx);
  vec2 corner = origin.x > origin.y ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 offsets = origin.xyxy + C.xxzz;
  offsets.xy -= corner;

  cell = mod(cell, 289.0);
  vec3 permutation = permute(
    permute(cell.y + vec3(0.0, corner.y, 1.0)) +
    cell.x + vec3(0.0, corner.x, 1.0)
  );

  vec3 weight = max(
    0.5 - vec3(
      dot(origin, origin),
      dot(offsets.xy, offsets.xy),
      dot(offsets.zw, offsets.zw)
    ),
    0.0
  );
  weight *= weight;
  weight *= weight;

  vec3 gradient = 2.0 * fract(permutation * C.www) - 1.0;
  vec3 height = abs(gradient) - 0.5;
  vec3 rounded = floor(gradient + 0.5);
  vec3 remainder = gradient - rounded;
  weight *= 1.792843 - 0.853734 * (remainder * remainder + height * height);

  vec3 contribution;
  contribution.x = remainder.x * origin.x + height.x * origin.y;
  contribution.yz = remainder.yz * offsets.xz + height.yz * offsets.yw;
  return 130.0 * dot(weight, contribution);
}

float fbm(vec2 point) {
  float value = 0.0;
  float amplitude = 0.5;
  float frequency = 1.0;

  for (int octave = 0; octave < 4; octave++) {
    value += amplitude * noise2D(point * frequency);
    frequency *= 2.0;
    amplitude *= 0.5;
  }

  return value;
}

void main() {
  vec2 uv = (gl_FragCoord.xy / uResolution) * 2.0 - 1.0;
  uv.x *= uResolution.x / uResolution.y;
  uv *= 0.72;

  float time = uTime * 0.08;
  float waveAmplitude = 0.12 + 0.035 * noise2D(vec2(time, 17.3));
  uv += vec2(
    waveAmplitude * sin(uv.y * 2.8 + time),
    waveAmplitude * sin(uv.x * 2.8 - time)
  );

  float radius = length(uv);
  float angle = atan(uv.y, uv.x);
  float swirl = 0.32 * (1.0 - smoothstep(0.0, 1.35, radius));
  angle += swirl * sin(time * 1.4 + radius * 2.4);
  uv = vec2(cos(angle), sin(angle)) * radius;

  float noiseValue = clamp(0.5 * (fbm(uv + vec2(time * 0.16, 0.0)) + 1.0), 0.0, 1.0);
  float signal = smoothstep(0.30, 0.92, noiseValue);

  vec3 black = vec3(0.0, 0.002, 0.004);
  vec3 deepBlue = vec3(0.0, 0.06, 0.11);
  vec3 mutedCyan = vec3(0.0, 0.22, 0.26);
  vec3 color = mix(black, deepBlue, signal);
  color = mix(color, mutedCyan, smoothstep(0.76, 1.0, signal) * 0.28);

  float alpha = smoothstep(0.20, 0.94, signal) * 0.40;
  outColor = vec4(color, alpha);
}`;

  function compileShader(
    gl: WebGL2RenderingContext,
    type: number,
    source: string,
  ): WebGLShader | null {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
    gl.deleteShader(shader);
    return null;
  }

  function createProgram(gl: WebGL2RenderingContext): WebGLProgram | null {
    const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
    const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);
    if (!vertexShader || !fragmentShader) {
      if (vertexShader) gl.deleteShader(vertexShader);
      if (fragmentShader) gl.deleteShader(fragmentShader);
      return null;
    }

    const program = gl.createProgram();
    if (!program) {
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
      return null;
    }

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    if (gl.getProgramParameter(program, gl.LINK_STATUS)) return program;
    gl.deleteProgram(program);
    return null;
  }

  onMount(() => {
    const gl = canvas.getContext("webgl2", {
      alpha: true,
      antialias: false,
      depth: false,
      powerPreference: "low-power",
      premultipliedAlpha: false,
      stencil: false,
    });
    if (!gl) {
      renderState = "unavailable";
      return;
    }

    const program = createProgram(gl);
    if (!program) {
      renderState = "unavailable";
      return;
    }

    const position = gl.getAttribLocation(program, "aPosition");
    const resolution = gl.getUniformLocation(program, "uResolution");
    const time = gl.getUniformLocation(program, "uTime");
    const vao = gl.createVertexArray();
    const buffer = gl.createBuffer();
    if (position < 0 || !resolution || !time || !vao || !buffer) {
      if (vao) gl.deleteVertexArray(vao);
      if (buffer) gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      renderState = "unavailable";
      return;
    }

    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW,
    );
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    gl.clearColor(0, 0, 0, 0);

    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const startTime = performance.now();
    let animationFrame = 0;
    let animationTimer = 0;
    let contextLost = false;

    const resize = () => {
      const pixelRatio = 0.5;
      const width = Math.max(1, Math.round(canvas.clientWidth * pixelRatio));
      const height = Math.max(1, Math.round(canvas.clientHeight * pixelRatio));
      if (canvas.width === width && canvas.height === height) return;
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
    };

    const draw = (timestamp: number) => {
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(program);
      gl.bindVertexArray(vao);
      gl.uniform2f(resolution, canvas.width, canvas.height);
      gl.uniform1f(time, (timestamp - startTime) / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    };

    const stop = () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
      if (animationTimer) clearTimeout(animationTimer);
      animationFrame = 0;
      animationTimer = 0;
    };

    const animate = (timestamp: number) => {
      animationFrame = 0;
      if (contextLost || motionPreference.matches || document.hidden) return;
      draw(timestamp);
      animationTimer = window.setTimeout(() => {
        animationTimer = 0;
        animationFrame = requestAnimationFrame(animate);
      }, frameIntervalMs);
    };

    const syncAnimation = () => {
      stop();
      if (contextLost) return;
      if (motionPreference.matches) {
        draw(startTime);
        renderState = "static";
        return;
      }
      if (document.hidden) {
        renderState = "paused";
        return;
      }
      renderState = "running";
      const timestamp = performance.now();
      draw(timestamp);
      animationTimer = window.setTimeout(() => {
        animationTimer = 0;
        animationFrame = requestAnimationFrame(animate);
      }, frameIntervalMs);
    };

    const handleResize = () => {
      resize();
      if (motionPreference.matches) draw(startTime);
    };
    const handleContextLost = () => {
      contextLost = true;
      stop();
      renderState = "lost";
    };

    window.addEventListener("resize", handleResize, { passive: true });
    document.addEventListener("visibilitychange", syncAnimation);
    motionPreference.addEventListener("change", syncAnimation);
    canvas.addEventListener("webglcontextlost", handleContextLost);
    resize();
    syncAnimation();

    return () => {
      contextLost = true;
      stop();
      window.removeEventListener("resize", handleResize);
      document.removeEventListener("visibilitychange", syncAnimation);
      motionPreference.removeEventListener("change", syncAnimation);
      canvas.removeEventListener("webglcontextlost", handleContextLost);
      gl.deleteBuffer(buffer);
      gl.deleteVertexArray(vao);
      gl.deleteProgram(program);
    };
  });
</script>

<canvas
  bind:this={canvas}
  aria-hidden="true"
  data-render-state={renderState}
  data-slot="homepage-mesh-background"
  hidden={renderState === "unavailable"}
></canvas>

<style>
  canvas {
    position: fixed;
    z-index: 0;
    inset: 0;
    display: block;
    width: 100%;
    height: 100%;
    opacity: 0.78;
    pointer-events: none;
  }

  canvas[hidden] { display: none; }
</style>
