RUN_PYTHON_CODE_TOOL_DESCRIPTION = """
Run Python code in an isolated sandbox for data analysis and plotting.
Sandbox globals: INPUT_DIR=/workspace/input, OUTPUT_DIR=/workspace/output, ATTACHMENTS, load_dataframe(path, **kwargs).
Attachment filenames in sandbox usually match attachment filenames (e.g. data.csv -> /workspace/input/data.csv).
If duplicate names exist, sandbox may assign prefixed fallback names like 01_data.csv to avoid collisions.
The sandbox process writes artifacts from /workspace/output (its working directory). Only write plot files in here and no json or csv outputs unless explicitly asked by user.
The tool mounts all attachments linked to the current conversation automatically.
load_dataframe handles csv/json/excel/txt/text-like files and common encodings (utf-8, utf-8-sig, utf-16, latin-1) with kwargs passthrough.
For plots, call plt.savefig('plot.png') or save files under OUTPUT_DIR so artifacts are returned.
Do not use any external or environment-specific plotting styles, themes, or style presets (e.g., plt.style.use(...), seaborn style names, custom .mplstyle files, URLs).
Use only default matplotlib/seaborn behavior and standard, in-scope packages and APIs available in this sandbox.
Available libraries include pandas, matplotlib, seaborn, numpy and openpyxl.
Args: code, description (optional).
""".strip()
