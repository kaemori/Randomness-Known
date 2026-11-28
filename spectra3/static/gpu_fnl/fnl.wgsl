<TABLES>

struct Params {
    width: u32,
    height: u32,
    seed: i32,
    ntype: i32,
    ftype: i32,
    octaves: i32,
    use_fmap: u32,
    freq: f32,
    lacunarity: f32,
    gain: f32,
    wstrength: f32,
    pingpong: f32,
    jitter: f32,
    bounding: f32,
};

@group(0) @binding(0) var<storage, read_write> outv: array<f32>;
@group(0) @binding(1) var<storage, read> fmap: array<f32>;
@group(0) @binding(2) var<storage, read> params: Params;

const PX: i32 = 501125321;
const PY: i32 = 1136930381;
const G2: f32 = 0.21132486540518713;

fn hash(s: i32, x: i32, y: i32) -> i32 {
    return (s ^ x ^ y) * 0x27d4eb2d;
}

fn valCoord(s: i32, x: i32, y: i32) -> f32 {
    var h = hash(s, x, y);
    h *= h;
    h ^= h << 19;
    return f32(h) * (1.0 / 2147483648.0);
}

fn gradCoord(s: i32, x: i32, y: i32, xd: f32, yd: f32) -> f32 {
    var h = hash(s, x, y);
    h ^= h >> 15;
    h &= 127 << 1;
    let index = u32(h);
    return xd * GRADIENTS_2D[index] + yd * GRADIENTS_2D[index | 1u];
}

fn simplex(s: i32, x: f32, y: f32) -> f32 {
    var i = i32(floor(x));
    var j = i32(floor(y));
    let xi = x - f32(i);
    let yi = y - f32(j);
    let t = (xi + yi) * G2;
    let x0 = xi - t;
    let y0 = yi - t;
    i *= PX;
    j *= PY;
    var n0 = 0.0;
    var n1 = 0.0;
    var n2 = 0.0;

    let a = 0.5 - x0 * x0 - y0 * y0;
    if (a > 0.0) {
        n0 = a * a * a * a * gradCoord(s, i, j, x0, y0);
    }

    let c = 2.0 * (1.0 - 2.0 * G2) * (1.0 / G2 - 2.0) * t
        + (-2.0 * (1.0 - 2.0 * G2) * (1.0 - 2.0 * G2) + a);
    if (c > 0.0) {
        let x2 = x0 + (2.0 * G2 - 1.0);
        let y2 = y0 + (2.0 * G2 - 1.0);
        n2 = c * c * c * c * gradCoord(s, i + PX, j + PY, x2, y2);
    }

    if (y0 > x0) {
        let x1 = x0 + G2;
        let y1 = y0 + (G2 - 1.0);
        let b = 0.5 - x1 * x1 - y1 * y1;
        if (b > 0.0) {
            n1 = b * b * b * b * gradCoord(s, i, j + PY, x1, y1);
        }
    } else {
        let x1 = x0 + (G2 - 1.0);
        let y1 = y0 + G2;
        let b = 0.5 - x1 * x1 - y1 * y1;
        if (b > 0.0) {
            n1 = b * b * b * b * gradCoord(s, i + PX, j, x1, y1);
        }
    }
    return (n0 + n1 + n2) * 99.83685446303647;
}

fn simplex2s(s: i32, x: f32, y: f32) -> f32 {
    var i = i32(floor(x));
    var j = i32(floor(y));
    let xi = x - f32(i);
    let yi = y - f32(j);
    let t = (xi + yi) * G2;
    let x0 = xi - t;
    let y0 = yi - t;
    i *= PX;
    j *= PY;
    let i1 = i + PX;
    let j1 = j + PY;

    const TW: f32 = 2.0 / 3.0;
    let a0 = TW - x0 * x0 - y0 * y0;
    var result = a0 * a0 * a0 * a0 * gradCoord(s, i, j, x0, y0);

    let a1 = 2.0 * (1.0 - 2.0 * G2) * (1.0 / G2 - 2.0) * t
        + (-2.0 * (1.0 - 2.0 * G2) * (1.0 - 2.0 * G2) + a0);
    let x1 = x0 - (1.0 - 2.0 * G2);
    let y1 = y0 - (1.0 - 2.0 * G2);
    result += a1 * a1 * a1 * a1 * gradCoord(s, i1, j1, x1, y1);

    let xmyi = xi - yi;
    var x2: f32;
    var y2: f32;
    var a2: f32;
    if (t > G2) {
        if (xi + xmyi > 1.0) {
            x2 = x0 + (3.0 * G2 - 2.0);
            y2 = y0 + (3.0 * G2 - 1.0);
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i + (PX << 1), j + PY, x2, y2);
            }
        } else {
            x2 = x0 + G2;
            y2 = y0 + (G2 - 1.0);
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i, j + PY, x2, y2);
            }
        }
        if (yi - xmyi > 1.0) {
            x2 = x0 + (3.0 * G2 - 1.0);
            y2 = y0 + (3.0 * G2 - 2.0);
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i + PX, j + bitcast<i32>(u32(PY) << 1u), x2, y2);
            }
        } else {
            x2 = x0 + (G2 - 1.0);
            y2 = y0 + G2;
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i + PX, j, x2, y2);
            }
        }
    } else {
        if (xi + xmyi < 0.0) {
            x2 = x0 + (1.0 - G2);
            y2 = y0 - G2;
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i - PX, j, x2, y2);
            }
        } else {
            x2 = x0 + (G2 - 1.0);
            y2 = y0 + G2;
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i + PX, j, x2, y2);
            }
        }
        if (yi < xmyi) {
            x2 = x0 - G2;
            y2 = y0 - (G2 - 1.0);
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i, j - PY, x2, y2);
            }
        } else {
            x2 = x0 + G2;
            y2 = y0 + (G2 - 1.0);
            a2 = TW - x2 * x2 - y2 * y2;
            if (a2 > 0.0) {
                result += a2 * a2 * a2 * a2 * gradCoord(s, i, j + PY, x2, y2);
            }
        }
    }
    return result * 18.24196194486065;
}

