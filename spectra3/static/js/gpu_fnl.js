(() => {
    const shaderUrl = "/static/gpu_fnl/fnl.wgsl";
    const tablesUrl = "/static/gpu_fnl/tables.txt";

    let devicePromise;
    let pipelinePromise;

    function toWgslTables(source) {
        return source
            .replace(
                /const float ([A-Z0-9_]+)\[(\d+)\]\s*=\s*\{/g,
                "const $1: array<f32, $2> = array<f32, $2>(",
            )
            .replace(/};/g, ");")
            .replace(/(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)f\b/g, "$1");
    }

    async function getDevice() {
        if (!navigator.gpu) {
            throw new Error("WebGPU is not available in this browser.");
        }
        if (!devicePromise) {
            devicePromise = (async () => {
                const adapter = await navigator.gpu.requestAdapter();
                if (!adapter) {
                    throw new Error("No WebGPU adapter is available.");
                }
                return adapter.requestDevice();
            })();
        }
        return devicePromise;
    }

    async function getPipeline(device) {
        if (!pipelinePromise) {
            pipelinePromise = (async () => {
                const [shaderResponse, tablesResponse] = await Promise.all([
                    fetch(shaderUrl),
                    fetch(tablesUrl),
                ]);
                if (!shaderResponse.ok || !tablesResponse.ok) {
                    throw new Error(
                        "Could not load the GPU noise shader or tables.",
                    );
                }
                const shaderTemplate = await shaderResponse.text();
                const tables = toWgslTables(await tablesResponse.text());
                const shaderModule = device.createShaderModule({
                    code: shaderTemplate.replace("<TABLES>", tables),
                });
                const info = await shaderModule.getCompilationInfo();
                const errors = info.messages.filter(
                    (message) => message.type === "error",
                );
                if (errors.length) {
                    throw new Error(
                        errors.map((message) => message.message).join("\n"),
                    );
                }
                return device.createComputePipelineAsync({
                    layout: "auto",
                    compute: { module: shaderModule, entryPoint: "main" },
                });
            })();
        }
        return pipelinePromise;
    }

    async function noise(options) {
        const {
            width,
            height,
            seed,
            type = 0,
            freq = 0.01,
            fractal = 0,
            octaves = 3,
            lacunarity = 2.0,
            gain = 0.5,
            weighted = 0.0,
            pingpong = 2.0,
            jitter = 1.0,
            frequencyMap = null,
        } = options;

        if (
            !Number.isInteger(width) ||
            width <= 0 ||
            !Number.isInteger(height) ||
            height <= 0
        ) {
            throw new RangeError("width and height must be positive integers.");
        }

        const device = await getDevice();
        const pipeline = await getPipeline(device);
        const outputBytes = width * height * Float32Array.BYTES_PER_ELEMENT;
        const output = device.createBuffer({
            size: outputBytes,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
        });
        const readback = device.createBuffer({
            size: outputBytes,
            usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
        });
        const frequencyData =
            frequencyMap === null ? null : Float32Array.from(frequencyMap);
        const frequencyBuffer = device.createBuffer({
            size: frequencyData ? frequencyData.byteLength : 4,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
        });
        const paramsBuffer = device.createBuffer({
            size: 56,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
        });
        const params = new ArrayBuffer(56);
        const view = new DataView(params);
        view.setUint32(0, width, true);
        view.setUint32(4, height, true);
        view.setInt32(8, seed, true);
        view.setInt32(12, type, true);
        view.setInt32(16, fractal, true);
        view.setInt32(20, octaves, true);
        view.setUint32(24, frequencyData ? 1 : 0, true);
        view.setFloat32(28, frequencyData ? 0 : Number(freq), true);
        view.setFloat32(32, lacunarity, true);
        view.setFloat32(36, gain, true);
        view.setFloat32(40, weighted, true);
        view.setFloat32(44, pingpong, true);
        view.setFloat32(48, jitter, true);
        const absoluteGain = Math.abs(gain);
        const total =
            octaves <= 1
                ? 1
                : absoluteGain === 1
                  ? octaves
                  : (1 - absoluteGain ** octaves) / (1 - absoluteGain);
        view.setFloat32(52, 1 / total, true);

        try {
            if (frequencyData) {
                if (frequencyData.length !== width * height) {
                    throw new RangeError(
                        "frequencyMap must contain width * height values.",
                    );
                }
                device.queue.writeBuffer(frequencyBuffer, 0, frequencyData);
            }
            device.queue.writeBuffer(paramsBuffer, 0, params);
            const bindGroup = device.createBindGroup({
                layout: pipeline.getBindGroupLayout(0),
                entries: [
                    { binding: 0, resource: { buffer: output } },
                    { binding: 1, resource: { buffer: frequencyBuffer } },
                    { binding: 2, resource: { buffer: paramsBuffer } },
                ],
            });
            const encoder = device.createCommandEncoder();
            const pass = encoder.beginComputePass();
            pass.setPipeline(pipeline);
            pass.setBindGroup(0, bindGroup);
            pass.dispatchWorkgroups(
                Math.ceil(height / 16),
                Math.ceil(width / 16),
            );
            pass.end();
            encoder.copyBufferToBuffer(output, 0, readback, 0, outputBytes);
            device.queue.submit([encoder.finish()]);
            await readback.mapAsync(GPUMapMode.READ);
            const result = new Float32Array(readback.getMappedRange().slice(0));
            readback.unmap();
            return result;
        } finally {
            output.destroy();
            readback.destroy();
            frequencyBuffer.destroy();
            paramsBuffer.destroy();
        }
    }

    globalThis.gpuFnl = { noise };
})();
