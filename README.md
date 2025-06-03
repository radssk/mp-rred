# 📑 MP‑RRED: Multi‑pass LLM Radiology Report Error Detector


https://chatgpt.com/share/683d0ee0-3168-8008-a45a-d85efe6473eb



---

## Installation (Conda)

```bash
# clone the repo and enter it
git clone https://github.com/radssk/mp-rred.git
cd mp-rred

# create and activate an isolated Python 3.10 env
conda create -n mp_rred python=3.10 -y
conda activate mp_rred

# install dependencies
pip install -r requirements.txt

# launch the app
streamlit run app.py
```

> Excel output is written to **your current working directory**.

---

## Try it online (no install)

1. Visit **https\://<USER>-<REPO>.streamlit.app**.


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

   
