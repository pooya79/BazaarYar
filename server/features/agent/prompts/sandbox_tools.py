RUN_PYTHON_CODE_TOOL_DESCRIPTION = (
    "Run Python code in an isolated sandbox for data analysis and plotting. "
    "Sandbox globals: INPUT_DIR=/workspace/input, OUTPUT_DIR=/workspace/output, ATTACHMENTS, AVAILABLE_FILES, load_dataframe(). "
    "The sandbox process writes artifacts from /workspace/output (its working directory). "
    "Pass attachment_ids as a list of user attachment IDs when selecting specific files. "
    "Use ATTACHMENTS entries (attachment_id/original_filename/sandbox_filename/input_path) to map IDs to files. "
    "For plots, call plt.savefig('plot.png') or save files under OUTPUT_DIR so artifacts are returned. "
    "Available libraries include pandas, matplotlib, seaborn, numpy and openpyxl. "
    "Args: code, attachment_ids (optional list of attachment IDs), description (optional)."
)
