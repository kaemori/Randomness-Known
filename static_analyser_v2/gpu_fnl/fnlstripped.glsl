#version 430
<TABLES>
layout(local_size_x=16, local_size_y=16) in;
layout(std430, binding=0) writeonly buffer Out  { float outv[]; };
layout(std430, binding=1) readonly  buffer FMap { float fmap[]; };

uniform ivec2 size;
uniform int   seed, ntype, ftype, octaves;
uniform bool  use_fmap;
uniform float freq, lacunarity, gain, wstrength, pingpong, jitter, bounding;

const int PX = 501125321, PY = 1136930381;
const float G2 = 0.21132486540518713;

int hash(int s, int x, int y) { return (s ^ x ^ y) * 0x27d4eb2d; }

float valCoord(int s, int x, int y) {
    int h = hash(s, x, y);
    h *= h; h ^= h << 19;
    return float(h) * (1.0 / 2147483648.0);
}

float gradCoord(int s, int x, int y, float xd, float yd) {
    int h = hash(s, x, y);
    h ^= h >> 15;
    h &= 127 << 1;
    return xd * GRADIENTS_2D[h] + yd * GRADIENTS_2D[h | 1];
}

float simplex(int s, float x, float y) {
    int i = int(floor(x)), j = int(floor(y));
    float xi = x - float(i), yi = y - float(j);
    float t = (xi + yi) * G2, x0 = xi - t, y0 = yi - t;
    i *= PX; j *= PY;
    float n0 = 0.0, n1 = 0.0, n2 = 0.0;

    float a = 0.5 - x0*x0 - y0*y0;
    if (a > 0.0) n0 = a*a*a*a * gradCoord(s, i, j, x0, y0);

    float c = 2.0*(1.0-2.0*G2)*(1.0/G2-2.0)*t + (-2.0*(1.0-2.0*G2)*(1.0-2.0*G2) + a);
    if (c > 0.0) {
        float x2 = x0 + (2.0*G2 - 1.0), y2 = y0 + (2.0*G2 - 1.0);
        n2 = c*c*c*c * gradCoord(s, i + PX, j + PY, x2, y2);
    }
    if (y0 > x0) {
        float x1 = x0 + G2, y1 = y0 + (G2 - 1.0);
        float b = 0.5 - x1*x1 - y1*y1;
        if (b > 0.0) n1 = b*b*b*b * gradCoord(s, i, j + PY, x1, y1);
    } else {
        float x1 = x0 + (G2 - 1.0), y1 = y0 + G2;
        float b = 0.5 - x1*x1 - y1*y1;
        if (b > 0.0) n1 = b*b*b*b * gradCoord(s, i + PX, j, x1, y1);
    }
    return (n0 + n1 + n2) * 99.83685446303647;
}

float perlin(int s, float x, float y) {
    int x0 = int(floor(x)), y0 = int(floor(y));
    float xd0 = x - float(x0), yd0 = y - float(y0), xd1 = xd0 - 1.0, yd1 = yd0 - 1.0;
    float xs = xd0*xd0*xd0*(xd0*(xd0*6.0-15.0)+10.0);
    float ys = yd0*yd0*yd0*(yd0*(yd0*6.0-15.0)+10.0);
    x0 *= PX; y0 *= PY;
    int x1 = x0 + PX, y1 = y0 + PY;
    float xf0 = mix(gradCoord(s,x0,y0,xd0,yd0), gradCoord(s,x1,y0,xd1,yd0), xs);
    float xf1 = mix(gradCoord(s,x0,y1,xd0,yd1), gradCoord(s,x1,y1,xd1,yd1), xs);
    return mix(xf0, xf1, ys) * 1.4247691104677813;
}

float value(int s, float x, float y) {
    int x0 = int(floor(x)), y0 = int(floor(y));
    float xs = x - float(x0), ys = y - float(y0);
    xs = xs*xs*(3.0-2.0*xs); ys = ys*ys*(3.0-2.0*ys);
    x0 *= PX; y0 *= PY;
    int x1 = x0 + PX, y1 = y0 + PY;
    return mix(mix(valCoord(s,x0,y0), valCoord(s,x1,y0), xs),
               mix(valCoord(s,x0,y1), valCoord(s,x1,y1), xs), ys);
}

float cellular(int s, float x, float y) {
    int xr = int(floor(x + 0.5)), yr = int(floor(y + 0.5));
    float d0 = 1e30, jit = 0.43701595 * jitter;
    for (int xi = xr-1; xi <= xr+1; xi++)
    {
        int xHash = xi * PX;
        for (int yi = yr-1; yi <= yr+1; yi++) {
            int yHash = yi * PY;
            int idx = hash(s, xHash, yHash) & (255 << 1);
            vec2 v = vec2(float(xi) - x, float(yi) - y)
                   + vec2(RAND_VECS_2D[idx], RAND_VECS_2D[idx | 1]) * jit;
            d0 = min(d0, dot(v, v));
        }
    }
    return d0 - 1.0;
}

float gen(int s, float x, float y) {
    if (ntype == 0) return simplex(s, x, y);
    if (ntype == 1) return perlin(s, x, y);
    if (ntype == 2) return value(s, x, y);
    return cellular(s, x, y);
}

float pingP(float t) { t -= float(int(t * 0.5)) * 2.0; return t < 1.0 ? t : 2.0 - t; }

float fractal(float x, float y) {
    if (ftype == 0) return gen(seed, x, y);
    float sum = 0.0, amp = bounding;
    int s = seed;
    for (int o = 0; o < octaves; o++) {
        float n = gen(s++, x, y);
        if (ftype == 1) {
            sum += n * amp; amp *= mix(1.0, min(n + 1.0, 2.0) * 0.5, wstrength);
        } else if (ftype == 2) {
            n = abs(n); sum += (n * -2.0 + 1.0) * amp; amp *= mix(1.0, 1.0 - n, wstrength);
        } else {
            n = pingP((n + 1.0) * pingpong); sum += (n - 0.5) * 2.0 * amp; amp *= mix(1.0, n, wstrength);
        }
        x *= lacunarity; y *= lacunarity; amp *= gain;
    }
    return sum;
}

void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.yx);
    if (p.x >= size.x || p.y >= size.y) return;
    int idx = p.x * size.y + p.y;
    float f = use_fmap ? fmap[idx] : freq;
    float x = float(p.x) * f, y = float(p.y) * f;
    if (ntype == 0) { float t = (x + y) * 0.3660254037844386; x += t; y += t; }
    outv[idx] = fractal(x, y);
}
