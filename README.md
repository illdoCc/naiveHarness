# Run the Workshop Notebook

Use Python 3.10 or newer. Run the commands below from this project directory, using your Python environment.

1. Install [Ollama](https://ollama.com/download), then download the model:

   ```bash
   ollama pull qwen3.5:4b
   ```

   Keep Ollama running. If it is not already running, start it in a separate terminal:

   ```bash
   ollama serve
   ```

2. Install Jupyter with pip:

   ```bash
   python -m pip install jupyterlab ipykernel
   ```

3. Open the notebook:

   ```bash
   python -m jupyterlab workshop.ipynb
   ```

   Select the Python kernel for your environment. Run the code cells from top to bottom with **Shift + Enter**, waiting for each cell to finish. The notebook calls your local Ollama server automatically; no API key is needed. Model generation can take several minutes on a CPU.

   To start a fresh run, restart the kernel and run the cells again from the top.
