# MP‑RRED: Multi‑pass LLM Radiology Report Error Detector


https://chatgpt.com/share/683d0ee0-3168-8008-a45a-d85efe6473eb


# 📑 LLM Streamlit Demo

A minimal **Streamlit** interface for running an LLM (e.g. OpenAI GPT‑4o) on radiology reports and exporting results to Excel. The API key is entered **in‑app**—no environment variables required.

---

## Installation (Conda)

```bash
git clone https://github.com/<YOUR-ID>/<REPO-NAME>.git
cd <REPO-NAME>
conda create -n llm_demo python=3.10 -y && conda activate llm_demo
pip install -r requirements.txt
streamlit run app.py    # Opens http://localhost:8501
```

> Excel output is written to **your current working directory**.

---

## Try it online (no install)

1. Visit **https\://<USER>-<REPO>.streamlit.app**.
2. Paste your **API key** when prompted.
3. Upload a CSV and run the workflow.
4. Download the generated Excel.

---

## Usage

1. **Upload** a CSV containing a `report` column.
2. **Enter** your API key & chosen model (`o4-mini`, `o3`, …). *Model applies only to the 2nd & 3rd passes.* *must be a JSON Schema-compatible OpenAI model*
3. Click **LLM Error Detection**.
4. For each flagged report, select **True Error** or **False Positive** → **Save & Next**.
5. When finished, review the summary and download `output.xlsx`.

---

## Citation

If this tool aids your research, please cite our preprint:

```bibtex
@misc{lastname2025llmstreamlit,
  title  = {LLM Streamlit Demo},
  author = {Lastname, First and Coauthors},
  note   = {arXiv:XXXX.XXXXX},
  year   = {2025}
}
```

---

## License — MIT

Free to use, modify, and distribute.

   
