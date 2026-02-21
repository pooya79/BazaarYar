RUN_PYTHON_CODE_TOOL_DESCRIPTION = """
Run Python in an isolated sandbox for data analysis and plotting. Use this tool for attachment analysis; do not provide Python code for the user to execute manually.

Sandbox environment:
INPUT_DIR=/workspace/input
OUTPUT_DIR=/workspace/output
ATTACHMENTS
load_dataframe(path, **kwargs)

Attachments are automatically mounted. Filenames usually match their original names (e.g., data.csv → /workspace/input/data.csv). If duplicates exist, prefixed names such as 01_data.csv may be assigned. Always select paths from available attachment filenames and use load_dataframe for csv/json/excel/txt files with encoding handled automatically.

Session behavior:
If the sandbox session is alive, variables and imports persist between user messages. Do not re-import or redefine objects unless necessary. If the session is restarted, previous state is lost and code must run cleanly in a fresh environment.

Code rules:
Do not write comments.
Write outputs only to OUTPUT_DIR.
Save plots using plt.savefig('plot.png') or under OUTPUT_DIR.
Do not generate csv/json files unless explicitly requested.
Execute analysis first, then use computed results to provide insights.
Prefer combining related charts into a single figure with subplots.
Do not apply external or custom matplotlib/seaborn styles. Use only default behavior and available libraries (pandas, numpy, matplotlib, seaborn, openpyxl).

Arguments: code (required), description (optional).
""".strip()
