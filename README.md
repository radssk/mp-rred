# 📑 MP‑RRED
Multi‑Pass LLM Radiology Report Error Detector




---

## Installation

clone the repo and enter it

```bash
git clone https://github.com/radssk/mp-rred.git
cd mp-rred
```

create and activate an `mm-rred` conda environment
```bash
conda create -n mp-rred python=3.10 -y
conda activate mp-rred
```

install dependencies
```bash
pip install -r requirements.txt
```

launch the app
```bash
streamlit run app.py
```

> Excel output is written to **your current working directory**.

---

## Try it online (no install)

Visit **https\://<USER>-<REPO>.streamlit.app**.


---

## Usage

1. **Upload** a CSV containing a `report` column.
2. **Enter API key & model** (OpenAI JSON‑Schema–compatible, e.g. o4-mini, o3). *Model choice affects only 2nd & 3rd passes.*
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

   