fn perlin(s: i32, x: f32, y: f32) -> f32 {
    var x0 = i32(floor(x));
    var y0 = i32(floor(y));
    let xd0 = x - f32(x0);
    let yd0 = y - f32(y0);
    let xd1 = xd0 - 1.0;
    let yd1 = yd0 - 1.0;
    let xs = xd0 * xd0 * xd0 * (xd0 * (xd0 * 6.0 - 15.0) + 10.0);
    let ys = yd0 * yd0 * yd0 * (yd0 * (yd0 * 6.0 - 15.0) + 10.0);
    x0 *= PX;
    y0 *= PY;
    let x1 = x0 + PX;
    let y1 = y0 + PY;
    let xf0 = mix(gradCoord(s, x0, y0, xd0, yd0), gradCoord(s, x1, y0, xd1, yd0), xs);
    let xf1 = mix(gradCoord(s, x0, y1, xd0, yd1), gradCoord(s, x1, y1, xd1, yd1), xs);
    return mix(xf0, xf1, ys) * 1.4247691104677813;
}

fn valueNoise(s: i32, x: f32, y: f32) -> f32 {
    var x0 = i32(floor(x));
    var y0 = i32(floor(y));
    var xs = x - f32(x0);
    var ys = y - f32(y0);
    xs = xs * xs * (3.0 - 2.0 * xs);
    ys = ys * ys * (3.0 - 2.0 * ys);
    x0 *= PX;
    y0 *= PY;
    let x1 = x0 + PX;
    let y1 = y0 + PY;
    return mix(
        mix(valCoord(s, x0, y0), valCoord(s, x1, y0), xs),
        mix(valCoord(s, x0, y1), valCoord(s, x1, y1), xs),
        ys,
    );
}

fn cellular(s: i32, x: f32, y: f32) -> f32 {
    let xr = i32(floor(x + 0.5));
    let yr = i32(floor(y + 0.5));
    var d0 = 1e30;
    let jit = 0.43701595 * params.jitter;
    for (var xi = xr - 1; xi <= xr + 1; xi++) {
        let xHash = xi * PX;
        for (var yi = yr - 1; yi <= yr + 1; yi++) {
            let yHash = yi * PY;
            let index = u32(hash(s, xHash, yHash) & (255 << 1));
            let offset = vec2<f32>(
                f32(xi) - x,
                f32(yi) - y,
            ) + vec2<f32>(RAND_VECS_2D[index], RAND_VECS_2D[index | 1u]) * jit;
            d0 = min(d0, dot(offset, offset));
        }
    }
    return d0 - 1.0;
}

fn gen(s: i32, x: f32, y: f32) -> f32 {
    if (params.ntype == 0) {
        return simplex(s, x, y);
    }
    if (params.ntype == 1) {
        return perlin(s, x, y);
    }
    if (params.ntype == 2) {
        return valueNoise(s, x, y);
    }
    if (params.ntype == 4) {
        return simplex2s(s, x, y);
    }
    return cellular(s, x, y);
}

fn pingP(t: f32) -> f32 {
    let remainder = t - f32(i32(t * 0.5)) * 2.0;
    return select(2.0 - remainder, remainder, remainder < 1.0);
}

fn fractal(xIn: f32, yIn: f32) -> f32 {
    if (params.ftype == 0) {
        return gen(params.seed, xIn, yIn);
    }
    var x = xIn;
    var y = yIn;
    var sum = 0.0;
    var amp = params.bounding;
    var s = params.seed;
    for (var octave = 0; octave < params.octaves; octave++) {
        var n = gen(s, x, y);
        s++;
        if (params.ftype == 1) {
            sum += n * amp;
            amp *= mix(1.0, min(n + 1.0, 2.0) * 0.5, params.wstrength);
        } else if (params.ftype == 2) {
            n = abs(n);
            sum += (n * -2.0 + 1.0) * amp;
            amp *= mix(1.0, 1.0 - n, params.wstrength);
        } else {
            n = pingP((n + 1.0) * params.pingpong);
            sum += (n - 0.5) * 2.0 * amp;
            amp *= mix(1.0, n, params.wstrength);
        }
        x *= params.lacunarity;
        y *= params.lacunarity;
        amp *= params.gain;
    }
    return sum;
}

@compute @workgroup_size(16, 16, 1)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let p = vec2<u32>(global_id.y, global_id.x);
    if (p.x >= params.width || p.y >= params.height) {
        return;
    }
    let index = p.x * params.height + p.y;
    var frequency = params.freq;
    if (params.use_fmap != 0u) {
        frequency = fmap[index];
    }
    var x = f32(p.x) * frequency;
    var y = f32(p.y) * frequency;
    if (params.ntype == 0 || params.ntype == 4) {
        let skew = (x + y) * 0.3660254037844386;
        x += skew;
        y += skew;
    }
    outv[index] = fractal(x, y);
}