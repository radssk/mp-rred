
from __future__ import annotations

import json, sys, types
from pathlib import Path
from datetime import datetime
from typing import Optional
from llm_tools import prompt  

import streamlit as st
import pandas as pd
from stqdm import stqdm
import tqdm

tqdm.tqdm = stqdm
sys.modules["tqdm"].tqdm = stqdm
auto_mod = types.ModuleType("tqdm.auto")
auto_mod.tqdm = stqdm
sys.modules["tqdm.auto"] = auto_mod
from llm_tools import pipeline as llm_eval  # updated path


COL_TEXT   = "report"
COL_PREPROCESSED = "preprocessed_report"
COL_ERROR  = "accuracy_2"
COL_SCORE  = "accuracy_2_score"
COL_RESULT = "accuracy_3"

NO_ERROR_JSON = {"error": "no error", "error_reason": "N/A"}

def tmp_save_path() -> Path:
    if "results_dir" not in st.session_state:
        default_dir = Path("results")
        default_dir.mkdir(exist_ok=True)
        st.session_state["results_dir"] = default_dir

    return st.session_state["results_dir"] / "CURRENT_RESULTS.csv"

def final_save_path() -> Path:
    return st.session_state["results_dir"] / "FINAL_RESULTS_DF.csv"

def parse_error_cell(cell) -> dict:
    if isinstance(cell, dict):
        return cell
    if pd.isna(cell) or cell == "":
        return NO_ERROR_JSON

    try:                                   
        parsed = json.loads(cell)
        if isinstance(parsed, dict):
            return parsed
        return {"error": parsed, "error_reason": "LLM returned non-dict JSON"}
    except (TypeError, json.JSONDecodeError):
        return {"error": str(cell), "error_reason": "Invalid JSON"}

# ───────────────────────────────
def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    req = {COL_TEXT, COL_ERROR, COL_SCORE}
    if not req.issubset(df.columns):
        raise ValueError(f"CSV must contain: {', '.join(req)}")

    df[COL_SCORE] = (
        pd.to_numeric(df[COL_SCORE], errors="coerce")
          .fillna(0)
          .astype(int)
    )

    df[COL_ERROR] = df[COL_ERROR].apply(parse_error_cell)

    if COL_RESULT not in df.columns:
        df[COL_RESULT] = ""
    else:
        df[COL_RESULT] = df[COL_RESULT].fillna("")
    if COL_PREPROCESSED not in df.columns:
        df[COL_PREPROCESSED] = "{}"

    return df

# ───────────────────────────────
# CSV load/save
# ───────────────────────────────
def load_csv(file) -> Optional[pd.DataFrame]:
    if file is None:
        return None
    if st.session_state.get("file_name") == file.name and "df" in st.session_state:
        return st.session_state["df"]

    try:
        df = pd.read_csv(file)
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        return None

    df = ensure_schema(df)
    st.session_state.update({"df": df, "file_name": file.name})
    return df

