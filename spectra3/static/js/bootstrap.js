async function initPyodideApp() {
    const loaderTag = document.getElementById("py-loader");
    const indexURL = loaderTag.dataset.indexUrl;
    const entryScript = loaderTag.dataset.entryScript;
    const pkgUrl = loaderTag.dataset.pkgUrl;

    const toolsFiles = ["liqfiller.py"];
    const shimFiles = [
        "__init__.py",
        "fast_noise_lite.py",
        "generation.py",
        "run_settings.py",
        "runtime.py",
        "state.py",
        "unity.py",
        "unity_random.py",
        "vectors.py",
    ];

    const [
        pyodide,
        pkgRes,
        structuresRes,
        mainRes,
        gpuFnlRes,
        toolsResponses,
        shimResponses,
    ] = await Promise.all([
        loadPyodide({ indexURL }),
        fetch(pkgUrl),
        fetch("/static/py/structures.pkg"),
        fetch(entryScript),
        fetch("/static/py/gpu_fnl.py"),
        Promise.all(
            toolsFiles.map((file) => fetch(`/static/py/tools/${file}`)),
        ),
        Promise.all(
            shimFiles.map((file) =>
                fetch(`/static/py/csharpshims/${file}`),
            ),
        ),
    ]);

    for (const [name, response] of [
        ["terrain package", pkgRes],
        ["structure package", structuresRes],
        ["Python entry script", mainRes],
        ["GPU noise shim", gpuFnlRes],
        ...toolsResponses.map((response, i) => [`tool ${toolsFiles[i]}`, response]),
        ...shimResponses.map((response, i) => [`shim ${shimFiles[i]}`, response]),
    ]) {
        if (!response.ok) {
            throw new Error(`Could not load ${name}: HTTP ${response.status}`);
        }
    }

    const pkgBytes = new Uint8Array(await pkgRes.arrayBuffer());
    pyodide.FS.writeFile("/home/pyodide/terrgen.pkg", pkgBytes);
    pyodide.FS.writeFile(
        "/home/pyodide/structures.pkg",
        new Uint8Array(await structuresRes.arrayBuffer()),
    );
    pyodide.FS.writeFile("/home/pyodide/gpu_fnl.py", await gpuFnlRes.text());

    pyodide.FS.mkdirTree("/home/pyodide/tools");
    for (let i = 0; i < toolsFiles.length; i++) {
        const fileCode = await toolsResponses[i].text();
        pyodide.FS.writeFile(`/home/pyodide/tools/${toolsFiles[i]}`, fileCode);
    }

    pyodide.FS.mkdirTree("/home/pyodide/csharpshims");
    for (let i = 0; i < shimFiles.length; i++) {
        pyodide.FS.writeFile(
            `/home/pyodide/csharpshims/${shimFiles[i]}`,
            await shimResponses[i].text(),
        );
    }

    await pyodide.loadPackage("numpy");
    await pyodide.loadPackage("scipy");
    await pyodide.runPythonAsync(await mainRes.text());
}

initPyodideApp().catch((error) => {
    const output = document.getElementById("output");
    if (output) {
        output.innerText = `Initialization failed: ${error.message}`;
    }
    console.error(error);
});
