async function initPyodideApp() {
    const loaderTag = document.getElementById("py-loader");
    const indexURL = loaderTag.dataset.indexUrl;
    const entryScript = loaderTag.dataset.entryScript;
    const pkgUrl = loaderTag.dataset.pkgUrl;

    const astoolsFiles = ["splitter.py"];
    const toolsFiles = ["liqfiller.py"];

    const [
        pyodide,
        pkgRes,
        mainRes,
        gpuFnlRes,
        astoolsResponses,
        toolsResponses,
    ] = await Promise.all([
        loadPyodide({ indexURL }),
        fetch(pkgUrl),
        fetch(entryScript),
        fetch("/static/py/gpu_fnl.py"),
        Promise.all(
            astoolsFiles.map((file) => fetch(`/static/py/astools/${file}`)),
        ),
        Promise.all(
            toolsFiles.map((file) => fetch(`/static/py/tools/${file}`)),
        ),
    ]);

    const pkgBytes = new Uint8Array(await pkgRes.arrayBuffer());
    pyodide.FS.writeFile("/home/pyodide/terrgen.pkg", pkgBytes);
    pyodide.FS.writeFile("/home/pyodide/gpu_fnl.py", await gpuFnlRes.text());

    pyodide.FS.mkdirTree("/home/pyodide/astools");
    for (let i = 0; i < astoolsFiles.length; i++) {
        const fileCode = await astoolsResponses[i].text();
        pyodide.FS.writeFile(
            `/home/pyodide/astools/${astoolsFiles[i]}`,
            fileCode,
        );
    }

    pyodide.FS.mkdirTree("/home/pyodide/tools");
    for (let i = 0; i < toolsFiles.length; i++) {
        const fileCode = await toolsResponses[i].text();
        pyodide.FS.writeFile(`/home/pyodide/tools/${toolsFiles[i]}`, fileCode);
    }

    await pyodide.loadPackage("numpy");
    await pyodide.loadPackage("scipy");
    await pyodide.runPythonAsync(await mainRes.text());
}

initPyodideApp();