def save_csv(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    st.session_state["df"].to_csv(path, index=False, encoding="utf-8")

def next_pending_index() -> Optional[int]:
    df: pd.DataFrame = st.session_state["df"]
    mask = (df[COL_SCORE] == 0) & (df[COL_RESULT].fillna("") == "")
    return int(mask.idxmax()) if mask.any() else None

# ───────────────────────────────
# Streamlit UI
# ───────────────────────────────
CUSTOM_CSS = """
<style>
[data-testid="stCode"] pre,
[data-testid="stCode"] code {
  white-space: pre-wrap !important;
  word-break: break-word !important;
}
</style>
"""
st.set_page_config(page_title="MP-RRED", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.subheader("📄 MP-RRED: Multi-Pass LLM Radiology Report Error Detector")



# 1️⃣ LLM Evaluation --------------------------------------------------------
with st.expander("1️⃣  LLM Evaluation", expanded=False):
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    api_key  = st.text_input("② OpenAI API key", type="password")
    model = st.text_input("③ Model", value="o3")

    # ── Prompt Editor ──────────────────────────
    if st.toggle("🛠️ Prompt Editor", value=False):
        with st.container():
            DEFAULTS = {
                "SYSTEM_PROMPT_PREPROCESS": prompt.SYSTEM_PROMPT_PREPROCESS,
                "SYSTEM_PROMPT_ERROR_CHECK": prompt.SYSTEM_PROMPT_ERROR_CHECK,
                "SYSTEM_PROMPT_FP_CHECK":     prompt.SYSTEM_PROMPT_FP_CHECK,
            }
            if "CUSTOM_PROMPTS" not in st.session_state:
                st.session_state["CUSTOM_PROMPTS"] = DEFAULTS.copy()

            with st.form("prompt_form", clear_on_submit=False):
                new_pre = st.text_area(
                    "SYSTEM_PROMPT_PREPROCESS",
                    st.session_state["CUSTOM_PROMPTS"]["SYSTEM_PROMPT_PREPROCESS"],
                    height=220
                )
                new_err = st.text_area(
                    "SYSTEM_PROMPT_ERROR_CHECK",
                    st.session_state["CUSTOM_PROMPTS"]["SYSTEM_PROMPT_ERROR_CHECK"],
                    height=220
                )
                new_fp  = st.text_area(
                    "SYSTEM_PROMPT_FP_CHECK",
                    st.session_state["CUSTOM_PROMPTS"]["SYSTEM_PROMPT_FP_CHECK"],
                    height=220
                )

                if st.form_submit_button("💾  Save prompts for this session"):
                    st.session_state["CUSTOM_PROMPTS"] = {
                        "SYSTEM_PROMPT_PREPROCESS": new_pre or DEFAULTS["SYSTEM_PROMPT_PREPROCESS"],
                        "SYSTEM_PROMPT_ERROR_CHECK": new_err or DEFAULTS["SYSTEM_PROMPT_ERROR_CHECK"],
                        "SYSTEM_PROMPT_FP_CHECK":     new_fp  or DEFAULTS["SYSTEM_PROMPT_FP_CHECK"],
                    }
                    st.success("Prompts updated (session-only) ✅")

    if st.button("🚀 LLM Error Detection"):

        # CSV  -----------------------------------------------------
        if uploaded_file is None:
            st.warning("Upload a CSV file first.")
            st.stop()

        # Prompt -------------------------------------------
        DEFAULT_PROMPTS = {
            "SYSTEM_PROMPT_PREPROCESS": prompt.SYSTEM_PROMPT_PREPROCESS,
            "SYSTEM_PROMPT_ERROR_CHECK": prompt.SYSTEM_PROMPT_ERROR_CHECK,
            "SYSTEM_PROMPT_FP_CHECK":     prompt.SYSTEM_PROMPT_FP_CHECK,
        }
        custom_prompts = st.session_state.get("CUSTOM_PROMPTS", DEFAULT_PROMPTS)
        st.session_state["CUSTOM_PROMPTS"] = custom_prompts     

        # 2) CSV → DataFrame ----------------------------------------------------
        raw_df = pd.read_csv(uploaded_file)          

        raw_file = Path(uploaded_file.name)          

        # prompt monkey-patch -----------------------------------------------
        _orig = {k: getattr(prompt, k) for k in custom_prompts}
        for k, v in custom_prompts.items():
            setattr(prompt, k, v)

        # LM pipeline -------------------------------------------------
        with st.spinner("Detecting errors..."):
            try:
                result_df, _ = llm_eval.get_unstructured_accuracy(
                    raw_df,
                    use_chatgpt=True,
                    model=model,
                    api_key=api_key,
                )
            finally:
                for k, v in _orig.items():
                    setattr(prompt, k, v)

        #  ------------------------------------------
        st.session_state["df"] = ensure_schema(result_df)
        st.session_state["file_name"] = raw_file.name
        st.rerun()

# 2️⃣ Labeling Section ------------------------------------------------------
if "df" not in st.session_state:
    st.info("Please run the LLM evaluation first.")
    st.stop()

if "fail_count" in st.session_state and st.session_state["fail_count"] > 0:
    fail_count = st.session_state.pop("fail_count")
    st.warning(f"⚠️ {fail_count} reports could not be processed by the LLM. "
               "See 'failed_requests.csv' in the results directory for details.")

df: pd.DataFrame = st.session_state["df"]

mask_total = df[COL_SCORE] == 0
total_to_label = int(mask_total.sum())
done_now = int((mask_total & (df[COL_RESULT].fillna("") != "")).sum())

st.progress(done_now / total_to_label if total_to_label else 0)
st.caption(f"🔖 {done_now} / {total_to_label} labeled")

idx = next_pending_index()

# ── Labeling UI / Completion ----------------------------------------------
if idx is None:   
    # --------------------------------------------------------------------
    # 🎉 Finish Screen with statistics & file saving (table removed)
    # --------------------------------------------------------------------
    st.success("🎉 Labeling complete!")

    # 1) accuracy_3_score = accuracy_2_score copy, then overwrite FP rows with 1
    df["accuracy_3_score"] = df[COL_SCORE].copy()
    df.loc[df[COL_RESULT] == "FP", "accuracy_3_score"] = 1

    # 2) Compute statistics
    total_reports    = len(df)
    tp_count         = int(df[COL_RESULT].eq("TP").sum())
    fp_count         = int(df[COL_RESULT].eq("FP").sum())
    true_error_ratio = tp_count / total_reports if total_reports else 0
    ppv              = tp_count / (tp_count + fp_count) if (tp_count + fp_count) else 0

    stats_df = pd.DataFrame(
        {
            "Metric": [
                "True Error (TP)",
                "False Positive (FP)",
                "Total Reports",
                "Absolute True-Positive Rate (aTPR)",
                "Positive Predictive Value (PPV)",
            ],
            "Value": [
                float(tp_count),          
                float(fp_count),
                float(total_reports),
                true_error_ratio,         
                ppv,                      
            ],
        }
    )

    def _fmt(v):
        return f"{v:.2%}" if isinstance(v, float) and v < 1 else f"{int(v):,}"

    st.subheader("📊 Summary Statistics")
    st.dataframe(
        stats_df.style.format({"Value": _fmt}),
        hide_index=True
    )

    
    csv_df = stats_df.copy()
    csv_df["Value"] = csv_df["Value"].apply(_fmt)


    FINAL_SAVE = final_save_path()
    STATS_SAVE = FINAL_SAVE.parent / "RESULT_STATS.csv"

    save_csv(FINAL_SAVE)                  
    stats_df.to_csv(STATS_SAVE, index=False, encoding="utf-8")


    st.markdown(
        f"""
        ✅ **Final results** saved to `{FINAL_SAVE.resolve()}`  
        📊 **Summary statistics** saved to `{STATS_SAVE.resolve()}`
        """,
        unsafe_allow_html=True,
    )
    st.stop()
else:
    row = df.loc[idx]
    err_json    = row[COL_ERROR]                    
    error_msg   = err_json.get("error", "N/A")
    error_cause = err_json.get("error_reason", "N/A")

    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader(f"📝 Report #{idx}")
        cell = row.get(COL_PREPROCESSED, "{}")
        try:
            obj = cell if isinstance(cell, dict) else json.loads(cell)
            findings_part    = obj.get("findings", "")
            impression_part  = obj.get("impression", "")
        except Exception:
            findings_part, impression_part = str(cell), ""
        st.markdown(f"**Findings**\n\n{findings_part}\n\n**Impression**\n\n{impression_part}")
    with right_col:
        upper, lower = st.container(), st.container()

        with upper:
            st.markdown("#### ⚠️ **Detected Error**")
            st.write(error_msg)        

        with lower:
            st.markdown("#### 💡 **Error Reason**")
            st.write(error_cause)

    choice = st.radio(
        "",
        options=("TP (True Error)", "FP (False Positive)"),
        horizontal=True,
    )

    if st.button("💾 Save & Next"):
        df.at[idx, COL_RESULT] = "TP" if choice.startswith("TP") else "FP"
        save_csv(tmp_save_path())
        st.rerun()