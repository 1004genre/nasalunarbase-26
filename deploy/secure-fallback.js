// This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
// On an address that is not secure (http and not localhost), a browser does not give a page the
// function crypto.subtle. The page uses that function for one job only: SHA-256, to check that its
// data files belong together. This file supplies SHA-256 where the browser does not, so that the
// checks stay on. On a secure address this file does nothing.
(() => {
  if (!globalThis.crypto || globalThis.crypto.subtle) return;

  const primes = [];
  for (let n = 2; primes.length < 64; n++) if (primes.every((p) => n % p)) primes.push(n);
  const fraction = (x) => ((x - Math.floor(x)) * 4294967296) >>> 0;
  const K = Uint32Array.from(primes, (p) => fraction(Math.cbrt(p)));
  const START = primes.slice(0, 8).map((p) => fraction(Math.sqrt(p)));
  const turn = (x, n) => (x >>> n) | (x << (32 - n));

  function sha256(bytes) {
    const bits = bytes.length * 8;
    const total = (((bytes.length + 8) >> 6) + 1) << 6;
    const data = new Uint8Array(total);
    data.set(bytes);
    data[bytes.length] = 0x80;
    const view = new DataView(data.buffer);
    view.setUint32(total - 8, Math.floor(bits / 4294967296));
    view.setUint32(total - 4, bits >>> 0);
    const h = Uint32Array.from(START);
    const w = new Uint32Array(64);
    for (let block = 0; block < total; block += 64) {
      for (let i = 0; i < 16; i++) w[i] = view.getUint32(block + i * 4);
      for (let i = 16; i < 64; i++) {
        const s0 = turn(w[i - 15], 7) ^ turn(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        const s1 = turn(w[i - 2], 17) ^ turn(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, k] = h;
      for (let i = 0; i < 64; i++) {
        const s1 = turn(e, 6) ^ turn(e, 11) ^ turn(e, 25);
        const t1 = (k + s1 + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0;
        const s0 = turn(a, 2) ^ turn(a, 13) ^ turn(a, 22);
        const t2 = (s0 + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        k = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += k;
    }
    const out = new DataView(new ArrayBuffer(32));
    h.forEach((value, i) => out.setUint32(i * 4, value));
    return out.buffer;
  }

  const subtle = {
    async digest(algorithm, data) {
      const name = typeof algorithm === 'string' ? algorithm : algorithm?.name;
      if (name !== 'SHA-256') throw new Error('This address is not secure. Only SHA-256 is available.');
      const bytes = data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      return sha256(bytes);
    },
  };
  try { Object.defineProperty(globalThis.crypto, 'subtle', { value: subtle, configurable: true }); } catch { /* the checks stay off */ }
  if (typeof module !== 'undefined') module.exports = { sha256 };
})();
