from __future__ import annotations
import csv, json
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from typing import List, Tuple
import pandas as pd, streamlit as st
from stqdm import stqdm as tqdm
from llm_tools import prompt, llm_call

def _preprocess_reports(df: pd.DataFrame, client, model: str) -> List[int]:
    failed: List[int] = []

    def _call(idx: int, raw_report: str):
        content = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "developer", "content": [{"type": "text", "text": prompt.SYSTEM_PROMPT_PREPROCESS}]},
                {"role": "user", "content": raw_report},
            ],
            response_format={"type": "json_schema", "json_schema": prompt.PREPROCESSING_SCHEMA},
            timeout=prompt.REQUEST_TIMEOUT,
        ).choices[0].message.content

        try:
            json.loads(content)
            df.at[idx, prompt.COL_PREPROCESSED] = content
        except Exception as e:
            raise ValueError(f"Invalid preprocessing JSON: {e}")

    with tqdm(total=len(df), desc="1st pass LLM: Preprocess", unit="rep") as pbar, ThreadPoolExecutor(max_workers=prompt.MAX_WORKERS) as pool:
        futs = {pool.submit(_call, i, txt): i for i, txt in df[prompt.COL_REPORT].items()}
        for fut in as_completed(futs):
            idx = futs[fut]
            try:
                fut.result(timeout=prompt.REQUEST_TIMEOUT)
            except Exception as e:
                st.warning(f"[Preprocess] idx={idx} failed: {e}")
                failed.append(idx)
            finally:
                pbar.update()

    # retry
    for idx in list(failed):
        raw_report = df.at[idx, prompt.COL_REPORT]
        try:
            content = llm_call._retry_call(
                lambda: client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "developer", "content": [{"type": "text", "text": prompt.SYSTEM_PROMPT_PREPROCESS}]},
                        {"role": "user", "content": raw_report},
                    ],
                    response_format={"type": "json_schema", "json_schema": prompt.PREPROCESSING_SCHEMA},
                    timeout=prompt.REQUEST_TIMEOUT,
                ).choices[0].message.content,
                prompt.RETRY_LIMIT_FIRST,
                prefix="Preprocess Retry",
                idx=idx,
            )
            json.loads(content)
            df.at[idx, prompt.COL_PREPROCESSED] = content
            failed.remove(idx)
        except Exception:
            pass

    return failed



def _evaluate_first_pass(df: pd.DataFrame, client, model: str) -> List[int]:
    failed: List[int] = []

    def _call(idx: int, report: str):
        content = llm_call._chat_completion(client, model, [
            {"role": "developer", "content": [{"type": "text", "text": prompt.SYSTEM_PROMPT_ERROR_CHECK}]},
            {"role": "user", "content": report},
        ])
        llm_call._validate_json_response(content)
        return idx, content

    with tqdm(total=len(df), desc="2nd pass LLM: Error detector", unit="rep") as pbar, ThreadPoolExecutor(max_workers=prompt.MAX_WORKERS) as pool:
        fut_map = {pool.submit(_call, i, txt): i for i, txt in df[prompt.COL_PREPROCESSED].items()}
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            try:
                _, content = fut.result(timeout=prompt.REQUEST_TIMEOUT)
                llm_call._validate_json_response(content)
                df.at[idx, prompt.COL_ACC1_JSON] = content
            except Exception as e:
                st.warning(f"[1st] idx={idx} failed: {e}")
                failed.append(idx)
            finally:
                pbar.update()

    if failed:
        st.info(f"Retrying {len(failed)} failed requests automatically...")
        for idx in failed:
            report = df.at[idx, prompt.COL_PREPROCESSED]
            try:
                content = llm_call._retry_call(
                    lambda: llm_call._chat_completion(client, model, [
                        {"role": "developer", "content": [{"type": "text", "text": prompt.SYSTEM_PROMPT_ERROR_CHECK}]},
                        {"role": "user", "content": f"<value note> {report}"}
                    ]),
                    prompt.RETRY_LIMIT_FIRST, prefix="Retry", idx=idx
                )
                df.at[idx, prompt.COL_ACC1_JSON] = content
                st.success(f"[Retry success] idx={idx}")
            except Exception as e:
                st.error(f"[Final Failure] idx={idx} Failed after retry attempt: {e}")

    df[prompt.COL_ACC1_SCORE] = df[prompt.COL_ACC1_JSON].apply(llm_call._parse_score)
    return failed

def _evaluate_fp_pass(df: pd.DataFrame, client, model: str):
    targets = df.index[df[prompt.COL_ACC1_SCORE] == 0].tolist()
    if not targets:
        return

    def _call(idx: int):
        content = llm_call._chat_completion(client, model, [
            {"role": "developer", "content": [{"type": "text", "text": prompt.SYSTEM_PROMPT_FP_CHECK}]},
            {"role": "user", "content": (
                f"<preprocessed report JSON>\n{df.at[idx, prompt.COL_PREPROCESSED]}\n\n"
                f"<previous error JSON>\n{df.at[idx, prompt.COL_ACC1_JSON]}"
            )},
        ])
        llm_call._validate_json_response(content)
        result_score = llm_call._parse_score(content)
        return idx, content, result_score

    with tqdm(total=len(targets), desc="3rd pass LLM: False positive verifier", unit="rep") as pbar, ThreadPoolExecutor(max_workers=prompt.MAX_WORKERS) as pool:
        fut_map = {pool.submit(_call, i): i for i in targets}
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            try:
                _, content, result_score = fut.result()
                df.at[idx, prompt.COL_ACC2_JSON]  = content
                df.at[idx, prompt.COL_ACC2_SCORE] = result_score
            except Exception as e:
                st.warning(f"[FP] idx={idx} failed: {e}")
            finally:
                pbar.update()




def get_unstructured_accuracy(
    data: pd.DataFrame,
    *,
    api_key: str,
    model: str = "o4-mini",
    use_chatgpt: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if prompt.COL_REPORT not in data.columns:
        raise ValueError("Input DataFrame must contain a 'report' column.")

    df = data.copy()
    df[[
        prompt.COL_PREPROCESSED,
        prompt.COL_ACC1_JSON, prompt.COL_ACC1_SCORE,
        prompt.COL_ACC2_JSON, prompt.COL_ACC2_SCORE
    ]] = None

    client = llm_call._make_client(api_key, use_chatgpt)

    # 0) Preprocess
    preprocess_failures = _preprocess_reports(df, client, model="gpt-4.1-nano")
    if preprocess_failures:
        st.error(f"🚨 Preprocessing failed for {len(preprocess_failures)} reports; they will be skipped.")
        df = df.drop(preprocess_failures)  # remove them from further analysis

    # 1) Error detection
    _evaluate_first_pass(df, client, model)
    df[prompt.COL_ACC2_JSON]  = df[prompt.COL_ACC1_JSON]
    df[prompt.COL_ACC2_SCORE] = df[prompt.COL_ACC1_SCORE]
    
    # 2) False‑positive check
    _evaluate_fp_pass(df, client, model)

    summary = pd.DataFrame({
        "Metric": ["mean", "std"],
        "accuracy_1": [df[prompt.COL_ACC1_SCORE].mean(), df[prompt.COL_ACC1_SCORE].std()],
        "accuracy_2": [df[prompt.COL_ACC2_SCORE].mean(), df[prompt.COL_ACC2_SCORE].std()],
    })
    return df.copy(), summary
